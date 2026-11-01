# Contributing to Galaxy S9+ Recovery & HDMI Control Suite

Thank you for your interest in contributing! Whether you are reporting a hardware compatibility finding, adding support for more Samsung/Android models, fixing a bug, or polishing the UI, contributions are warmly welcomed.

---

## 🛠️ Development Setup

1. **Fork & Clone**:
   ```bash
   git clone https://github.com/rustyy1/-s9-plus-recovery-suite.git
   cd -s9-plus-recovery-suite
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # Or Command Prompt:
   venv\Scripts\activate.bat
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov
   ```

4. **Verify Test Suite**:
   ```bash
   pytest -v
   ```
   All 58 existing unit tests should pass with zero hardware connected (hardware interactions are mocked in `tests/`).

---

## 📝 Guidelines

- **Zero-Bypass Policy**: Do not bypass security boundaries, authorization checks, or system integrity rules.
- **Hardware Agnostic Testing**: Any new backend feature (ADB commands, UVC queries, USB detection) should include unit tests with mocked subprocess/multimedia calls.
- **Code Style**: Follow PEP 8 guidelines. Keep functions modular and clearly documented.
- **Preserve Documentation**: Maintain docstrings and update corresponding sections in `README.md` or `feasibility_report.md` when behavior changes.

---

## 🚀 Submitting Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Commit your changes with a meaningful message:
   ```bash
   git commit -m "feat: add support for Galaxy S10 DP Alt Mode switching"
   ```
3. Push to your branch and open a **Pull Request** targeting `main`.
