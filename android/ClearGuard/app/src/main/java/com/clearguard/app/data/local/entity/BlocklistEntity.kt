package com.clearguard.app.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "blocklists")
data class BlocklistEntity(
    @PrimaryKey val domain: String,
    val category: String = "adult",
    val addedAt: Long = System.currentTimeMillis()
)
