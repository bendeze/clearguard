package com.clearguard.app.service.accessibility

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.view.accessibility.AccessibilityEvent
import com.clearguard.app.MainActivity

class ClearGuardAccessibilityService : AccessibilityService() {

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return

        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            val packageName = event.packageName?.toString() ?: ""
            if (packageName == "com.android.settings") {
                val className = event.className?.toString() ?: ""
                // Detect force stop or admin deactivation attempts in settings
                if (className.contains("DeviceAdminAdd") || className.contains("ApplicationSettings")) {
                    val intent = Intent(this, MainActivity::class.java).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                    }
                    startActivity(intent)
                }
            }
        }
    }

    override fun onInterrupt() {}
}
