package com.clearguard.app.service.dns

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.io.ByteArrayOutputStream

class DnsPacketParserTest {

    @Test
    fun extractDomainName_validQuery_returnsCorrectDomain() {
        val dnsPacket = createDnsQueryPacket("example.com")
        val domain = DnsPacketParser.extractDomainName(dnsPacket)
        assertEquals("example.com", domain)
    }

    @Test
    fun extractDomainName_subdomain_returnsCorrectDomain() {
        val dnsPacket = createDnsQueryPacket("sub.domain.co.uk")
        val domain = DnsPacketParser.extractDomainName(dnsPacket)
        assertEquals("sub.domain.co.uk", domain)
    }

    @Test
    fun extractDomainName_shortPacket_returnsNull() {
        val shortPacket = ByteArray(5)
        val domain = DnsPacketParser.extractDomainName(shortPacket)
        assertNull(domain)
    }

    private fun createDnsQueryPacket(domain: String): ByteArray {
        val out = ByteArrayOutputStream()

        // 12-byte DNS Header
        out.write(byteArrayOf(0x12, 0x34)) // Transaction ID
        out.write(byteArrayOf(0x01, 0x00)) // Standard query flags
        out.write(byteArrayOf(0x00, 0x01)) // QDCOUNT = 1
        out.write(byteArrayOf(0x00, 0x00)) // ANCOUNT = 0
        out.write(byteArrayOf(0x00, 0x00)) // NSCOUNT = 0
        out.write(byteArrayOf(0x00, 0x00)) // ARCOUNT = 0

        // QNAME encoding
        for (part in domain.split(".")) {
            val bytes = part.toByteArray(Charsets.US_ASCII)
            out.write(bytes.size)
            out.write(bytes)
        }
        out.write(0) // Null byte terminating QNAME

        // QTYPE (A = 1) and QCLASS (IN = 1)
        out.write(byteArrayOf(0x00, 0x01))
        out.write(byteArrayOf(0x00, 0x01))

        return out.toByteArray()
    }
}
