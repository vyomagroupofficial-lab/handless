# Vyoma Handless

> Speak naturally. Handless understands the screen. Your computer responds.

A lightweight, intelligent Windows desktop application that lets you control your PC using your voice instead of manually operating the mouse and keyboard.

## Key Features

- **Local Speech Recognition**: Offline voice input powered by Vosk.
- **Windows UI Automation**: Deep accessibility tree integration to click, type, and navigate desktop controls reliably without fragile static mouse coordinates.
- **Three-Tier Intelligence**:
  1. *Tier 1 (Local Rules)*: Sub-10ms deterministic command parsing for standard actions.
  2. *Tier 2 (Local LLM)*: Pluggable offline LLM engine (Ollama/Llama.cpp).
  3. *Tier 3 (Google Gemini 2.5 Flash)*: Cloud multimodal reasoning and screen-vision fallback.
- **Secure Windows Credential Storage**: Native Windows Credential Manager storage for API keys (`keyring`).
- **Emergency Stop**: Global hotkey (`Ctrl+Shift+Q` or double `Escape`) to instantly stop any in-flight actions.
- **Cream & Paper Minimal Aesthetic**: Frameless, elegant floating control bar designed with high-end stationery vibes.

## Running Locally

```powershell
.\.venv\Scripts\activate
python -m handless.app
```
