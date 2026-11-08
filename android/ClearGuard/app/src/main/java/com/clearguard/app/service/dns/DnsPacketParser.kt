package com.clearguard.app.service.dns

import java.nio.ByteBuffer

object DnsPacketParser {

    /**
     * Extracts the requested domain name (QNAME) from a raw DNS query packet.
     * Returns null if the packet is malformed or invalid.
     */
    fun extractDomainName(dnsPacket: ByteArray): String? {
        if (dnsPacket.size < 12) return null // DNS header is 12 bytes minimum

        val buffer = ByteBuffer.wrap(dnsPacket)

        // Skip Header: Transaction ID (2), Flags (2), QDCOUNT (2), ANCOUNT (2), NSCOUNT (2), ARCOUNT (2)
        val qdCount = buffer.getShort(4).toInt() and 0xFFFF
        if (qdCount <= 0) return null

        buffer.position(12) // Move past header to Question section

        return parseQName(buffer)
    }

    private fun parseQName(buffer: ByteBuffer): String? {
        val domainParts = mutableListOf<String>()
        val maxLen = buffer.capacity()

        while (buffer.position() < maxLen) {
            val length = buffer.get().toInt() and 0xFF
            if (length == 0) break // Root label reached (end of domain)

            // Pointer/Compression (not typical in query QNAMEs, but handled defensively)
            if ((length and 0xC0) == 0xC0) return null

            if (buffer.remaining() < length) return null

            val labelBytes = ByteArray(length)
            buffer.get(labelBytes)
            domainParts.add(String(labelBytes, Charsets.US_ASCII))
        }

        return if (domainParts.isNotEmpty()) {
            domainParts.joinToString(".").lowercase()
        } else {
            null
        }
    }
}
