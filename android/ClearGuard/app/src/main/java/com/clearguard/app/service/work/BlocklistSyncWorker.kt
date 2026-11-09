package com.clearguard.app.service.work

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.clearguard.app.domain.repository.BlocklistRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class BlocklistSyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParams: WorkerParameters,
    private val blocklistRepository: BlocklistRepository
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        val syncResult = blocklistRepository.syncBlocklistFromBackend()
        return if (syncResult.isSuccess) {
            Result.success()
        } else {
            Result.retry()
        }
    }

    companion object {
        const val WORK_NAME = "blocklist_sync_worker"
    }
}
