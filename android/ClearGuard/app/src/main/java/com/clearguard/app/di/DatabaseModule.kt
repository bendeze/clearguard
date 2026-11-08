package com.clearguard.app.di

import android.content.Context
import androidx.room.Room
import com.clearguard.app.data.local.ClearGuardDatabase
import com.clearguard.app.data.local.dao.BlocklistDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideClearGuardDatabase(
        @ApplicationContext context: Context
    ): ClearGuardDatabase {
        return Room.databaseBuilder(
            context,
            ClearGuardDatabase::class.java,
            "clearguard_db"
        ).fallbackToDestructiveMigration(true).build()
    }

    @Provides
    fun provideBlocklistDao(
        database: ClearGuardDatabase
    ): BlocklistDao {
        return database.blocklistDao()
    }
}
