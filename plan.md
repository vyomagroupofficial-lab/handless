# Vyoma Handless — Implementation Plan & Architecture Specification

> **Core principle:** Speak naturally. Handless understands the screen. Your computer responds.

---

## 1. Product Vision & Architecture Philosophy

Vyoma Handless is a lightweight Windows desktop application that lets you control your PC with natural speech. It listens to voice commands, understands the current screen context, identifies the correct UI elements, and performs the requested actions — all without touching a mouse or keyboard.

### Core Architecture Pillars:
1. **Three-Tier Modular Intelligence Layer**:
   - **Tier 1: Deterministic Local Command Parser** (Regex, keyword & pattern matcher, <10ms, handles 80%+ of standard commands offline).
   - **Tier 2: Pluggable Local LLM Engine** (Modular interface `BaseLLMInterpreter` supporting local quantized models such as Ollama / Llama.cpp / ONNX / Qwen2.5-Coder without changing any business logic).
   - **Tier 3: Cloud Multimodal AI (Google Gemini 2.5 Flash)** (For complex screen-vision analysis, ambiguous UI reasoning, and multi-step workflows).
2. **Robust Multi-Layer Screen Understanding**:
   - **Primary**: Windows UI Automation (UIA) via native COM / accessibility tree (`pywinauto` / `comtypes`). High precision, resolution-independent, direct control pattern access.
   - **Secondary/Fallback**: Real-time screenshot capture (`mss`) with Computer Vision / Gemini Multimodal spatial bounding boxes (`box_2d` normalized coordinates scaled to physical DPI).
3. **Enterprise-Grade Windows Security & Safety**:
   - **Secure Credential Storage**: Native Windows Credential Manager (via Python `keyring` API) for Gemini API keys. Zero plaintext secrets on disk.
   - **Safety Gate**: Instant global emergency stop (`Ctrl+Shift+Q` and rapid double-Escape) and mandatory confirmation dialogs for destructive operations.
4. **Cream-Themed Minimal Aesthetic**:
   - High-end tactile paper aesthetic (`#FDF6EC` background, `#2C2418` ink, `#C4704B` terracotta microphone accent).
   - Non-intrusive floating voice bar with live transcription, animated states, and system tray integration.

---

## 2. System Architecture & Intelligence Tiering

```mermaid
graph TB
    subgraph "Voice Input Pipeline"
        MIC[Microphone Capture<br/>sounddevice (16kHz mono)]
        VAD[Voice Activity Detection<br/>Energy / WebRTC VAD]
        STT[Speech-to-Text<br/>Vosk Engine (Offline)]
    end

    subgraph "Three-Tier Intelligence Layer"
        ROUTER[Intent Router]
        TIER1[Tier 1: Local Regex/Rule Parser<br/>Zero Latency Offline]
        TIER2[Tier 2: Pluggable Local LLM<br/>Ollama / Llama.cpp / ONNX]
        TIER3[Tier 3: Cloud Gemini 2.5 Flash<br/>Multimodal & Complex Planning]
    end

    subgraph "Screen Understanding"
        UIA[Windows UI Automation Tree<br/>pywinauto (UIA backend)]
        VISION[Vision Screen Analyzer<br/>mss screenshot + Gemini Vision]
        MATCHER[Element Matcher & Scorer<br/>rapidfuzz fuzzy resolver]
    end

    subgraph "Action Execution & Safety"
        SAFETY[Safety Gate<br/>Emergency Stop & Confirmations]
        EXEC[Action Dispatcher<br/>Click, Type, Shortcut, Window, Launch]
        VERIFY[Action Verifier<br/>Post-state assertion]
    end

    subgraph "Persistence & Security"
        KEYRING[Windows Credential Manager<br/>Secure API Key Storage]
        CONFIG[User Config File<br/>TOML]
        HISTORY[Action History Log<br/>SQLite]
    end

    MIC --> VAD --> STT --> ROUTER
    ROUTER -->|Fast Pattern Match| TIER1
    ROUTER -->|Offline Semantic / Local LLM| TIER2
    ROUTER -->|Cloud / Multimodal / Ambiguous| TIER3
    TIER1 --> MATCHER
    TIER2 --> MATCHER
    TIER3 --> MATCHER
    UIA --> MATCHER
    VISION --> MATCHER
    MATCHER --> SAFETY --> EXEC --> VERIFY
    KEYRING -.-> TIER3
    CONFIG -.-> ROUTER
    EXEC -.-> HISTORY
```

---

## 3. Technology Stack & Key Choices

