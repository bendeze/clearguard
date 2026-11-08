package com.clearguard.app.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.clearguard.app.data.local.entity.BlocklistEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface BlocklistDao {
    @Query("SELECT * FROM blocklists")
    fun getAllBlockedDomains(): Flow<List<BlocklistEntity>>

    @Query("SELECT EXISTS(SELECT 1 FROM blocklists WHERE domain = :domain)")
    suspend fun isDomainBlocked(domain: String): Boolean

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDomains(domains: List<BlocklistEntity>)

    @Query("DELETE FROM blocklists WHERE domain = :domain")
    suspend fun deleteDomain(domain: String)

    @Query("DELETE FROM blocklists")
    suspend fun clearAll()
}
