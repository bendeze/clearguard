package com.clearguard.app.service

import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor
import com.clearguard.app.domain.repository.BlocklistRepository
import com.clearguard.app.service.dns.DnsPacketParser
import com.clearguard.app.service.dns.DnsResponseGenerator
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.nio.ByteBuffer
import javax.inject.Inject

@AndroidEntryPoint
class ClearGuardVpnService : VpnService() {

    @Inject
    lateinit var blocklistRepository: BlocklistRepository

    private var vpnInterface: ParcelFileDescriptor? = null
    private var packetLoopJob: Job? = null
    private val serviceScope = CoroutineScope(Dispatchers.IO)

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startVpn()
            ACTION_STOP -> stopVpn()
        }
        return START_STICKY
    }

    private fun startVpn() {
        if (vpnInterface != null) return

        try {
            val builder = Builder()
                .setSession("ClearGuard Local Protection")
                .addAddress("10.0.0.2", 32)
                .addDnsServer("10.0.0.1")
                .addRoute("10.0.0.1", 32)   // Capture local virtual DNS
                .addRoute("1.1.1.1", 32)    // Capture Cloudflare DNS
                .addRoute("1.0.0.1", 32)
                .addRoute("8.8.8.8", 32)    // Capture Google DNS
                .addRoute("8.8.4.4", 32)
                .setBlocking(true)

            vpnInterface = builder.establish()
            _isRunning.value = true

            startPacketProcessingLoop()
        } catch (e: Exception) {
            e.printStackTrace()
            stopVpn()
        }
    }

    private fun startPacketProcessingLoop() {
        val pfd = vpnInterface ?: return

        packetLoopJob = serviceScope.launch {
            val inputStream = FileInputStream(pfd.fileDescriptor)
            val outputStream = FileOutputStream(pfd.fileDescriptor)
            val packetBuffer = ByteArray(32767)

            while (_isRunning.value) {
                try {
                    val length = inputStream.read(packetBuffer)
                    if (length <= 0) continue

                    processCapturedPacket(packetBuffer, length, outputStream)
                } catch (_: Exception) {
                    if (!_isRunning.value) break
                }
            }
        }
    }

    private suspend fun processCapturedPacket(
        packet: ByteArray,
        length: Int,
        outputStream: FileOutputStream
    ) {
        if (length < 28) return // Minimum IP (20) + UDP (8) header size

        val buffer = ByteBuffer.wrap(packet, 0, length)
        val ipVersionAndIhl = buffer.get(0).toInt() and 0xFF
        val ipVersion = ipVersionAndIhl ushr 4

        if (ipVersion != 4) return // Focus on IPv4 DNS queries

        val ihl = (ipVersionAndIhl and 0x0F) * 4
        val protocol = buffer.get(9).toInt() and 0xFF

        // Drop DNS-over-TLS (port 853) packets to force browsers to fallback to standard DNS
        if (protocol == 6 || protocol == 17) {
            val destPort = buffer.getShort(ihl + 2).toInt() and 0xFFFF
            if (destPort == 853) {
                return // Drop DoT bypass attempts
            }
        }

        // Process UDP DNS queries (Protocol = 17, Dest Port = 53)
        if (protocol == 17) {
            val destPort = buffer.getShort(ihl + 2).toInt() and 0xFFFF
            if (destPort == 53) {
                val udpHeaderLength = 8
                val dnsOffset = ihl + udpHeaderLength
                val dnsLength = length - dnsOffset

                if (dnsLength > 12) {
                    val dnsQueryBytes = ByteArray(dnsLength)
                    System.arraycopy(packet, dnsOffset, dnsQueryBytes, 0, dnsLength)

                    val queriedDomain = DnsPacketParser.extractDomainName(dnsQueryBytes)
                    if (queriedDomain != null) {
                        val isBlocked = blocklistRepository.isDomainBlocked(queriedDomain)
                        if (isBlocked) {
                            // Blocked Domain -> Return NXDOMAIN Response
                            val dnsNxResponse = DnsResponseGenerator.createNxDomainResponse(dnsQueryBytes)
                            if (dnsNxResponse != null) {
                                val ipResponsePacket = buildUdpIpResponsePacket(
                                    packet = packet,
                                    ihl = ihl,
                                    dnsResponseBytes = dnsNxResponse
                                )
                                try {
                                    outputStream.write(ipResponsePacket)
                                } catch (e: Exception) {
                                    e.printStackTrace()
                                }
                            }
                        } else {
                            // Allowed Domain -> Forward to Real Upstream DNS (1.1.1.1) and return real answer
                            forwardAllowedDnsQuery(
                                packet = packet,
                                ihl = ihl,
                                dnsQueryBytes = dnsQueryBytes,
                                outputStream = outputStream
                            )
                        }
                    }
                }
            }
        }
    }

    private fun forwardAllowedDnsQuery(
        packet: ByteArray,
        ihl: Int,
        dnsQueryBytes: ByteArray,
        outputStream: FileOutputStream
    ) {
        try {
            val socket = DatagramSocket()
            protect(socket) // Exclude upstream UDP socket from VPN loop
            socket.soTimeout = 2500

            val upstreamAddress = InetAddress.getByName("1.1.1.1") // Cloudflare Public DNS
            val sendPacket = DatagramPacket(dnsQueryBytes, dnsQueryBytes.size, upstreamAddress, 53)
            socket.send(sendPacket)

            val receiveBuffer = ByteArray(1500)
            val receivePacket = DatagramPacket(receiveBuffer, receiveBuffer.size)
            socket.receive(receivePacket)
            socket.close()

            val upstreamDnsResponse = ByteArray(receivePacket.length)
            System.arraycopy(receiveBuffer, 0, upstreamDnsResponse, 0, receivePacket.length)

            val ipResponsePacket = buildUdpIpResponsePacket(
                packet = packet,
                ihl = ihl,
                dnsResponseBytes = upstreamDnsResponse
            )
            outputStream.write(ipResponsePacket)
        } catch (_: Exception) {
            // Socket timeout or network unreachable
        }
    }

    private fun buildUdpIpResponsePacket(
        packet: ByteArray,
        ihl: Int,
        dnsResponseBytes: ByteArray
    ): ByteArray {
        val udpHeaderLength = 8
        val totalLength = ihl + udpHeaderLength + dnsResponseBytes.size
        val response = ByteArray(totalLength)

        // Copy IP Header
        System.arraycopy(packet, 0, response, 0, ihl)

        // Swap Source & Destination IP in IP Header
        System.arraycopy(packet, 16, response, 12, 4) // Original Dest -> New Source
        System.arraycopy(packet, 12, response, 16, 4) // Original Source -> New Dest

        // Update Total Length in IP Header
        response[2] = (totalLength ushr 8).toByte()
        response[3] = (totalLength and 0xFF).toByte()

        // UDP Header Offset
        val udpOffset = ihl
        val srcPort = ((packet[udpOffset + 2].toInt() and 0xFF) shl 8) or (packet[udpOffset + 3].toInt() and 0xFF)
        val dstPort = ((packet[udpOffset].toInt() and 0xFF) shl 8) or (packet[udpOffset + 1].toInt() and 0xFF)

        // UDP Source & Dest Port
        response[udpOffset] = (srcPort ushr 8).toByte()
        response[udpOffset + 1] = (srcPort and 0xFF).toByte()
        response[udpOffset + 2] = (dstPort ushr 8).toByte()
        response[udpOffset + 3] = (dstPort and 0xFF).toByte()

        // UDP Length
        val udpTotalLen = udpHeaderLength + dnsResponseBytes.size
        response[udpOffset + 4] = (udpTotalLen ushr 8).toByte()
        response[udpOffset + 5] = (udpTotalLen and 0xFF).toByte()

        // Zero out UDP Checksum
        response[udpOffset + 6] = 0
        response[udpOffset + 7] = 0

        // Zero out IPv4 Header Checksum before calculating valid checksum
        response[10] = 0
        response[11] = 0

        val ipChecksum = computeIpHeaderChecksum(response, ihl)
        response[10] = (ipChecksum.toInt() ushr 8).toByte()
        response[11] = (ipChecksum.toInt() and 0xFF).toByte()

        // Copy DNS Payload
        System.arraycopy(dnsResponseBytes, 0, response, udpOffset + udpHeaderLength, dnsResponseBytes.size)

        return response
    }

    private fun computeIpHeaderChecksum(header: ByteArray, ihl: Int): Short {
        var sum = 0
        var i = 0
        while (i < ihl) {
            if (i != 10) { // Skip checksum field at bytes 10-11
                val word = ((header[i].toInt() and 0xFF) shl 8) or (header[i + 1].toInt() and 0xFF)
                sum += word
            }
            i += 2
        }
        while (sum ushr 16 > 0) {
            sum = (sum and 0xFFFF) + (sum ushr 16)
        }
        return (sum.inv() and 0xFFFF).toShort()
    }

    private fun stopVpn() {
        try {
            packetLoopJob?.cancel()
            packetLoopJob = null
            vpnInterface?.close()
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            vpnInterface = null
            _isRunning.value = false
            stopSelf()
        }
    }

    override fun onDestroy() {
        stopVpn()
        super.onDestroy()
    }

    companion object {
        const val ACTION_START = "com.clearguard.app.action.START_VPN"
        const val ACTION_STOP = "com.clearguard.app.action.STOP_VPN"

        private val _isRunning = MutableStateFlow(false)
        val isRunning: StateFlow<Boolean> = _isRunning.asStateFlow()
    }
}
