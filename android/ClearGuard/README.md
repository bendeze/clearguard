<p align="center">
  <img src="docs/screenshots/logo.png" width="120" alt="ClearGuard Logo" />
  <h1 align="center">ClearGuard Android</h1>
  <p align="center">
    <strong>Open-Source Digital Self-Protection for Android</strong>
  </p>
</p>

---

Native Android application for **ClearGuard** — an open-source, offline-first digital self-protection system designed to block pornography and adult content across your entire device using local DNS filtering and VPN packet inspection.

---

## 🌟 Features

- **🔒 Local On-Device DNS Filtering**: Enforces system-wide filtering through a local VPN interface (`10.0.0.2`) without routing your traffic through external VPN servers.
- **⚡ Zero Bypass Architecture**: Automatically drops encrypted DNS bypass attempts (DNS-over-TLS port 853 / DNS-over-HTTPS) forcing browsers to fall back to standard local DNS filtering.
- **📱 Ultra-Minimalist UI**: Designed with high-contrast dark zinc monochrome aesthetic (`#09090B`), Lucide-style outlined icons, and dynamic light/dark theme modes.
- **🚫 100% Privacy & Zero Logging**: Operates completely on-device. Zero browsing history, URL logs, or personal metrics are stored or transmitted.
- **📡 Offline-First & Background Sync**: Ships with pre-loaded local SQLite Room blocklist rules that work without an internet connection, supported by WorkManager background cloud updates.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Language** | Kotlin 2.2.10 |
| **UI Framework** | Jetpack Compose (Material 3) |
| **Architecture** | MVVM + Clean Architecture Principles |
| **Dependency Injection** | Hilt |
| **Local Database** | Room / SQLite |
| **Network Protection** | Android `VpnService` + UDP Packet Parsing |
| **Background Tasks** | WorkManager (`HiltWorker`) |
| **Networking** | Retrofit + OkHttp |
| **Testing** | JUnit4, Mockito, Kotlinx Coroutines Test |
| **Build System** | Gradle Kotlin DSL (`AGP 9.5.1`) |

---

## 📱 Application Screens

### 1. Dashboard Screen
Main protection toggle with active status indicators, animated transitions, and quick settings access.

### 2. Settings Screen
Configure strict domain blocking rules, automatic background cloud updates, dark mode toggle, and view active rule counters.

### 3. Onboarding & System VPN Authorization
Guided setup screen explaining local DNS filtering and requesting native Android `VpnService` permission (`VpnService.prepare`).

---

## 🚀 Getting Started

### Prerequisites

- **Android Studio**: Ladybug / 2024.2+ or Android Studio Build Tooling.
- **JDK**: Java 17 or Java 21.
- **Android SDK**: `compileSdk 37`, `minSdk 24` (Android 7.0+).

### Setup & Build Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/bendeze/clearguard.git
   cd clearguard/android/ClearGuard
   ```

2. **Configure Local Environment**:
   Copy `local.properties.example` to `local.properties`:
   ```bash
   cp local.properties.example local.properties
   ```
   Set your local Android SDK path and optional API backend URL in `local.properties`:
   ```properties
   sdk.dir=/path/to/android/sdk
   BACKEND_BASE_URL=https://api.clearguard.example.com/
   ```

3. **Build Debug APK**:
   ```bash
   ./gradlew app:assembleDebug
   ```

4. **Run Unit Tests**:
   ```bash
   ./gradlew app:testDebugUnitTest
   ```

---

## 📐 Architecture Overview

```text
com.clearguard.app/
│
├── domain/                  # Clean Architecture Domain Layer
│   ├── model/               # Core Domain Enums & Models (ProtectionStatus)
│   └── repository/          # ProtectionRepository & BlocklistRepository Interfaces
│
├── data/                    # Data Layer
│   ├── local/               # Room Database, DAOs & Entities
│   ├── remote/              # Retrofit API Services & Models
│   └── repository/          # Repository Implementations
│
├── service/                 # System Services & Packet Engine
│   ├── ClearGuardVpnService # VpnService Loopback & Packet Filter
│   ├── dns/                 # DnsPacketParser, DomainMatcher, DnsResponseGenerator
│   ├── receiver/            # BootReceiver (Restores protection on device boot)
│   └── work/                # BlocklistSyncWorker (WorkManager Background Sync)
│
├── ui/                      # Jetpack Compose UI
│   ├── dashboard/           # DashboardScreen & DashboardViewModel
│   ├── settings/            # SettingsScreen & SettingsViewModel
│   ├── onboarding/          # OnboardingScreen
│   ├── navigation/          # ClearGuardNavGraph (Jetpack Navigation)
│   └── theme/               # Color Palette, Theme, Typography
│
└── di/                      # Hilt Modules (DatabaseModule, RepositoryModule, NetworkModule)
```

---

## 🤝 Contributing

Contributions are welcome! Please review [CONTRIBUTING.md](CONTRIBUTING.md) for details on code style, commit message conventions, and the pull request process.

---

## 📄 License

This project is open-source and available under the [Apache License 2.0](LICENSE).
