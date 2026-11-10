package com.clearguard.app.domain.security

import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import java.security.KeyStore
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

object BiometricAuthManager {

    private const val KEY_ALIAS = "clearguard_partner_biometric_key"
    private const val KEYSTORE_NAME = "AndroidKeyStore"

    /**
     * Checks if the device hardware supports biometric authentication (Fingerprint / Face Recognition).
     */
    fun isBiometricAvailable(context: Context): Boolean {
        val biometricManager = BiometricManager.from(context)
        val status = biometricManager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.BIOMETRIC_WEAK
        )
        return status == BiometricManager.BIOMETRIC_SUCCESS || status == BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED
    }

    /**
     * Checks if biometric credentials (fingerprint/face) are currently enrolled on the device.
     */
    fun isBiometricEnrolled(context: Context): Boolean {
        val biometricManager = BiometricManager.from(context)
        val status = biometricManager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.BIOMETRIC_WEAK
        )
        return status == BiometricManager.BIOMETRIC_SUCCESS
    }

    /**
     * Launches Android's native system biometric enrollment screen so the partner can add a new fingerprint.
     */
    fun launchBiometricEnrollment(activity: FragmentActivity) {
        val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Intent(Settings.ACTION_BIOMETRIC_ENROLL).apply {
                putExtra(
                    Settings.EXTRA_BIOMETRIC_AUTHENTICATORS_ALLOWED,
                    BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.BIOMETRIC_WEAK
                )
            }
        } else {
            @Suppress("DEPRECATION")
            Intent(Settings.ACTION_SECURITY_SETTINGS)
        }
        try {
            activity.startActivity(intent)
        } catch (_: Exception) {
            activity.startActivity(Intent(Settings.ACTION_SETTINGS))
        }
    }

    /**
     * Generates a secret key in Android KeyStore bound to biometric authentication.
     * If enrolled fingerprints are altered in System Settings, KeyStore automatically invalidates this key.
     */
    fun generateBiometricKey() {
        val keyGenerator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE_NAME)
        val builder = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_CBC)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_PKCS7)
            .setUserAuthenticationRequired(true)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            builder.setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
        }

        keyGenerator.init(builder.build())
        keyGenerator.generateKey()
    }

    private fun getSecretKey(): SecretKey? {
        val keyStore = KeyStore.getInstance(KEYSTORE_NAME).apply { load(null) }
        return keyStore.getKey(KEY_ALIAS, null) as? SecretKey
    }

    /**
     * Launches native Android BiometricPrompt dialog with hardware KeyStore CryptoObject binding.
     */
    fun promptBiometricAuth(
        activity: FragmentActivity,
        title: String = "Co-Sign Authentication",
        subtitle: String = "Authenticate fingerprint or face to proceed",
        onSuccess: () -> Unit,
        onError: (String) -> Unit
    ) {
        val executor = ContextCompat.getMainExecutor(activity)
        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                super.onAuthenticationSucceeded(result)
                onSuccess()
            }

            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                super.onAuthenticationError(errorCode, errString)
                onError(errString.toString())
            }

            override fun onAuthenticationFailed() {
                super.onAuthenticationFailed()
                onError("Biometric authentication failed")
            }
        }

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setSubtitle(subtitle)
            .setNegativeButtonText("Cancel")
            .build()

        val biometricPrompt = BiometricPrompt(activity, executor, callback)

        try {
            if (getSecretKey() == null) {
                generateBiometricKey()
            }
            val cipher = Cipher.getInstance("${KeyProperties.KEY_ALGORITHM_AES}/${KeyProperties.BLOCK_MODE_CBC}/${KeyProperties.ENCRYPTION_PADDING_PKCS7}")
            cipher.init(Cipher.ENCRYPT_MODE, getSecretKey())
            biometricPrompt.authenticate(promptInfo, BiometricPrompt.CryptoObject(cipher))
        } catch (_: Exception) {
            // Fallback to standard prompt if CryptoObject initialization fails
            biometricPrompt.authenticate(promptInfo)
        }
    }

    /**
     * Computes SHA-256 hash of a PIN string for secure storage and comparison.
     */
    fun hashPin(pin: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(pin.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
