# Contributing to Vyoma Handless™

Thank you for your interest in contributing to **Vyoma Handless**! We welcome bug fixes, documentation improvements, new voice command grammars, and feature enhancements from the open-source community.

---

## 🛠️ Development Setup

1. **Fork and clone the repository:**
   ```powershell
   git clone https://github.com/<your-username>/handless.git
   cd handless
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Install development dependencies in editable mode:**
   ```powershell
   pip install -e ".[dev]"
   ```

4. **Verify your local installation:**
   ```powershell
   pytest -q
   # All tests should pass cleanly
   ```

---

## 🧪 Testing Guidelines

* Every bug fix or new feature must be accompanied by corresponding unit or integration tests in `tests/`.
* When writing tests for Windows UI Automation, use mocked objects or the `offscreen` Qt QPA platform:
  ```powershell
  $env:QT_QPA_PLATFORM="offscreen"
  pytest -q
  ```
* Ensure all tests pass with zero warnings or failures before opening a pull request.

---

## 📐 Coding Standards

* **Type Annotations**: All new Python functions, methods, and classes must include static type hints (`typing` / `from __future__ import annotations`).
* **Architecture Integrity**:
  * Voice commands must follow the three-tier routing strategy (Tier 1 deterministic regex $\to$ Tier 2 local LLM $\to$ Tier 3 Groq/Gemini).
  * Direct hardware controls should be routed through `SystemTools` or `SystemController` with clean thread safety.
* **Preserve Documentation**: Maintain comments, docstrings, and architectural explanations.

---

## 🚀 Submitting a Pull Request

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. Commit your changes with conventional commit messages:
   ```bash
   git commit -m "feat(dictation): add support for custom text expansion macros"
   ```
3. Push to your fork and open a Pull Request against `main` on [vyomagroupofficial-lab/handless](https://github.com/vyomagroupofficial-lab/handless).
4. Fill out the PR description template with testing steps and screenshots if UI changes are involved.

---

## 💬 Community & Questions

Have questions or want to discuss architecture ideas before coding? Open a discussion on GitHub or reach out to the Vyoma team!