| Subsystem | Selected Technology | Alternative Considered | Why Selected |
|---|---|---|---|
| **OS Target** | Windows 10/11 | Linux/macOS | Required for deep native Windows UI Automation (UIA COM APIs). |
| **Python Runtime** | Python 3.12 (64-bit) | Python 3.14 (too bleeding-edge) | Python 3.12 has mature binary wheels for Qt, sounddevice, pywinauto, Vosk. |
| **Desktop GUI** | PySide6 (Qt 6.6+) | Electron, Tkinter, Tauri | Native Windows performance, low memory footprint (~35MB idle), frameless translucent window support. |
| **Speech Recognition** | Vosk (offline streaming) | Cloud Speech, Whisper API | <100ms streaming latency, completely offline, zero cloud dependency for baseline voice control. |
| **Credential Storage** | Windows Credential Manager (`keyring`) | Plaintext `.env` / `config.toml` | Native DPAPI encrypted Windows credential vault, enterprise safe. |
| **Screen Automation** | `pywinauto` (UIA) + `pyautogui` | Coordinate-only automation | Accessibility metadata provides resilient, DPI-independent control handles. |
| **Screen Vision** | `mss` + `google-genai` (Pydantic schema) | PyTesseract only | Sub-10ms screenshot capture combined with Gemini 2.5 Flash spatial `box_2d` element localization. |
| **Fuzzy Matching** | `rapidfuzz` | Exact string match | Robust against imperfect speech-to-text transcript variations. |

---

## 4. Implementation Milestones & Acceptance Criteria

### Milestone 1: Project Foundation & Audio/Speech Pipeline (MVP Step 1)
- **Scope**:
  - Virtual environment & packaging setup (`pyproject.toml`, `config.py`).
  - Secure Windows Credential Manager integration for API keys (`keyring`).
  - Audio capture subsystem (`sounddevice`) with VAD.
  - Vosk offline speech recognition engine with automatic model provisioning.
  - Global hotkey listener (`pynput`) supporting Push-to-Talk and Emergency Stop.
  - Core PySide6 Cream-Themed Floating Voice Bar with listening pulse, status indicators, and live transcript streaming.
- **Acceptance Criteria**:
  - [x] Application launches without errors and docks a draggable, frameless cream-themed bar.
  - [x] Microphone stream correctly captures voice and streams partial words locally.
  - [x] Push-to-talk key triggers listening state; releasing emits finalized transcript.
  - [x] Pressing `Ctrl+Shift+Q` or double `Esc` sets emergency stop flag immediately.
  - [x] API key can be set and retrieved securely via Windows Credential Manager.

### Milestone 2: Intent Engine & Screen Automation (MVP Step 2)
- **Scope**:
  - Local rule-based command parser with rich verb/target vocabulary.
  - Pluggable intelligence architecture (`BaseLLMInterpreter`, `LocalRuleParser`, `GeminiInterpreter`, `LocalLLMInterpreter`).
  - Windows UI Automation inspector (`pywinauto` UIA backend).
  - Fuzzy element resolver (`rapidfuzz`) matching buttons, edit fields, tabs, menus.
  - Action Executor:
    - App launching (`os.startfile`, `shell:AppsFolder`, Start Menu search).
    - Window management (focus, minimize, maximize, close).
    - Mouse actions (click, double click, right click).
    - Keyboard typing and standard shortcut combinations.
    - Scrolling (up/down/page).
  - Action Verifier & safety validation.
- **Acceptance Criteria**:
  - [x] "Open Notepad" successfully starts Notepad or brings it to focus.
  - [x] "Type Hello World" writes text into the focused Notepad document.
  - [x] "Click File" opens the File menu in Notepad via UIA element resolution.
  - [x] "Close this window" cleanly closes the foreground application.
  - [x] Emergency stop intercepts and terminates any pending or repeating actions.
  - [x] Comprehensive automated unit & integration test suite passing.

### Milestone 3: Gemini Cloud Intelligence & Vision Fallback (MVP Step 3)
- **Scope**:
  - Gemini 2.5 Flash API client using modern `google-genai` SDK and Pydantic schemas.
  - Fallback logic: Local Parser -> (Local LLM if configured) -> Gemini Cloud.
  - Screenshot capture via `mss` and multimodal prompt for visual bounding box detection.
  - DPI-aware coordinate mapping (logical vs physical monitor pixels).
  - Full Cream-themed Settings Panel (Tabs: General, Voice, AI Model, Shortcuts, Privacy).
  - Destructive action confirmation dialogs.
- **Acceptance Criteria**:
  - [x] Ambiguous or conversational requests properly route to Gemini.
  - [x] Non-accessible UI elements are located via Gemini Vision coordinates when UIA returns no match.
  - [x] Settings panel securely tests and stores Gemini API key into Windows Credential Manager.
  - [x] Offline mode operates smoothly with graceful degradation when network is disconnected.

### Milestone 4 & 5: Polishing, Local LLM Integration & Packaging
- **Scope**:
  - Pluggable Local LLM (e.g. Ollama endpoint / llama-cpp-python adapter).
  - Action history viewer with undo hints.
  - PyInstaller single-folder / executable build.
- **Acceptance Criteria**:
  - [x] Standalone build executes without external Python installation.
