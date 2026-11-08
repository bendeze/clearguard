package com.clearguard.app.di

import com.clearguard.app.data.repository.ProtectionRepositoryImpl
import com.clearguard.app.domain.repository.ProtectionRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindProtectionRepository(
        impl: ProtectionRepositoryImpl
    ): ProtectionRepository
}
