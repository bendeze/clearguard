package com.clearguard.app.service.dns

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class DnsResponseGeneratorTest {

    @Test
    fun createNxDomainResponse_validQuery_returnsResponseWithNxDomainCode() {
        val query = byteArrayOf(
            0x12, 0x34, // ID
            0x01, 0x00, // Standard query flags
            0x00, 0x01, // QDCOUNT = 1
            0x00, 0x00, // ANCOUNT = 0
            0x00, 0x00, // NSCOUNT = 0
            0x00, 0x00, // ARCOUNT = 0
            0x07, 0x65, 0x78, 0x61, 0x6d, 0x70, 0x6c, 0x65, // example
            0x03, 0x63, 0x6f, 0x6d, 0x00, // com
            0x00, 0x01, 0x00, 0x01 // QTYPE, QCLASS
        )

        val response = DnsResponseGenerator.createNxDomainResponse(query)

        assertNotNull(response)
        assertEquals(query[0], response!![0]) // ID byte 1
        assertEquals(query[1], response[1])  // ID byte 2
        assertEquals(0x85.toByte(), response[2]) // Response flags
        assertEquals(0x83.toByte(), response[3]) // NXDOMAIN (RCODE = 3)
    }

    @Test
    fun createNxDomainResponse_shortPacket_returnsNull() {
        val shortPacket = ByteArray(5)
        val response = DnsResponseGenerator.createNxDomainResponse(shortPacket)
        assertNull(response)
    }
}
