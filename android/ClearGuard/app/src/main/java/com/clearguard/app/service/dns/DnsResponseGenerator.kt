package com.clearguard.app.service.dns

object DnsResponseGenerator {

    /**
     * Creates a synthetic NXDOMAIN (Domain Not Found) DNS response packet
     * corresponding to the given DNS [queryPacket].
     * Returns null if the query packet is too short to be a valid DNS header.
     */
    fun createNxDomainResponse(queryPacket: ByteArray): ByteArray? {
        if (queryPacket.size < 12) return null

        val response = queryPacket.copyOf()

        // Set Flags (Bytes 2 & 3)
        // Byte 2: QR=1 (Response), Opcode=0 (Standard Query), AA=1 (Authoritative), TC=0, RD=1 (Recursion Desired) -> 0x85
        // Byte 3: RA=1 (Recursion Available), Z=0, RCODE=3 (NXDOMAIN) -> 0x83
        response[2] = 0x85.toByte()
        response[3] = 0x83.toByte()

        return response
    }
}
