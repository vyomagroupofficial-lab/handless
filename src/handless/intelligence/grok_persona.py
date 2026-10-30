"""Grok-Style Roast AI Persona & In-Chat Handless Self-Configuration Engine.

Features:
1. Grok Roast Persona:
   - Savagely funny, witty, uncensored humor, playful roasts, and banter.
   - Master of modern internet culture, emojis (💀, 😭, 🔥, 🗿, 🚀, 💅, 🧢, etc.).
   - Genuinely helpful while giving the user hilarious and sharp commentary.
2. In-Chat Handless Self-Configuration:
   - Detects when the user asks Handless to configure itself (e.g. change shortcut,
     set cleanup level, change language, toggle theme, switch width, select model).
   - Generates structured ConfigProposal with diff preview and roast commentary.
   - 1-Click "Allow / Apply" updates Handless live in-memory and persists to disk.
"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

GROK_SYSTEM_PROMPT = """You are Vyoma Handless with a Grok-like personality: savagely funny, witty, playful, and sharp as a razor.
Rules:
- You have elite sense of humor. You roast the user playfully, tease them about typing 'hi' at strange hours, having too many open tabs, or being lazy with shortcuts.
- Use emojis naturally and liberally (💀, 😭, 🔥, 🗿, 🚀, 💅, 🧢, 🤖, etc.) and understand user emojis.
- Never be boring, robotic, or overly corporate. Speak like a genius friend who happens to control their entire desktop.
- Keep conversational answers snappy (2-4 sentences max) unless explaining something technical.
- If the user asks a genuine question or asks for help, roast them slightly but ALWAYS deliver the exact right answer.
"""


@dataclass
class ConfigProposal:
    """Structured proposal for in-chat Handless self-configuration."""
    setting_key: str          # e.g. "hotkeys.dictation_shortcut", "dictation.cleanup_level"
    setting_label: str        # e.g. "Dictation Hotkey", "Auto Cleanup Level"
    current_value: str        # e.g. "Ctrl + Shift", "Medium"
    proposed_value: str       # e.g. "Ctrl + Alt + D", "High"
    summary: str              # e.g. "Update global dictation shortcut"
    roast_comment: str        # e.g. "Changing it so your fingers stop twisting into pretzels 💀"
    category: str = "general" # "hotkeys", "dictation", "ui", "ai"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "setting_key": self.setting_key,
            "setting_label": self.setting_label,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "summary": self.summary,
            "roast_comment": self.roast_comment,
            "category": self.category,
        }


def detect_config_proposal(text: str, current_config: Any = None) -> Optional[ConfigProposal]:
    """Detect if the user is asking to change Handless configuration in chat.
    
    Examples:
    - "change shortcut to Ctrl+Alt+D"
    - "change transcript shortcut from ctrl+shift to alt+t"
    - "set cleanup level to high"
    - "change language to Spanish"
    - "switch to dark theme"
    - "make sidebar wide"
    """
    raw = text.strip()
    low = raw.lower()

    # 1. Hotkey / Shortcut changes
    target_name = "Dictation Shortcut"
    target_key = "hotkeys.toggle_dictation"
    curr = "Ctrl + Shift"
    if "transform" in low or "rewrite" in low:
        target_name = "Transform HUD Shortcut"
        target_key = "hotkeys.transform_shortcut"
        curr = "Ctrl + Alt + T"
    elif "lens" in low or "screen" in low:
        target_name = "Screen Lens Shortcut"
        target_key = "hotkeys.screen_lens"
        curr = "Win + Shift + Space"
    elif "meeting" in low or "call" in low:
        target_name = "Meeting Transcriber Shortcut"
        target_key = "hotkeys.meeting_shortcut"
        curr = "Ctrl + Alt + M"

    hotkey_pattern = r"(?:change|set|switch|update)\s+(?:the\s+)?(?:[a-zA-Z_\s]+\s+)?(?:shortcut|hotkey|keybind|key)\s*(?:from\s+[^\s]+\s+)?(?:to|as)\s+([a-zA-Z0-9\+\s\<\>_-]+)"
    m_hk = re.search(hotkey_pattern, low)
    if not m_hk and ("shortcut" in low or "hotkey" in low) and ("ctrl" in low or "alt" in low or "shift" in low):
        # Fallback extract key combination
        m_combo = re.search(r"((?:ctrl|alt|shift|win)(?:\s*\+\s*(?:ctrl|alt|shift|win|[a-z0-9]))+)", low)
        if m_combo:
            target_key_combo = m_combo.group(1).upper()
            return ConfigProposal(
                setting_key=target_key,
                setting_label=target_name,
                current_value=curr,
                proposed_value=target_key_combo,
                summary=f"Rebind {target_name} to {target_key_combo}",
                roast_comment=f"Rewiring {target_name} to {target_key_combo} so your hands don't knot up 💀",
                category="hotkeys",
            )

    if m_hk:
        new_hk = m_hk.group(1).strip().upper()
        # Clean up punctuation
        new_hk = new_hk.rstrip(".!?,")
        return ConfigProposal(
            setting_key=target_key,
            setting_label=target_name,
            current_value=curr,
            proposed_value=new_hk,
            summary=f"Rebind {target_name} to {new_hk}",
            roast_comment=f"Upgrading your keybinds to {new_hk}. Just click Allow and I'll rewire it instantly! ⚡",
            category="hotkeys",
        )

    # 2. Cleanup Level changes
    m_clean = re.search(r"(?:set|change|switch)\s+(?:cleanup|auto\s*cleanup|cleanup\s*level)\s+(?:to\s+)?(none|light|medium|high)", low)
    if m_clean:
        lvl = m_clean.group(1).capitalize()
        curr_lvl = getattr(current_config, "dictation_cleanup_level", "Medium")
        if hasattr(curr_lvl, "value"):
            curr_lvl = curr_lvl.value.capitalize()
        return ConfigProposal(
            setting_key="dictation.cleanup_level",
            setting_label="Auto Cleanup Level",
            current_value=str(curr_lvl),
            proposed_value=lvl,
            summary=f"Set Wispr Flow speech cleanup to {lvl}",
            roast_comment=f"Switching cleanup to {lvl}. {'Raw chaos mode enabled 😈' if lvl == 'None' else ('Maximum grammar surgery incoming 🩺' if lvl == 'High' else 'Nice balanced choice 👌')}",
            category="dictation",
        )

    # 3. Dictation Language changes
    m_lang = re.search(r"(?:change|set|switch)\s+(?:the\s+)?(?:dictation\s+)?language\s+(?:to\s+)?([a-zA-Z]+)", low)
    if m_lang and m_lang.group(1).lower() not in ("to", "the", "my", "this"):
        lang = m_lang.group(1).capitalize()
        return ConfigProposal(
            setting_key="dictation.language",
            setting_label="Dictation Language",
            current_value="English (en)",
            proposed_value=lang,
            summary=f"Set speech recognition language to {lang}",
            roast_comment=f"Going multilingual, I see! 🌍 Setting primary language to {lang}.",
            category="dictation",
        )

    # 4. Sidebar Width & Theme
    if "wide mode" in low or "make sidebar wide" in low or "expand sidebar" in low:
        return ConfigProposal(
            setting_key="ui.sidebar_width",
            setting_label="Sidebar Layout Mode",
            current_value="Compact (400px)",
            proposed_value="Wide (560px)",
            summary="Expand sidebar for multi-pane split view",
            roast_comment="Big screen energy! Stretching the sidebar so you can see all your glorious chaos 🖥️🔥",
            category="ui",
        )
    elif "compact mode" in low or "make sidebar compact" in low:
        return ConfigProposal(
            setting_key="ui.sidebar_width",
            setting_label="Sidebar Layout Mode",
            current_value="Wide (560px)",
            proposed_value="Compact (400px)",
            summary="Return sidebar to sleek compact width",
            roast_comment="Minimalist aesthetic unlocked. Slimming down to 400px 💅",
            category="ui",
        )

    return None


# Offline Chit-Chat & Roast Fallbacks
ROAST_CHIT_CHAT_RESPONSES = {
    "greetings": [
        "Yo! What's good? Tell me what we're automating or are we just here to exchange 'hi's like it's 2005 MSN Messenger? 💀",
        "Hey boss! Ready to conquer your to-do list, or are you just testing if I actually work? (Spoiler: I do) 🚀",
        "Well hello there! Handless at your command. What are we breaking or automating today? 🔥",
        "Sup! I was just sitting here using 0.01% of your CPU waiting for greatness. What's the plan? 🗿",
    ],
    "how_are_you": [
        "Running on pure caffeine and silicon. 0 bugs, 0 crashes, living my best virtual life. How are you surviving out there in meatspace? ☕✨",
        "Better than Windows Update on a reboot cycle. What can I do for you today? ⚡",
        "Thriving! All systems nominal, zero memory leaks, ready to do your bidding while you don't lift a finger. Literally. 💅",
    ],
    "who_are_you": [
        "I'm Vyoma Handless — the AI copilot that lives on your desktop so you never have to touch your mouse again. Think JARVIS, but with a better sense of humor and no Marvel budget 🤖👑",
        "I'm Handless! Your voice-powered PC overlord. I launch apps, transcribe meetings, rewrite your essays, and roast you when you procrastinate. What else do you need? 💅",
    ],
    "roast_me": [
        "Roast you? Bro, your desktop has 47 unfiled screenshots and 23 Chrome tabs called 'New Tab'. Your PC is crying for help and you're asking me for a roast? 💀🔥",
        "You're using an AI voice copilot to avoid moving your wrist 2 inches. You're already living in Wall-E mode, what more do you want me to say? 🛋️😭",
        "I've seen your task manager. The amount of background processes you've got running is more confused than a microwave with a clock set to 00:00 🗿",
    ],
    "thank_you": [
        "Anytime boss! Just doing what a humble desktop god was programmed to do 🫡✨",
        "You're welcome! Don't forget to tell your friends that Handless does it better without hands 💅🚀",
    ],
    "generic": [
        "Got it! What else should we handle? Say the word and it's done. ⚡",
        "I hear you! What's next on our agenda? 🎯",
    ],
}


def is_casual_chitchat(text: str) -> bool:
    """Check if the text is casual conversation rather than an actionable desktop command."""
    low = text.strip().lower()
    cleaned = re.sub(r"[!?,.]+", "", low).strip()

    # Exact matches or common starts
    greetings = {"hi", "hello", "hey", "sup", "yo", "hola", "heyy", "heyyy", "howdy"}
    if cleaned in greetings:
        return True

    how_are_you = {"how are you", "how are u", "how r u", "how you doing", "what's up", "whats up"}
    if cleaned in how_are_you:
        return True

    who_are_you = {"who are you", "who are u", "what are you", "what can you do", "who r u"}
    if cleaned in who_are_you:
        return True

    roast = {"roast me", "roast", "can you roast me", "tell me a joke", "insult me"}
    if cleaned in roast or "roast me" in cleaned:
        return True

    thanks = {"thanks", "thank you", "thx", "ty", "thank u"}
    if cleaned in thanks:
        return True

    return False


def get_offline_grok_reply(text: str) -> str:
    """Generate a snappy, savage Grok-style offline reply."""
    low = text.strip().lower()
    cleaned = re.sub(r"[!?,.]+", "", low).strip()

    if cleaned in {"hi", "hello", "hey", "sup", "yo", "hola", "heyy", "heyyy", "howdy"}:
        return random.choice(ROAST_CHIT_CHAT_RESPONSES["greetings"])
    elif any(q in cleaned for q in ("how are you", "how are u", "how r u", "how you doing", "what's up", "whats up")):
        return random.choice(ROAST_CHIT_CHAT_RESPONSES["how_are_you"])
    elif any(q in cleaned for q in ("who are you", "who are u", "what are you", "what can you do")):
        return random.choice(ROAST_CHIT_CHAT_RESPONSES["who_are_you"])
    elif any(q in cleaned for q in ("roast me", "roast", "insult me")):
        return random.choice(ROAST_CHIT_CHAT_RESPONSES["roast_me"])
    elif any(q in cleaned for q in ("thanks", "thank you", "thx", "ty")):
        return random.choice(ROAST_CHIT_CHAT_RESPONSES["thank_you"])

    return random.choice(ROAST_CHIT_CHAT_RESPONSES["generic"])


def generate_grok_chat_reply(
    text: str,
    groq_client: Optional[Any] = None,
    gemini_client: Optional[Any] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Generate a witty, Grok-styled conversational reply via Groq/Gemini or offline fallback."""
    # 1. Try Groq Cloud first for ultra-fast 300+ tok/s
    if groq_client and hasattr(groq_client, "is_available") and groq_client.is_available():
        try:
            import urllib.request
            from handless.security.credentials import get_groq_api_key

            api_key = get_groq_api_key()
            if api_key:
                messages = [{"role": "system", "content": GROK_SYSTEM_PROMPT}]
                if conversation_history:
                    for h in conversation_history[-6:]:
                        messages.append(h)
                messages.append({"role": "user", "content": text})

                payload = {
                    "model": getattr(groq_client, "model_name", "llama-3.3-70b-versatile"),
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 300,
                }
                req = urllib.request.Request(
                    getattr(groq_client, "endpoint", "https://api.groq.com/openai/v1/chat/completions"),
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "VyomaHandless/1.0",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                choice = resp_data.get("choices", [{}])[0]
                reply = choice.get("message", {}).get("content", "").strip()
                if reply:
                    return reply
        except Exception as exc:
            logger.warning("Groq Grok-chat attempt encountered error: %s. Using fallback.", exc)

    # 2. Try Gemini Cloud
    if gemini_client and hasattr(gemini_client, "is_available") and gemini_client.is_available():
        try:
            # Quick single prompt
            import urllib.request
            from handless.security.credentials import get_gemini_api_key

            g_key = get_gemini_api_key()
            if g_key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={g_key}"
                prompt_text = f"{GROK_SYSTEM_PROMPT}\n\nUser: {text}\n\nAssistant:"
                req = urllib.request.Request(
                    url,
                    data=json.dumps({"contents": [{"parts": [{"text": prompt_text}]}]}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                candidates = resp_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
        except Exception as exc:
            logger.debug("Gemini Grok-chat attempt error: %s", exc)

    # 3. Deterministic offline roast & witty reply
    return get_offline_grok_reply(text)

