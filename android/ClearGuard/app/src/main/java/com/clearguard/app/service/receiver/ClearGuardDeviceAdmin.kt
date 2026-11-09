package com.clearguard.app.service.receiver

import android.app.admin.DeviceAdminReceiver
import android.content.Context
import android.content.Intent

class ClearGuardDeviceAdmin : DeviceAdminReceiver() {

    override fun onEnabled(context: Context, intent: Intent) {
        super.onEnabled(context, intent)
    }

    override fun onDisabled(context: Context, intent: Intent) {
        super.onDisabled(context, intent)
    }

    override fun onDisableRequested(context: Context, intent: Intent): CharSequence {
        return "Deactivating ClearGuard Device Admin requires dual-user co-signing and initiates a mandatory 60-day cool-off delay."
    }
}
