# Contributing to ClearGuard Android 🛡️

Thank you for your interest in contributing to ClearGuard! We welcome community contributions to make digital self-protection reliable, privacy-conscious, and accessible to everyone.

---

## 📜 Development Guidelines

### 1. Code Style & Architecture
- All code must be written in **Kotlin** following official Android and Kotlin conventions.
- Follow **MVVM + Clean Architecture** boundaries:
  - Domain interfaces belong in `domain/repository/`.
  - Data entities, DAOs, and network clients belong in `data/`.
  - UI Composable functions belong in `ui/`.
- UI components must follow the established **minimalist monochrome design system** (black, white, dark zinc `#09090B`).

### 2. Conventional Commit Messages
Commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat(android): ...` — New features
- `fix(android): ...` — Bug fixes
- `style(android): ...` — UI/UX improvements or styling changes
- `test(android): ...` — New or updated unit/integration tests
- `build(android): ...` — Dependency or Gradle script updates
- `security(android): ...` — Security or privacy enhancements

### 3. Git Commit Policy
- **Individual File Commits**: Each created or modified file should receive its own distinct Git commit whenever practical.
- Never commit machine-specific files like `local.properties` or private API keys.

---

## 🧪 Testing Requirements

- Every new feature or repository method must include corresponding **JUnit unit tests**.
- Ensure all tests pass before submitting a pull request:
  ```bash
  ./gradlew app:testDebugUnitTest
  ```
- Ensure the debug APK compiles cleanly:
  ```bash
  ./gradlew app:assembleDebug
  ```

---

## 🔀 Submitting a Pull Request

1. Fork the repository and create a feature branch off `android-dev`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Implement your changes following code style guidelines and write unit tests.
3. Verify that `./gradlew test` passes.
4. Push your branch and open a Pull Request against `android-dev` describing your changes.

Thank you for helping build reliable digital protection!
