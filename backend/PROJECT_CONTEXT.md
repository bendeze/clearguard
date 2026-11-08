# ClearGuard — Project Context

> **Product:** ClearGuard  
> **Repository:** `clearguard`  
> **Document:** Project Context  
> **Status:** Initial project definition  
> **Product category:** Android Digital Protection  
> **Primary objective:** Adult-content filtering and self-protection

---

## 1. Project Overview

ClearGuard is an Android application designed to help individuals protect themselves from pornography and other adult content accessible through their mobile devices.

The primary objective is to provide reliable, system-wide adult-content filtering using a combination of network-level filtering, local protection mechanisms, and intelligent content classification as the project evolves.

ClearGuard aims to make accessing adult content significantly more difficult while maintaining user privacy, device performance, and a straightforward user experience.

The project consists of two primary components:

1. **Android Mobile Application:** Responsible for enforcing protection directly on the Android device.
2. **Python Backend:** Responsible for managing filtering intelligence, distributing blocklists, and providing supporting APIs and future classification services.

Both components are maintained in a single Git repository (monorepo), but developed independently using their respective development environments and AI coding agents.

## 2. Product Vision

To provide individuals with an accessible, reliable, and privacy-conscious tool that helps them maintain control over their digital environment.

ClearGuard is designed around three principles:

- **Protection:** Reduce exposure and access to pornography and adult content.
- **Privacy:** Minimize the collection and transmission of personal information.
- **Reliability:** Maintain protection even when internet connectivity or backend services are unavailable.

## 3. Target Users and Product Scope

### 3.1 Target Users

The initial target audience is individuals who voluntarily want to protect themselves from pornography and adult content.

The initial product is not designed as a parental-control platform or an employee-monitoring solution.

### 3.2 Product Scope

The initial scope focuses exclusively on adult-content protection.

This includes:

- Blocking known pornographic and adult websites.
- Filtering adult domains across applications using local network filtering.
- Maintaining and updating adult-domain blocklists.
- Supporting safer search configurations where technically possible.
- Providing visibility into the protection status.
- Supporting offline filtering through locally stored rules.

Future versions may introduce on-device AI-based detection of explicit images and other content that cannot be identified through domain filtering alone.

### 3.3 Out of Scope for the Initial MVP

The following features are not part of the initial Minimum Viable Product:

- Parental control and child monitoring.
- General-purpose website blocking.
- Gambling and social media restrictions.
- Cloud-based browsing surveillance.
- Explicit video recognition.
- AI-based image classification.
- Subscription and payment management.

These features must not be introduced without an explicit product decision.

## 4. Technology Stack

### 4.1 Android Application

| Component | Technology |
|---|---|
| Programming language | Kotlin |
| Development environment | Android Studio |
| UI framework | Jetpack Compose |
| Application architecture | MVVM with clean architecture principles |
| Dependency injection | Hilt |
| Local database | Room / SQLite |
| Background operations | WorkManager |
| Network filtering | Android VpnService |
| DNS filtering | Local DNS filtering engine |
| Local AI inference | ONNX Runtime (future consideration) |

### 4.2 Backend

| Component | Technology |
|---|---|
| Programming language | Python |
| Framework | FastAPI |
| Python environment and package manager | uv |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2 |
| Database migrations | Alembic |
| Testing | Pytest |
| Containerization | Docker |

### 4.3 Supporting Technologies

- Git and GitHub for version control.
- GitHub Actions for CI/CD.
- Markdown for technical documentation.
- Docker for backend development and deployment.

Technology choices may evolve through documented architectural decisions.

## 5. High-Level System Architecture

ClearGuard follows a hybrid, offline-first architecture.

The Android application is the primary protection component. The backend provides supporting intelligence and synchronization services.

### 5.1 Android Application Responsibilities

The Android application is responsible for:

- Presenting the user interface.
- Managing protection settings.
- Requesting and managing Android VPN permissions.
- Running the local VPN protection service.
- Handling DNS requests and applying filtering rules.
- Maintaining locally available blocklists.
- Synchronizing filtering rules with the backend.
- Displaying protection status and relevant statistics.
- Managing local application data.

### 5.2 Backend Responsibilities

The backend is responsible for:

- Providing REST APIs.
- Managing adult-domain filtering datasets.
- Publishing and versioning blocklists.
- Providing updated filtering intelligence.
- Managing synchronization between the application and backend.
- Supporting future content-classification services.
- Providing appropriate administrative and monitoring capabilities.

### 5.3 Offline-First Principle

The Android application MUST NOT depend on the backend for real-time filtering decisions.

Essential filtering must continue when:

- The device has no internet connection.
- The backend is unavailable.
- Synchronization fails.
- The user temporarily loses access to the server.

The backend should provide updates, not become a single point of failure for device protection.

## 6. Core Functional Requirements

