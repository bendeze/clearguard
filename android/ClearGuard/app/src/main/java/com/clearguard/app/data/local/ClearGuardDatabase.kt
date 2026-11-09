package com.clearguard.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.clearguard.app.data.local.dao.BlocklistDao
import com.clearguard.app.data.local.entity.BlocklistEntity

@Database(
    entities = [BlocklistEntity::class],
    version = 1,
    exportSchema = false
)
abstract class ClearGuardDatabase : RoomDatabase() {
    abstract fun blocklistDao(): BlocklistDao
}
