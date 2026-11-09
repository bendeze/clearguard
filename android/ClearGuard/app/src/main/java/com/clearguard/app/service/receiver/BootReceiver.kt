package com.clearguard.app.service.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.clearguard.app.domain.model.ProtectionStatus
import com.clearguard.app.domain.repository.ProtectionRepository
import com.clearguard.app.service.ClearGuardVpnService
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class BootReceiver(
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) : BroadcastReceiver() {

    @Inject
    lateinit var protectionRepository: ProtectionRepository

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            val pendingResult = try { goAsync() } catch (_: Exception) { null }
            CoroutineScope(ioDispatcher).launch {
                try {
                    val status = protectionRepository.getProtectionStatus().first()
                    if (status == ProtectionStatus.ACTIVE) {
                        val vpnIntent = Intent(context, ClearGuardVpnService::class.java).apply {
                            action = ClearGuardVpnService.ACTION_START
                        }
                        context.startService(vpnIntent)
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                } finally {
                    pendingResult?.finish()
                }
            }
        }
    }
}