The initial product should progressively implement the following capabilities.

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Activate and deactivate protection | Must |
| FR-02 | Block known adult websites | Must |
| FR-03 | Perform local DNS filtering | Must |
| FR-04 | Maintain locally available blocklists | Must |
| FR-05 | Display protection status | Must |
| FR-06 | Operate offline using cached rules | Must |
| FR-07 | Configure protection settings | Must |
| FR-08 | Synchronize blocklists with backend | Must |
| FR-09 | Support safer search configurations | Should |
| FR-10 | Provide basic protection statistics | Later |
| FR-11 | Detect explicit images using on-device AI | Later |

Priorities indicate implementation order, not permission to sacrifice reliability or security.

## 7. Security and Privacy Principles

Security and privacy are fundamental requirements, not optional enhancements.

All components must follow these principles:

1. Do not collect detailed browsing history by default.
2. Do not transmit browsing activity to the backend unnecessarily.
3. Use HTTPS for communication with remote services.
4. Store sensitive information securely.
5. Validate and sanitize all incoming API data.
6. Apply appropriate authentication and authorization when user accounts are introduced.
7. Avoid unnecessary Android permissions.
8. Clearly explain why Android permissions are required.
9. Make protection status transparent to the user.
10. Never implement hidden surveillance or unauthorized monitoring.

The application must also clearly communicate that no filtering solution can guarantee detection of every adult-content source.

## 8. Repository Organization

The repository uses a monorepo structure.

```text
clearguard/
│
├── android/
│   ├── PROJECT_CONTEXT.md
│   └── app/
│
├── backend/
│   ├── PROJECT_CONTEXT.md
│   └── app/
│
├── ml/
│
├── data/
│
├── infrastructure/
│
├── docs/
│
├── scripts/
│
├── .github/
│
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── .gitignore
```

Each primary component maintains its own implementation, dependencies, tests, and development documentation.

## 9. Development Guidelines for AI Coding Agents

This project is developed with assistance from separate AI coding agents working in different IDEs.

All agents must respect the following guidelines:

### 9.1 General Rules

- Read this document before making implementation decisions.
- Respect the established product scope.
- Do not introduce unnecessary dependencies.
- Prefer simple, modular, maintainable implementations.
- Follow the existing architecture and naming conventions.
- Write tests for important functionality.
- Document significant architectural decisions.
- Do not assume that an unimplemented feature already exists.
- Do not introduce breaking changes without explaining their impact.
- Ask for clarification when a requirement is ambiguous or requires a significant architectural decision.

### 9.2 Android Agent Responsibilities

The Android development agent is responsible for everything inside the `android/` directory.

Its primary focus is:

- Native Android development.
- Kotlin and Jetpack Compose.
- VPN service implementation.
- DNS filtering.
- Local storage.
- Android permissions and lifecycle management.
- Mobile application testing.

The Android agent must not independently redesign backend architecture or introduce backend dependencies into the local filtering engine.

### 9.3 Backend Agent Responsibilities

The backend development agent is responsible for everything inside the `backend/` directory.

Its primary focus is:

- FastAPI application development.
- API design and implementation.
- Domain intelligence and blocklist management.
- PostgreSQL integration.
- Database migrations.
- API validation and security.
- Backend testing and deployment preparation.

The backend agent must not assume that the mobile application requires an active backend connection to enforce protection.

### 9.4 Cross-Component Communication

Any functionality requiring communication between Android and backend must use documented API contracts.

Changes to shared interfaces must be communicated through the repository documentation.

The backend and Android agents must not independently invent incompatible API endpoints, request formats, response structures, or synchronization mechanisms.

## 10. Current Development Status

The project is currently in its initial planning and foundation stage.

Established decisions:

- Product name: ClearGuard.
- Repository name: `clearguard`.
- Product scope: Pornography and adult-content protection.
- Initial target audience: Individual users protecting themselves.
- Repository strategy: Monorepo.
- Mobile development: Kotlin and Android Studio.
- Backend development: Python and FastAPI.
- Architecture direction: Hybrid and offline-first.
- Initial filtering direction: Local VPN and DNS-based filtering.

Technical details that remain subject to explicit decisions include:

- Minimum supported Android API level.
- Final VPN and DNS implementation strategy.
- Backend deployment environment.
- Authentication requirements.
- Blocklist sources and update policies.
- Detailed API contracts.
- AI model selection and deployment strategy.

Do not treat these undecided items as finalized requirements.

## 11. Project Success Criteria

The initial MVP will be considered successful when:

1. The Android application can be installed and configured.
2. The user can activate protection through the application.
3. The local VPN service can operate correctly.
4. Known adult domains are successfully blocked.
5. Filtering continues without backend connectivity.
6. Blocklists can be updated from the backend.
7. The application provides clear feedback about its protection status.
8. Core filtering and synchronization functionality has automated tests.
9. The application does not unnecessarily collect personal browsing information.

## 12. Final Development Principle

ClearGuard must prioritize reliable protection, user privacy, maintainability, and transparent operation.

Every implementation decision should support these objectives.

Build the core protection mechanism first. Introduce additional intelligence, automation, and advanced content classification only when the underlying protection system is stable.

**ClearGuard — Protect your digital environment.**