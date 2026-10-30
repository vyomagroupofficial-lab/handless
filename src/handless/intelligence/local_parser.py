"""Tier 1: Deterministic Local Rule-Based Command Parser.

Executes offline in <10ms with zero latency for standard voice commands.
Covers app launching, clicking, typing, scrolling, window control, fundamental PC controls
(volume, media, lock, power, shell, snapping, desktops, browser navigation), and shortcuts.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from ..dictation.text_cleaner import clean_spoken_text
from .base import BaseIntentInterpreter
from .models import ActionRequest, ActionType, IntentResult, WindowActionType

logger = logging.getLogger(__name__)


class LocalRuleParser(BaseIntentInterpreter):
    """Deterministic local rule parser for ultra-fast, zero-cloud execution."""

    @property
    def name(self) -> str:
        return "local_rule"

    def is_available(self) -> bool:
        return True

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = text.strip().lower()
        if not cleaned:
            return ""
        # 1. Strip trailing punctuation
        cleaned = cleaned.rstrip(".!?,")
        
        # 2. Strip conversational prefixes
        conversational_prefixes = (
            r"^(?:ok|okay|now|hey|hi|hello|please|can you|can u|could you|would you|"
            r"just|so|and now|vyoma|hey vyoma|bro|handless|hey handless|go ahead and|"
            r"i want you to|help me|alright|right now)\b[\s,]*"
        )
        while True:
            new_cleaned = re.sub(conversational_prefixes, "", cleaned, flags=re.IGNORECASE).strip()
            if new_cleaned == cleaned or not new_cleaned:
                break
            cleaned = new_cleaned

        # 3. Strip conversational suffixes
        conversational_suffixes = (
            r"[\s,]+(?:ok|okay|please|right now|thanks|thank you|bro|now)$"
        )
        cleaned = re.sub(conversational_suffixes, "", cleaned, flags=re.IGNORECASE).strip()

        # 4. Normalize common STT speech transcription typos
        typo_map = {
            r"\bprfile\b": "profile",
            r"\bprofle\b": "profile",
            r"\bprofl\b": "profile",
            r"\bproifle\b": "profile",
            r"\bchorme\b": "chrome",
            r"\bchrom\b": "chrome",
            r"\byotube\b": "youtube",
            r"\byoutub\b": "youtube",
            r"\baniravity\b": "antigravity",
            r"\bantigravty\b": "antigravity",
            r"\bseletion\b": "selection",
            r"\bselction\b": "selection",
        }
        for pattern, repl in typo_map.items():
            cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)

        return cleaned

    def interpret(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[IntentResult]:
        cleaned = self._clean_text(transcript)
        if not cleaned:
            return None

        # -------------------------------------------------------------------
        # High-Priority WhatsApp & Messaging Intent Handling
        # -------------------------------------------------------------------
        # 1. Compound Contact Selection & Message Typing/Sending
        # e.g. "select vaishu and type hi to her", "select vaishu and send her hi", "type vaishu and send her hi"
        m_msg_compound = re.match(
            r"^(?:in\s+whatsapp\s+|on\s+whatsapp\s+|inside\s+whatsapp\s+)?"
            r"(?:(?:select|choose|click|open\s+(?:chat\s+with\s+)?|search\s+for|search|find|type)\s+([a-zA-Z0-9_\s]+?))\s+"
            r"(?:and\s+then\s+|then\s+|and\s+)"
            r"(type|write|input|send|message)\s+(?:(?:to\s+)?(?:her|him|them|\1)\s+)?(.+?)"
            r"(?:\s+to\s+(?:her|him|them|\1))?"
            r"(?:\s+(?:and\s+wait(?:\s+for\s+me)?(?:\s+to\s+send)?))?$",
            cleaned,
            re.IGNORECASE,
        )
        if m_msg_compound:
            contact = m_msg_compound.group(1).strip()
            verb = m_msg_compound.group(2).lower()
            raw_msg = m_msg_compound.group(3).strip()
            # Clean leading saying/that and trailing pronouns
            raw_msg = re.sub(r"^(?:saying|that)\s+", "", raw_msg, flags=re.IGNORECASE).strip()
            raw_msg = re.sub(r"\s+(?:to\s+)?(?:her|him|them|[a-zA-Z0-9_]+)$", "", raw_msg, flags=re.IGNORECASE).strip()
            msg_text = clean_spoken_text(raw_msg, capitalize_first=False)
            is_send = verb in ("send", "message") or any(s in raw_msg.lower().split()[-3:] for s in ("send", "send it"))

            actions = [
                ActionRequest(action_type=ActionType.CLICK, target=contact, target_type="contact"),
                ActionRequest(action_type=ActionType.CLICK, target="Type a message", target_type="edit"),
                ActionRequest(action_type=ActionType.TYPE, text=msg_text, target="Type a message"),
            ]
            if is_send:
                actions.append(ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"))

            reasoning = f"Select contact '{contact}', focus message box, and {'send' if is_send else 'type'} '{msg_text}'"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.96,
                actions=actions,
                reasoning=reasoning,
            )

        # 2. "send <msg> to <contact>"
        m_send_to = re.match(
            r"^(?:in\s+whatsapp\s+|on\s+whatsapp\s+|inside\s+whatsapp\s+)?"
            r"(?:send|message)\s+(.+?)\s+to\s+([a-zA-Z0-9_\s]+)$",
            cleaned,
            re.IGNORECASE,
        )
        if m_send_to:
            raw_msg = m_send_to.group(1).strip()
            contact = m_send_to.group(2).strip()
            if contact not in ("her", "him", "them", "me"):
                raw_msg = re.sub(r"^(?:saying|that)\s+", "", raw_msg, flags=re.IGNORECASE).strip()
                msg_text = clean_spoken_text(raw_msg, capitalize_first=False)
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.96,
                    actions=[
                        ActionRequest(action_type=ActionType.CLICK, target=contact, target_type="contact"),
                        ActionRequest(action_type=ActionType.CLICK, target="Type a message", target_type="edit"),
                        ActionRequest(action_type=ActionType.TYPE, text=msg_text, target="Type a message"),
                        ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
                    ],
                    reasoning=f"Send message '{msg_text}' to contact '{contact}'",
                )

        # 3. "type <msg> to <contact>"
        m_type_to = re.match(
            r"^(?:in\s+whatsapp\s+|on\s+whatsapp\s+|inside\s+whatsapp\s+)?"
            r"(?:type|write)\s+(.+?)\s+to\s+([a-zA-Z0-9_\s]+)$",
            cleaned,
            re.IGNORECASE,
        )
        if m_type_to:
            raw_msg = m_type_to.group(1).strip()
            contact = m_type_to.group(2).strip()
            msg_text = clean_spoken_text(raw_msg, capitalize_first=False)
            if contact in ("her", "him", "them"):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.96,
                    actions=[
                        ActionRequest(action_type=ActionType.CLICK, target="Type a message", target_type="edit"),
                        ActionRequest(action_type=ActionType.TYPE, text=msg_text, target="Type a message"),
                    ],
                    reasoning=f"Focus message box and type '{msg_text}'",
                )
            else:
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.96,
                    actions=[
                        ActionRequest(action_type=ActionType.CLICK, target=contact, target_type="contact"),
                        ActionRequest(action_type=ActionType.CLICK, target="Type a message", target_type="edit"),
                        ActionRequest(action_type=ActionType.TYPE, text=msg_text, target="Type a message"),
                    ],
                    reasoning=f"Select contact '{contact}', focus message box, and type '{msg_text}'",
                )

        # 4. "send her <msg>" or "send him <msg>" or "send them <msg>"
        m_send_pronoun = re.match(
            r"^(?:in\s+whatsapp\s+|on\s+whatsapp\s+|inside\s+whatsapp\s+)?"
            r"(?:send|message)\s+(?:her|him|them)\s+(.+)$",
            cleaned,
            re.IGNORECASE,
        )
        if m_send_pronoun:
            raw_msg = m_send_pronoun.group(1).strip()
            msg_text = clean_spoken_text(raw_msg, capitalize_first=False)
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.96,
                actions=[
                    ActionRequest(action_type=ActionType.CLICK, target="Type a message", target_type="edit"),
                    ActionRequest(action_type=ActionType.TYPE, text=msg_text, target="Type a message"),
                    ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
                ],
                reasoning=f"Focus message box, type '{msg_text}', and send",
            )

        # Check for compound conjunctions first if the command has compound markers
        conjunction_markers = (" and then ", " then ", " and ", ", then ", ", and ", ";", ",")
        if any(marker in cleaned for marker in conjunction_markers):
            conjunction_pattern = r"\s*(?:,\s*(?:and\s+then|then|and)\b|\b(?:and\s+then|then|and)\b|[,;])\s*"
            parts = [p.strip() for p in re.split(conjunction_pattern, cleaned, flags=re.IGNORECASE) if p.strip()]
            if len(parts) >= 2:
                sub_results: List[IntentResult] = []
                all_succeeded = True
                for part in parts:
                    part_cleaned = self._clean_text(part)
                    if not part_cleaned:
                        continue
                    part_res = self._interpret_single_clause(part_cleaned, part)
                    if part_res is None or not part_res.actions:
                        all_succeeded = False
                        break
                    sub_results.append(part_res)

                if all_succeeded and len(sub_results) >= 2:
                    all_actions: List[ActionRequest] = []
                    for r in sub_results:
                        all_actions.extend(r.actions)
                    reasonings = " -> ".join(r.reasoning or "" for r in sub_results if r.reasoning)
                    logger.info("LocalRuleParser chained %d compound actions: %s", len(all_actions), reasonings)
                    return IntentResult(
                        raw_transcript=transcript,
                        source=self.name,
                        confidence=0.95,
                        actions=all_actions,
                        reasoning=f"Chained compound commands: {reasonings}",
                    )

        # Interpret as a single deterministic clause
        return self._interpret_single_clause(cleaned, transcript)

    def _interpret_single_clause(
        self, cleaned: str, transcript: str
    ) -> Optional[IntentResult]:
        # 1. Emergency stop / cancel / resume
        if cleaned in ("stop", "emergency stop", "halt", "cancel", "cancel that"):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=1.0,
                actions=[ActionRequest(action_type=ActionType.NONE, target="emergency_stop")],
                reasoning="Emergency stop command recognized",
            )

        if cleaned in ("resume", "continue", "reset stop", "clear stop", "unfreeze", "enable controls"):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=1.0,
                actions=[ActionRequest(action_type=ActionType.NONE, target="reset_stop")],
                reasoning="Reset emergency stop and resume normal operations",
            )

        # 1.1 Dictation mode toggles
        if re.match(r"^(?:start|enable|enter|turn\s+on)\s+dictation(?:\s+mode)?$|^dictation\s+mode$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="start_dictation")],
                reasoning="Enable hands-free direct dictation mode",
            )

        if re.match(r"^(?:stop|exit|disable|turn\s+off)\s+dictation(?:\s+mode)?$|^(?:command|voice)\s+mode$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="stop_dictation")],
                reasoning="Disable dictation mode and return to command mode",
            )

        # 1.11 Dictation Undo / Revert
        if re.match(r"^(?:undo\s+dictation|revert\s+dictation|revert\s+(?:to\s+)?raw(?:\s+dictation)?|undo\s+ai\s+edit)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.99,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="undo_dictation")],
                reasoning="Revert recent dictation to verbatim raw speech",
            )

        # 1.12 Dictation Cleanup Level selection (None, Light, Medium, High)
        m_cleanup = re.match(
            r"^(?:set\s+cleanup(?:\s+level)?\s+(?:to\s+)?(none|raw|light|medium|high)|cleanup(?:\s+level)?\s+(none|raw|light|medium|high)|raw\s+dictation)$",
            cleaned,
            re.IGNORECASE,
        )
        if m_cleanup:
            lvl = (m_cleanup.group(1) or m_cleanup.group(2) or "none").lower()
            if lvl == "raw":
                lvl = "none"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="set_cleanup_level", target=lvl)],
                reasoning=f"Set dictation auto cleanup level to '{lvl}'",
            )

        # 1.13 Dictation Language Switching (100+ languages)
        m_lang = re.match(
            r"^(?:(?:switch|change|set)\s+language\s+(?:to\s+)?([a-z\s]+)|dictate\s+in\s+([a-z\s]+)|auto\s+language)$",
            cleaned,
            re.IGNORECASE,
        )
        if m_lang and not any(kw in cleaned for kw in ("programming", "code", "python")):
            lang_target = (m_lang.group(1) or m_lang.group(2) or "auto").strip().lower()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="set_language", target=lang_target)],
                reasoning=f"Switch spoken dictation language to '{lang_target}'",
            )

        # 1.14 Text Transforms (Rewrite Selected Text)
        if re.match(r"^(?:open\s+|show\s+)?transforms?(?:\s+overlay|\s+menu)?$|^transform\s+selection$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="open_transforms")],
                reasoning="Open text transform overlay menu",
            )

        if re.match(r"^(?:polish(?:\s+this|\s+selection|\s+text)?|make\s+this\s+clearer)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="transform_selection", target="polish")],
                reasoning="Transform selected text: Polish writing for clarity and brevity",
            )

        if re.match(r"^(?:prompt\s+engineer(?:\s+this|\s+selection)?|make\s+(?:an?\s+)?ai\s+prompt|convert\s+to\s+prompt)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="transform_selection", target="prompt_engineer")],
                reasoning="Transform selected text: Restructure into a high-performance AI prompt",
            )

        if re.match(r"^(?:fix\s+grammar(?:\s+and\s+tone|\s+in\s+this)?|correct\s+grammar)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="transform_selection", target="grammar")],
                reasoning="Transform selected text: Fix grammar, punctuation, and typos",
            )

        if re.match(r"^(?:make(?:\s+this)?\s+executive|executive\s+tone|make\s+formal)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="transform_selection", target="tone_executive")],
                reasoning="Transform selected text: Rewrite with executive, punchy phrasing",
            )

        if re.match(r"^(?:bulletize(?:\s+this)?|convert\s+to\s+bullets?|make\s+bullet\s+points?)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="transform_selection", target="bulletize")],
                reasoning="Transform selected text: Format as structured bullet points",
            )

        # 1.15 Send / Submit / Enter (Essential for chat prompts, messaging, search inputs)
        # e.g., "send it", "now send it", "send", "send message", "send this", "send prompt",
        # "submit", "submit it", "press enter", "hit enter", "enter"
        if re.match(
            r"^(?:(?:now\s+|please\s+)?(?:send\s+(?:it|message|this|prompt|the\s+message|the\s+prompt)|send|submit(?:\s+it|\s+form|\s+message)?)|(?:press|hit)\s+enter|enter)$",
            cleaned,
            re.IGNORECASE,
        ):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=1.0,
                actions=[ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter")],
                reasoning="Send/submit message (Enter)",
            )

        if re.match(r"^(?:send\s+with\s+|press\s+)?ctrl\s+enter$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=1.0,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+enter")],
                reasoning="Send message (Ctrl+Enter)",
            )

        # 1.16 Desktop Element Inspector
        if re.match(r"^(?:open\s+)?(?:desktop\s+)?element\s+inspector$|^(?:inspect\s+(?:elements?|controls|ui|tree|uia))$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=1.0,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="open_inspector")],
                reasoning="Open Desktop UI Element Inspector",
            )

        # 1.2 Fast Web & Platform Searches
        # YouTube: "search youtube", "now search youtube", "search youtube lofi", "search youtube for lofi", "search on youtube for <query>"
        m_yt = re.match(
            r"^(?:search\s+(?:on\s+|in\s+)?youtube(?:\s+for)?|youtube\s+search(?:\s+for)?)\s*(.*)$",
            cleaned,
            re.IGNORECASE,
        )
        if not m_yt:
            m_yt2 = re.match(r"^(?:search|find|look\s+up)\s+(?:for\s+)?(.+?)\s+on\s+youtube$", cleaned, re.IGNORECASE)
            if m_yt2:
                yt_query = m_yt2.group(1).strip()
                encoded_query = urllib.parse.quote_plus(yt_query)
                target_url = f"https://www.youtube.com/results?search_query={encoded_query}"
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.98,
                    actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                    reasoning=f"Search YouTube for '{yt_query}'",
                )
        if m_yt:
            yt_query = m_yt.group(1).strip()
            if yt_query:
                encoded_query = urllib.parse.quote_plus(yt_query)
                target_url = f"https://www.youtube.com/results?search_query={encoded_query}"
                reasoning = f"Search YouTube for '{yt_query}'"
            else:
                target_url = "https://www.youtube.com"
                reasoning = "Open YouTube"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=reasoning,
            )

        # YouTube media playback: "play <song> on youtube", "play <song>" (excluding generic system media keys like "play music")
        m_play = re.match(r"^(?:play|listen\s+to)\s+(.+?)(?:\s+on\s+youtube)?$", cleaned, re.IGNORECASE)
        if m_play and not any(cleaned.startswith(p) for p in ("play video", "play/pause", "play pause")):
            song = m_play.group(1).strip()
            if "on youtube" in cleaned or song.lower() not in ("music", "media", "audio", "track", "song", "video", "sound"):
                target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(song)}"
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                    reasoning=f"Play '{song}' on YouTube",
                )

        # Google web search: "search google", "search google for <query>", "search on google for <query>", "google <query>"
        m_g = re.match(
            r"^(?:search\s+(?:on\s+|in\s+)?google(?:\s+for)?|google\s+search(?:\s+for)?|google)\s*(.*)$",
            cleaned,
            re.IGNORECASE,
        )
        if not m_g:
            m_g2 = re.match(r"^(?:search|look\s+up)\s+(?:for\s+)?(.+?)\s+on\s+google$", cleaned, re.IGNORECASE)
            if m_g2:
                g_query = m_g2.group(1).strip()
                encoded_query = urllib.parse.quote_plus(g_query)
                target_url = f"https://www.google.com/search?q={encoded_query}"
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.98,
                    actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                    reasoning=f"Search Google for '{g_query}'",
                )
        if m_g:
            g_query = m_g.group(1).strip()
            if g_query:
                encoded_query = urllib.parse.quote_plus(g_query)
                target_url = f"https://www.google.com/search?q={encoded_query}"
                reasoning = f"Search Google for '{g_query}'"
            else:
                target_url = "https://www.google.com"
                reasoning = "Open Google"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=reasoning,
            )

        # 1.3 New Tab Navigation & Web Commands
        # "in the new tab open youtube", "in a new tab open chatgpt", "open youtube in a new tab",
        # "in the new tab search lofi beats", "new tab and open google", "in new tab open <x>"
        m_new_tab = (
            re.match(r"^(?:in\s+(?:the\s+|a\s+)?new\s+tab\s+(?:open|launch|go\s+to|visit|search(?:\s+for)?)|(?:open\s+)?(?:a\s+)?new\s+tab\s+and\s+(?:open|launch|go\s+to|visit|search(?:\s+for)?))\s+(.+)$", cleaned, re.IGNORECASE)
            or re.match(r"^(?:open|launch|go\s+to|visit|search(?:\s+for)?)\s+(.+?)\s+in\s+(?:the\s+|a\s+)?new\s+tab$", cleaned, re.IGNORECASE)
        )
        if m_new_tab:
            tab_target = m_new_tab.group(1).strip()
            clean_tab_target = tab_target.lower()
            
            from ..actions.launcher import WEB_APP_MAP
            nav_url = None
            if clean_tab_target in WEB_APP_MAP:
                nav_url = WEB_APP_MAP[clean_tab_target]
            elif clean_tab_target.startswith(("http://", "https://")):
                nav_url = tab_target
            elif any(clean_tab_target.endswith(tld) for tld in (".com", ".org", ".net", ".io", ".dev", ".ai", ".in")):
                nav_url = f"https://{clean_tab_target}"
            else:
                nav_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(tab_target)}"

            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[
                    ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+t"),
                    ActionRequest(action_type=ActionType.TYPE, text=nav_url),
                    ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
                ],
                reasoning=f"Open new tab and navigate to '{tab_target}'",
            )

        # "go to youtube", "go to google", "go to chatgpt", "go to reddit", "visit wikipedia"
        m_goto = re.match(r"^(?:go\s+to|visit|navigate\s+to)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\:\/]+)$", cleaned, re.IGNORECASE)
        if m_goto:
            dest = m_goto.group(1).strip().lower()
            from ..actions.launcher import WEB_APP_MAP
            if dest in WEB_APP_MAP or dest.startswith(("http://", "https://")) or any(dest.endswith(tld) for tld in (".com", ".org", ".net", ".io", ".dev", ".ai", ".in")):
                target_url = WEB_APP_MAP.get(dest, dest if dest.startswith("http") else f"https://{dest}")
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.98,
                    actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                    reasoning=f"Navigate to '{dest}'",
                )

        # GitHub search: "search github for <query>"
        m_gh = re.match(r"^(?:search\s+github\s+for|github\s+search(?:\s+for)?)\s+(.+)$", cleaned, re.IGNORECASE)
        if m_gh:
            gh_query = m_gh.group(1).strip()
            target_url = f"https://github.com/search?q={urllib.parse.quote_plus(gh_query)}"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=f"Search GitHub for '{gh_query}'",
            )

        # Wikipedia search: "search wikipedia for <query>"
        m_wiki = re.match(r"^(?:search\s+wikipedia\s+for|wikipedia\s+search(?:\s+for)?)\s+(.+)$", cleaned, re.IGNORECASE)
        if m_wiki:
            wiki_query = m_wiki.group(1).strip()
            target_url = f"https://en.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote_plus(wiki_query)}"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=f"Search Wikipedia for '{wiki_query}'",
            )

        # Reddit search: "search reddit for <query>"
        m_rd = re.match(r"^(?:search\s+reddit\s+for|reddit\s+search(?:\s+for)?)\s+(.+)$", cleaned, re.IGNORECASE)
        if m_rd:
            rd_query = m_rd.group(1).strip()
            target_url = f"https://www.reddit.com/search/?q={urllib.parse.quote_plus(rd_query)}"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=f"Search Reddit for '{rd_query}'",
            )

        # Amazon search: "search amazon for <query>"
        m_amz = re.match(r"^(?:search\s+amazon\s+for|amazon\s+search(?:\s+for)?)\s+(.+)$", cleaned, re.IGNORECASE)
        if m_amz:
            amz_query = m_amz.group(1).strip()
            target_url = f"https://www.amazon.com/s?k={urllib.parse.quote_plus(amz_query)}"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=f"Search Amazon for '{amz_query}'",
            )

        # Twitter / X search: "search twitter for <query>", "search x for <query>"
        m_tw = re.match(r"^(?:search\s+(?:twitter|x)\s+for|(?:twitter|x)\s+search(?:\s+for)?)\s+(.+)$", cleaned, re.IGNORECASE)
        if m_tw:
            tw_query = m_tw.group(1).strip()
            target_url = f"https://twitter.com/search?q={urllib.parse.quote_plus(tw_query)}"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=f"Search Twitter for '{tw_query}'",
            )

        # Google Maps search: "search maps for <query>", "search google maps for <query>"
        m_map = re.match(r"^(?:search\s+(?:google\s+)?maps\s+for|(?:google\s+)?maps\s+search(?:\s+for)?)\s+(.+)$", cleaned, re.IGNORECASE)
        if m_map:
            map_query = m_map.group(1).strip()
            target_url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(map_query)}"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=f"Search Google Maps for '{map_query}'",
            )

        # Generic web search: "search the web for <query>", "search online for <query>"
        m_web = re.match(r"^(?:search\s+the\s+web\s+for|search\s+online\s+for|web\s+search\s+for)\s+(.+)$", cleaned, re.IGNORECASE)
        if m_web:
            web_query = m_web.group(1).strip()
            encoded_query = urllib.parse.quote_plus(web_query)
            target_url = f"https://www.google.com/search?q={encoded_query}"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=f"Search web for '{web_query}'",
            )

        # 1.3 Direct URL / Domain Navigation (e.g. "go to reddit.com", "open github.com")
        m_url = re.match(r"^(?:go\s+to|open|navigate\s+to)\s+([a-zA-Z0-9_\-]+\.(?:com|org|net|io|dev|ai|co|edu|gov|in|tv|app))(?:/(.*))?$", cleaned, re.IGNORECASE)
        if m_url:
            domain = m_url.group(1).strip().lower()
            path = m_url.group(2) or ""
            target_url = f"https://{domain}/{path}" if path else f"https://{domain}"
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=target_url)],
                reasoning=f"Navigate to {target_url}",
            )

        # 2. Fundamental System Audio & Media Controls
        # 2.0 Master Volume Controls (e.g. "set volume to 50%", "volume 80%", "set my desktop volume to 100", "turn my volume up")
        vol_target_pattern = r"(?:(?:the\s+|my\s+|our\s+|this\s+)?(?:pc\s+|desktop\s+|computer\s+|laptop\s+|system\s+|master\s+)?(?:volume|sound|audio))"
        m_vol_num = re.match(
            rf"^(?:(?:set|change|turn|adjust|put|make)\s+{vol_target_pattern}\s+(?:to\s+|at\s+)?|{vol_target_pattern}\s+(?:to\s+|at\s+)?)([0-9]+)(?:\s*%)?(?:\s+percent)?$",
            cleaned,
            re.IGNORECASE,
        )
        if m_vol_num:
            vol_val = max(0, min(100, int(m_vol_num.group(1))))
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(
                    action_type=ActionType.SYSTEM_ACTION,
                    system_action="set_volume",
                    scroll_amount=vol_val,
                )],
                reasoning=f"Set system volume to {vol_val}%",
            )

        if re.match(rf"^(?:max\s+{vol_target_pattern}|maximum\s+{vol_target_pattern}|full\s+{vol_target_pattern}|{vol_target_pattern}\s+(?:to\s+)?(?:max|maximum|full))$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="volume_up", scroll_amount=25)],
                reasoning="Set system volume to maximum",
            )

        if re.match(rf"^(?:zero\s+{vol_target_pattern}|min\s+{vol_target_pattern}|minimum\s+{vol_target_pattern}|{vol_target_pattern}\s+(?:to\s+)?(?:zero|0|min|minimum|0%?))$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="set_volume", scroll_amount=0)],
                reasoning="Set system volume to 0%",
            )

        if re.match(r"^(?:unmute|turn\s+on\s+sound|restore\s+sound|enable\s+sound)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="unmute")],
                reasoning="Unmute system audio",
            )

        if re.match(rf"^(?:{vol_target_pattern}\s+up|increase\s+{vol_target_pattern}|turn\s+(?:up\s+)?{vol_target_pattern}\s*(?:up)?|louder|make\s+it\s+louder|turn\s+it\s+up|boost\s+{vol_target_pattern})$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="volume_up", scroll_amount=5)],
                reasoning="Increase system volume",
            )

        if re.match(rf"^(?:{vol_target_pattern}\s+down|decrease\s+{vol_target_pattern}|turn\s+(?:down\s+)?{vol_target_pattern}\s*(?:down)?|quieter|make\s+it\s+quieter|lower\s+{vol_target_pattern}|turn\s+it\s+down|soften\s+{vol_target_pattern})$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="volume_down", scroll_amount=5)],
                reasoning="Decrease system volume",
            )

        if re.match(rf"^(?:mute|unmute|mute\s+{vol_target_pattern}|toggle\s+mute|silence|turn\s+off\s+sound)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="mute")],
                reasoning="Toggle audio mute",
            )

        if re.match(r"^(?:play|pause|play\s+pause|resume(?:\s+music)?|play\s+music|pause\s+music)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="play_pause")],
                reasoning="Toggle media play/pause",
            )

        if re.match(r"^(?:next\s+track|next\s+song|skip\s+song|skip\s+track)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="next_track")],
                reasoning="Skip to next track",
            )

        if re.match(r"^(?:prev(?:ious)?\s+track|prev(?:ious)?\s+song|last\s+song)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="prev_track")],
                reasoning="Return to previous track",
            )

        if re.match(r"^(?:stop\s+music|stop\s+playback)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="stop_media")],
                reasoning="Stop media playback",
            )

        if re.match(r"^(?:rewind(?:\s+\d+\s+seconds?)?|go\s+back\s+\d+\s+seconds?|backward(?:\s+\d+\s+seconds?)?)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="rewind")],
                reasoning="Rewind media playback (Left arrow)",
            )

        if re.match(r"^(?:fast\s+forward|forward(?:\s+\d+\s+seconds?)?|skip\s+\d+\s+seconds?|seek\s+forward)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="forward")],
                reasoning="Forward media playback (Right arrow)",
            )

        if re.match(r"^(?:speed\s+up|faster|playback\s+faster|increase\s+speed)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="speed_up")],
                reasoning="Increase playback speed (Shift+>)",
            )

        if re.match(r"^(?:slow\s+down|slower|playback\s+slower|decrease\s+speed)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="slow_down")],
                reasoning="Decrease playback speed (Shift+<)",
            )

        if re.match(r"^(?:captions|subtitles|toggle\s+captions|toggle\s+subtitles|turn\s+on\s+captions|turn\s+off\s+captions|turn\s+on\s+subtitles|turn\s+off\s+subtitles)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="captions")],
                reasoning="Toggle subtitles/captions ('c')",
            )

        if re.match(r"^(?:theater\s+mode|cinema\s+mode)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="theater_mode")],
                reasoning="Toggle theater mode ('t')",
            )

        if re.match(r"^(?:fullscreen\s+video|full\s+screen\s+video)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="fullscreen_media")],
                reasoning="Toggle fullscreen video ('f')",
            )

        if re.match(r"^(?:mute\s+video|unmute\s+video|mute\s+player)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="mute_media")],
                reasoning="Toggle video player mute ('m')",
            )

        if re.match(r"^(?:max\s+volume|full\s+volume|volume\s+100|100%\s+volume)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="volume_up", scroll_amount=25)],
                reasoning="Set volume to maximum",
            )

        # 2.9 Display Brightness & Visual Comfort
        bright_target_pattern = r"(?:(?:the\s+|my\s+|our\s+|this\s+)?(?:pc\s+|desktop\s+|computer\s+|laptop\s+|screen\s+|display\s+|monitor\s+)?(?:brightness|brigthenes|brightnes|brightess|bright))"
        m_bright = re.match(
            rf"^(?:(?:set|change|turn|adjust|put|make)\s+{bright_target_pattern}\s+(?:to\s+|at\s+)?|{bright_target_pattern}\s+(?:to\s+|at\s+)?)([0-9]+)(?:\s*%)?(?:\s+percent)?(?:\s+(?:now|please|ok))?$",
            cleaned,
            re.IGNORECASE,
        )
        if m_bright:
            bright_val = max(0, min(100, int(m_bright.group(1))))
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(
                    action_type=ActionType.SYSTEM_ACTION,
                    system_action="set_brightness",
                    scroll_amount=bright_val,
                )],
                reasoning=f"Set display brightness to {bright_val}%",
            )

        if re.match(rf"^(?:max\s+{bright_target_pattern}|maximum\s+{bright_target_pattern}|full\s+{bright_target_pattern}|{bright_target_pattern}\s+(?:to\s+)?(?:max|maximum|full|100%?))$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="set_brightness", scroll_amount=100)],
                reasoning="Set display brightness to 100%",
            )

        if re.match(r"^(?:dim(?:\s+the)?\s+(?:screen|display|monitor)|dim)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="set_brightness", scroll_amount=30)],
                reasoning="Dim display brightness to 30%",
            )

        if re.match(rf"^(?:decrease\s+{bright_target_pattern}|lower\s+{bright_target_pattern}|turn\s+(?:down\s+)?{bright_target_pattern}\s*(?:down)?|{bright_target_pattern}\s+down)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="brightness_down", scroll_amount=15)],
                reasoning="Decrease display brightness",
            )

        if re.match(rf"^(?:increase\s+{bright_target_pattern}|boost\s+{bright_target_pattern}|turn\s+(?:up\s+)?{bright_target_pattern}\s*(?:up)?|{bright_target_pattern}\s+up|make\s+(?:the\s+)?(?:screen|display|monitor)\s+brighter|brighter)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="brightness_up", scroll_amount=15)],
                reasoning="Increase display brightness",
            )

        # Dark Mode, Light Mode & Night Light
        if re.match(r"^(?:(?:switch\s+to|enable|turn\s+on|activate)\s+dark\s+(?:mode|theme)|dark\s+(?:mode|theme))$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="dark_mode")],
                reasoning="Enable Windows Dark Mode",
            )

        if re.match(r"^(?:(?:switch\s+to|enable|turn\s+on|activate)\s+light\s+(?:mode|theme)|light\s+(?:mode|theme))$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="light_mode")],
                reasoning="Enable Windows Light Mode",
            )

        if re.match(r"^(?:toggle\s+(?:dark\s+mode|theme|dark\s+theme)|switch\s+theme)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="toggle_dark_mode")],
                reasoning="Toggle Windows Dark/Light Mode",
            )

        if re.match(r"^(?:(?:toggle|turn\s+on|enable|turn\s+off|disable)\s+night\s+light|night\s+light)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="night_light")],
                reasoning="Toggle Windows Night Light",
            )

        # Multi-Monitor Display Switching
        if re.match(r"^(?:duplicate\s+(?:displays?|screens?)|clone\s+(?:displays?|screens?))$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="display_mode", target="clone")],
                reasoning="Duplicate displays (/clone)",
            )

        if re.match(r"^(?:extend\s+(?:displays?|screens?)|extend\s+desktop)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="display_mode", target="extend")],
                reasoning="Extend desktop displays (/extend)",
            )

        if re.match(r"^(?:pc\s+screen\s+only|internal\s+display\s+only|first\s+screen\s+only)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="display_mode", target="internal")],
                reasoning="PC screen only (/internal)",
            )

        if re.match(r"^(?:second\s+screen\s+only|external\s+display\s+only)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="display_mode", target="external")],
                reasoning="Second screen only (/external)",
            )

        # Battery & System Diagnostics
        if re.match(r"^(?:(?:what(?:'s|\s+is)\s+(?:my\s+)?)?battery(?:\s+(?:percentage|percent|level|status|life))?|check\s+battery|how\s+much\s+battery(?:\s+is\s+left)?)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="battery_status")],
                reasoning="Check battery percentage & status",
            )

        if re.match(r"^(?:which\s+app\s+is\s+using\s+the\s+most\s+ram|what\s+is\s+using\s+ram|check\s+ram|ram\s+usage|memory\s+usage|top\s+ram|system\s+health|what(?:'s|\s+is)\s+my\s+cpu\s+usage)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="system_health")],
                reasoning="Check system health, RAM & CPU usage",
            )

        # Process Killer & Explorer Restart
        m_kill = re.match(r"^(?:force\s+quit|kill\s+process|kill|terminate|end\s+task)\s+(?:the\s+)?([a-zA-Z0-9_\-\.]+?)(?:\s+(?:app|application|program|process))?$", cleaned, re.IGNORECASE)
        if m_kill:
            target_p = m_kill.group(1).strip()
            if target_p not in ("this", "window", "tab", "all"):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.98,
                    actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="kill_process", target=target_p)],
                    reasoning=f"Force terminate process '{target_p}'",
                )

        if re.match(r"^(?:restart\s+(?:windows\s+)?explorer|restart\s+taskbar)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="restart_explorer")],
                reasoning="Restart Windows Explorer",
            )

        # Recent Downloads, Files & Recycle Bin
        if re.match(r"^(?:open\s+(?:the\s+)?(?:last|latest|recent)\s+download(?:ed\s+file)?|open\s+(?:the\s+)?last\s+file\s+i\s+downloaded)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="open_latest_download")],
                reasoning="Open most recently downloaded file",
            )

        if re.match(r"^(?:open\s+(?:the\s+)?(?:last|latest|recent)\s+screenshot)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="open_latest_screenshot")],
                reasoning="Open most recent screenshot",
            )

        m_folder = re.match(r"^(?:open\s+(?:my\s+)?(downloads|documents|desktop|pictures|videos|music)(?:\s+folder)?)$", cleaned, re.IGNORECASE)
        if m_folder:
            f_name = m_folder.group(1).lower()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="open_folder", target=f_name)],
                reasoning=f"Open {f_name.capitalize()} folder",
            )

        if re.match(r"^(?:empty\s+(?:the\s+)?recycle\s+bin|clear\s+(?:the\s+)?recycle\s+bin|clear\s+trash|empty\s+trash)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="empty_recycle_bin")],
                reasoning="Empty Windows Recycle Bin",
            )

        # Caffeine / Keep Awake & Boss Mode
        if re.match(r"^(?:keep\s+(?:the\s+)?screen\s+awake|don'?t\s+sleep|caffeine\s+mode|prevent\s+sleep)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="keep_awake")],
                reasoning="Enable Caffeine / Keep Awake mode",
            )

        if re.match(r"^(?:allow\s+sleep|caffeine\s+off|disable\s+caffeine)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="allow_sleep")],
                reasoning="Disable Caffeine mode (normal sleep restored)",
            )

        if re.match(r"^(?:boss\s+mode|hide\s+everything|privacy\s+shield|privacy\s+mode)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="boss_mode")],
                reasoning="Engage Boss Mode (Desktop shown, audio muted)",
            )

        # Network Info & Connectivity
        if re.match(r"^(?:what(?:'s|\s+is)\s+(?:my\s+)?(?:ip|ip\s+address|local\s+ip)|check\s+internet|network\s+info|ping\s+status)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="network_info")],
                reasoning="Query network connection & local IP",
            )

        # Clipboard Power Tools
        if re.match(r"^(?:paste\s+as\s+plain\s+text|paste\s+plain\s+text|plain\s+text\s+paste)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="paste_plain_text")],
                reasoning="Paste unformatted plain text (Ctrl+Shift+V)",
            )

        if re.match(r"^(?:clear\s+(?:the\s+)?clipboard|empty\s+(?:the\s+)?clipboard)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="clear_clipboard")],
                reasoning="Clear clipboard contents",
            )

        # Browser Tabs & URL Shortcuts
        m_tab_sw = re.match(r"^(?:switch\s+to\s+(?:the\s+)?(.+?)\s+tab|go\s+to\s+(?:the\s+)?tab\s+with\s+(.+?)|find\s+tab\s+with\s+(.+?))$", cleaned, re.IGNORECASE)
        if m_tab_sw:
            q_name = (m_tab_sw.group(1) or m_tab_sw.group(2) or m_tab_sw.group(3) or "").strip()
            if q_name and not q_name.isdigit():
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.98,
                    actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="switch_to_tab", target=q_name)],
                    reasoning=f"Switch to browser tab matching '{q_name}'",
                )

        if re.match(r"^(?:copy\s+(?:the\s+)?(?:current\s+)?url|copy\s+link|copy\s+address)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="copy_current_url")],
                reasoning="Copy current browser address URL",
            )

        # 3. Security, Power, & Lock Controls
        if re.match(r"^(?:lock\s+pc|lock\s+computer|lock\s+(?:the\s+)?screen|lock\s+workstation)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="lock_pc")],
                reasoning="Lock Windows workstation",
            )

        if re.match(r"^(?:sleep\s+pc|put\s+(?:the\s+)?computer\s+to\s+sleep|sleep\s+computer)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sleep_pc")],
                reasoning="Put computer to sleep",
            )

        # 4. Windows Shell & System Utilities
        if re.match(r"^(?:show\s+desktop|go\s+to\s+desktop|hide\s+all\s+windows|minimize\s+all)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="show_desktop")],
                reasoning="Toggle desktop view (Win+D)",
            )

        if re.match(r"^(?:(?:open\s+)?task\s+manager)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="task_manager")],
                reasoning="Open Task Manager (Ctrl+Shift+Esc)",
            )

        if re.match(r"^(?:(?:open\s+)?file\s+explorer|(?:open\s+)?my\s+computer|(?:open\s+)?this\s+pc|open\s+files)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="file_explorer")],
                reasoning="Open File Explorer (Win+E)",
            )

        if re.match(r"^(?:(?:open\s+)?(?:windows|pc|os)\s+settings)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="settings")],
                reasoning="Open Windows Settings",
            )

        if re.match(r"^(?:open\s+start\s+menu|start\s+menu|press\s+windows\s+key|windows\s+menu)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="start_menu")],
                reasoning="Open Start Menu (Win)",
            )

        if re.match(r"^(?:windows\s+search|search\s+windows)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="search")],
                reasoning="Open Windows Search (Win+S)",
            )

        if re.match(r"^(?:take\s+screenshot|screenshot|screen\s+clip|snip|snip\s+screen)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="screenshot")],
                reasoning="Trigger Snipping Tool (Win+Shift+S)",
            )

        if re.match(r"^(?:clipboard\s+history|show\s+clipboard|clipboard)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="clipboard_history")],
                reasoning="Open Clipboard History (Win+V)",
            )

        if re.match(r"^(?:action\s+center|notifications|open\s+notifications)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="action_center")],
                reasoning="Open Action Center (Win+A)",
            )

        if re.match(r"^(?:open\s+run|run\s+dialog|open\s+run\s+dialog)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="open_run")],
                reasoning="Open Run dialog (Win+R)",
            )

        if re.match(r"^(?:emoji\s+panel|open\s+emojis|emojis|emoji\s+keyboard)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="emoji_panel")],
                reasoning="Open Emoji panel (Win+.)",
            )

        if re.match(r"^(?:game\s+bar|screen\s+record|record\s+screen)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="game_bar")],
                reasoning="Open Game Bar / Recording (Win+G)",
            )

        if re.match(r"^(?:quick\s+settings|control\s+center)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="quick_settings")],
                reasoning="Open Quick Settings (Win+A)",
            )

        if re.match(r"^(?:sound\s+settings|audio\s+settings|volume\s+settings)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target="ms-settings:sound")],
                reasoning="Open Windows Sound Settings",
            )

        if re.match(r"^(?:bluetooth\s+settings|bluetooth)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target="ms-settings:bluetooth")],
                reasoning="Open Windows Bluetooth Settings",
            )

        if re.match(r"^(?:wifi\s+settings|network\s+settings|internet\s+settings)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target="ms-settings:network")],
                reasoning="Open Windows Network Settings",
            )

        if re.match(r"^(?:display\s+settings|screen\s+settings)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target="ms-settings:display")],
                reasoning="Open Windows Display Settings",
            )

        # 4.9 Handless Sidebar Self-Positioning, Edge Docking, Sizing, Floating, & Settings
        # Dock Left / Move to Left side
        if re.match(r"^(?:(?:move|dock|put|place|switch|shift)\s+(?:the\s+)?(?:sidebar\s+|copilot\s+|handless\s+|window\s+)?(?:to|in|on)?\s*(?:the\s+)?left(?:\s+side|\s+edge|\s+dock)?|dock\s+(?:to\s+(?:the\s+)?)?left|put\s+sidebar\s+on\s+left|left\s+dock|dock\s+left)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_dock_left")],
                reasoning="Dock Handless sidebar to left screen edge",
            )

        # Dock Right / Move to Right side
        if re.match(r"^(?:(?:move|dock|put|place|switch|shift)\s+(?:the\s+)?(?:sidebar\s+|copilot\s+|handless\s+|window\s+)?(?:to|in|on)?\s*(?:the\s+)?right(?:\s+side|\s+edge|\s+dock)?|dock\s+(?:to\s+(?:the\s+)?)?right|put\s+sidebar\s+on\s+right|right\s+dock|dock\s+right)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_dock_right")],
                reasoning="Dock Handless sidebar to right screen edge",
            )

        # Auto-fit / Adjust to side of screen
        if re.match(r"^(?:(?:auto\s+)?fit\s+(?:to\s+)?(?:the\s+)?(?:side|screen)|(?:auto\s+)?adjust\s+(?:to\s+)?(?:the\s+)?(?:side|screen)|snap\s+to\s+side|align\s+to\s+side|auto\s+fit|auto\s+adjust)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_auto_fit")],
                reasoning="Auto-fit Handless sidebar to side of screen",
            )

        # Start Live Call (Gemini 3.8 Live)
        if re.match(r"^(?:(?:start\s+)?(?:live\s+)?(?:voice\s+)?call|call\s+(?:gemini|handless)|open\s+(?:live\s+)?call|live\s+call)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_call")],
                reasoning="Start Live Voice Call with Gemini 3.8 Live",
            )

        # End Live Call
        if re.match(r"^(?:end\s+(?:the\s+)?call|hang\s+up|stop\s+(?:the\s+)?call|disconnect\s+call|close\s+call)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="end_call")],
                reasoning="End active Live Voice Call",
            )

        # Move out of the way / Switch sides / Dodge
        if re.match(r"^(?:move\s+out\s+of\s+(?:the\s+)?way|get\s+out\s+of\s+(?:the\s+)?way|switch\s+sides|other\s+side|dodge|let\s+me\s+see|toggle\s+dock(?:\s+side)?)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_toggle_dock")],
                reasoning="Switch Handless sidebar to opposite screen edge",
            )

        # Make wider / Expand sidebar / Open full / Big mode
        if re.match(r"^(?:(?:make\s+(?:it\s+|the\s+)?(?:sidebar\s+)?)?(?:wider|wide|big|large)|expand(?:\s+sidebar)?|open\s+full|full\s+width|wide\s+mode|big\s+sidebar|wide\s+sidebar|expand\s+sidebar)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_expand")],
                reasoning="Expand Handless sidebar to wide mode",
            )

        # Make narrower / Compact / Standard width / Small mode
        if re.match(r"^(?:(?:make\s+(?:it\s+|the\s+)?(?:sidebar\s+)?)?(?:narrower|narrow|small|compact)|shrink(?:\s+sidebar)?|compact\s+mode|standard\s+width|normal\s+width|small\s+sidebar|compact\s+sidebar|standard\s+sidebar)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_compact")],
                reasoning="Set Handless sidebar to standard width",
            )

        # Minimize sidebar / Float as bot icon
        if re.match(r"^(?:minimize\s+(?:the\s+)?sidebar|float(?:\s+sidebar)?|floating\s+mode|shrink\s+to\s+(?:floating\s+)?(?:bot|icon|button)|minimize\s+to\s+floating)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_float")],
                reasoning="Minimize Handless sidebar to floating bot icon",
            )

        # Open Handless Settings / API Keys
        if re.match(r"^(?:(?:open\s+)?(?:handless\s+|vyoma\s+|app\s+)?settings|show\s+settings|configure\s+api\s+keys?|api\s+keys?|settings\s+page)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_settings")],
                reasoning="Open Handless settings view inside sidebar",
            )

        # Open Call Transcripts & Meeting Notes Screen
        if re.match(r"^(?:(?:open\s+|show\s+)?(?:meeting\s+transcripts?|call\s+transcripts?|meeting\s+notes?|call\s+notes?)|transcribe\s+meeting|transcribe\s+call)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="sidebar_meeting")],
                reasoning="Open Handless call transcripts and meeting notes screen",
            )

        # Start Recording Call / Meeting
        if re.match(r"^(?:start\s+(?:meeting\s+)?recording|record\s+(?:the\s+)?(?:call|meeting|zoom|google\s+meet|teams|whatsapp(?:\s+call)?)|start\s+transcribing\s+(?:the\s+)?(?:call|meeting))$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="start_meeting_recording")],
                reasoning="Start recording and transcribing call audio from mic and system loopback",
            )

        # Stop Recording Call / Meeting
        if re.match(r"^(?:stop\s+(?:meeting\s+)?recording|stop\s+recording\s+(?:the\s+)?(?:call|meeting)|end\s+(?:the\s+)?meeting\s+recording|stop\s+transcribing\s+(?:the\s+)?(?:call|meeting))$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="stop_meeting_recording")],
                reasoning="Stop recording and save meeting session transcript",
            )

        # 1-Click Meeting AI Summary
        if re.match(r"^(?:summarize\s+(?:the\s+)?(?:meeting|call|transcript)|generate\s+(?:meeting\s+)?summary|create\s+(?:meeting\s+)?summary)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="summarize_meeting")],
                reasoning="Generate 1-click AI executive summary and action items for current meeting",
            )

        # 4.3 Watch Me & Automate (No-Code Voice Macros)
        # Start recording user actions
        if re.match(r"^(?:(?:handless\s*,?\s*)?(?:watch\s+(?:what\s+)?i\s+do|watch\s+me|record\s+(?:a\s+)?(?:workflow|macro)|start\s+recording\s+(?:workflow|macro)))$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.99,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="start_macro_recording")],
                reasoning="Start recording desktop user actions for autonomous macro replication",
            )

        # Save recorded macro with voice name (e.g. "Call this 'Morning Report Workflow'", "Save workflow as Morning Report")
        m_save_macro = re.match(
            r"^(?:call\s+this\s+['\"]?(.+?)['\"]?|save\s+(?:this\s+)?(?:workflow|macro)\s+as\s+['\"]?(.+?)['\"]?|name\s+this\s+(?:workflow|macro)\s+['\"]?(.+?)['\"]?)$",
            transcript.strip(),
            re.IGNORECASE,
        )
        if m_save_macro:
            macro_name = (m_save_macro.group(1) or m_save_macro.group(2) or m_save_macro.group(3) or "Custom Voice Workflow").strip().strip("'\"")
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="save_macro", target=macro_name)],
                reasoning=f"Save recorded macro workflow as '{macro_name}'",
            )

        # Stop / Discard recorded macro
        if re.match(r"^(?:stop\s+(?:macro\s+|workflow\s+)?recording|discard\s+(?:the\s+)?(?:workflow|macro)|cancel\s+(?:macro\s+|workflow\s+)?recording)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="stop_macro_recording")],
                reasoning="Stop or discard active macro recording",
            )

        # 4.4 Universal Screen Lens (Win + Shift + Space voice trigger)
        if re.match(r"^(?:(?:open\s+)?screen\s+lens|inspect\s+screen|what(?:'s|\s+is)\s+on\s+my\s+screen|explain\s+(?:this\s+)?screen|analyze\s+(?:this\s+)?screen|inspect\s+active\s+window)$", cleaned, re.IGNORECASE):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="open_screen_lens")],
                reasoning="Open Universal Screen Lens to analyze active window with multimodal AI",
            )

        # 5. Window Positioning, Snapping, Centering, Popup Mode, & Multi-App Layouts
        # 5.1 Multi-App Coordinated Layout (e.g. "put chrome on left and vscode on right", "put chrome on top and terminal below it")
        m_multi = re.match(
            r"^(?:put|place|move|tile|dock)\s+(.+?)\s+(?:on|in|to)\s+(?:the\s+)?(left|right|top|bottom|top\s+left|top\s+right|bottom\s+left|bottom\s+right|left\s+top|left\s+bottom|right\s+top|right\s+bottom)(?:\s+half|\s+side)?\s+(?:and|,)\s+(?:put\s+|place\s+|move\s+)?(.+?)\s+(?:on|in|to|down\s+of|below)\s+(?:the\s+)?(left|right|top|bottom|down|below|it|down\s+of\s+it|below\s+it|top\s+left|top\s+right|bottom\s+left|bottom\s+right|left\s+top|left\s+bottom|right\s+top|right\s+bottom)(?:\s+half|\s+side)?$",
            cleaned,
            re.IGNORECASE,
        )
        if m_multi:
            app1 = m_multi.group(1).strip()
            pos1_raw = m_multi.group(2).lower().replace(" ", "_")
            app2 = m_multi.group(3).strip()
            pos2_raw = m_multi.group(4).lower().replace(" ", "_")

            pos_action_map = {
                "left": WindowActionType.SNAP_LEFT,
                "right": WindowActionType.SNAP_RIGHT,
                "top": WindowActionType.TOP_HALF,
                "bottom": WindowActionType.BOTTOM_HALF,
                "top_left": WindowActionType.TOP_LEFT,
                "left_top": WindowActionType.TOP_LEFT,
                "top_right": WindowActionType.TOP_RIGHT,
                "right_top": WindowActionType.TOP_RIGHT,
                "bottom_left": WindowActionType.BOTTOM_LEFT,
                "left_bottom": WindowActionType.BOTTOM_LEFT,
                "bottom_right": WindowActionType.BOTTOM_RIGHT,
                "right_bottom": WindowActionType.BOTTOM_RIGHT,
            }

            if pos2_raw in ("below", "down", "it", "down_of_it", "below_it"):
                if pos1_raw in ("top", "top_half"):
                    pos2_act = WindowActionType.BOTTOM_HALF
                elif pos1_raw in ("top_left", "left_top"):
                    pos2_act = WindowActionType.BOTTOM_LEFT
                elif pos1_raw in ("top_right", "right_top"):
                    pos2_act = WindowActionType.BOTTOM_RIGHT
                else:
                    pos2_act = WindowActionType.BOTTOM_HALF
            else:
                pos2_act = pos_action_map.get(pos2_raw, WindowActionType.SNAP_RIGHT)

            pos1_act = pos_action_map.get(pos1_raw, WindowActionType.SNAP_LEFT)

            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[
                    ActionRequest(action_type=ActionType.WINDOW_ACTION, target=app1, window_action=pos1_act),
                    ActionRequest(action_type=ActionType.WINDOW_ACTION, target=app2, window_action=pos2_act),
                ],
                reasoning=f"Position '{app1}' to {pos1_act.value} and '{app2}' to {pos2_act.value}",
            )

        # 5.2 Center Window ("center window", "center chrome", "center it", "put chrome in center", "put in center")
        m_center = re.match(
            r"^(?:(?:put|place|move)\s+(?:the\s+)?(.+?)\s+(?:in|to|at)\s+(?:the\s+)?center|center\s+(?:the\s+)?(.+?)|(?:put|place|move)\s+(?:in|to|at)\s+(?:the\s+)?center|center(?:\s+it|\s+window|\s+this)?)$",
            cleaned,
            re.IGNORECASE,
        )
        if m_center:
            target_raw = (m_center.group(1) or m_center.group(2) or "").strip()
            if target_raw in ("this", "the", "window", "app", "application", "program", "active", "current", "it", "this window"):
                target_raw = None
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(
                    action_type=ActionType.WINDOW_ACTION,
                    target=target_raw,
                    window_action=WindowActionType.CENTER,
                )],
                reasoning=f"Center {'window' if not target_raw else f"'{target_raw}'"} on screen",
            )

        # 5.3 Small Popup Window ("make a small popup window of it", "make chrome a popup", "make it a popup window", "popup window", "float chrome")
        m_popup = re.match(
            r"^(?:make\s+(?:a\s+)?(?:small\s+)?popup(?:\s+window)?(?:\s+of\s+it)?|make\s+(?:the\s+)?(.+?)\s+(?:a\s+)?(?:small\s+)?popup(?:\s+window)?|float\s+(?:the\s+)?(.+?)|(?:make\s+it\s+a\s+)?(?:small\s+)?popup(?:\s+window)?)$",
            cleaned,
            re.IGNORECASE,
        )
        if m_popup:
            target_raw = (m_popup.group(1) or m_popup.group(2) or "").strip()
            if not target_raw or target_raw in ("this", "the", "window", "app", "application", "program", "active", "current", "it", "this window"):
                target_raw = None
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(
                    action_type=ActionType.WINDOW_ACTION,
                    target=target_raw,
                    window_action=WindowActionType.POPUP,
                )],
                reasoning=f"Make {'active window' if not target_raw else f"'{target_raw}'"} a small popup window",
            )

        # 5.4 Standard Active Window Snapping (Active window shortcuts)
        if re.match(r"^(?:snap\s+(?:window\s+)?left|tile\s+left)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.SNAP_LEFT)],
                reasoning="Snap window left (Win+Left)",
            )

        if re.match(r"^(?:snap\s+(?:window\s+)?right|tile\s+right)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.SNAP_RIGHT)],
                reasoning="Snap window right (Win+Right)",
            )

        if re.match(r"^(?:snap\s+(?:window\s+)?top\s+left|tile\s+top\s+left)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="snap_top_left")],
                reasoning="Snap window top left",
            )

        if re.match(r"^(?:snap\s+(?:window\s+)?top\s+right|tile\s+top\s+right)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="snap_top_right")],
                reasoning="Snap window top right",
            )

        if re.match(r"^(?:snap\s+(?:window\s+)?bottom\s+left|tile\s+bottom\s+left)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="snap_bottom_left")],
                reasoning="Snap window bottom left",
            )

        if re.match(r"^(?:snap\s+(?:window\s+)?bottom\s+right|tile\s+bottom\s+right)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="snap_bottom_right")],
                reasoning="Snap window bottom right",
            )

        # 5.5 Single-app Positional Snapping ("put chrome on left", "put in left", "put chrome in top left", "snap chrome left")
        m_snap = re.match(
            r"^(?:(?:put|place|move|tile|dock)\s+(?:(?:the\s+)?(.+?)\s+)?(?:on|in|to)\s+(?:the\s+)?|snap\s+(?:the\s+)?([a-zA-Z0-9_\-\.]+?)\s+)(top\s+left|top\s+right|bottom\s+left|bottom\s+right|left\s+top|left\s+bottom|right\s+top|right\s+bottom|left|right|top|bottom)(?:\s+half|\s+side|\s+corner)?$",
            cleaned,
            re.IGNORECASE,
        )
        if m_snap:
            target_raw = (m_snap.group(1) or m_snap.group(2) or "").strip()
            if not target_raw or target_raw in ("this", "the", "window", "app", "application", "program", "active", "current", "it", "this window"):
                target_raw = None
            pos_str = m_snap.group(3).lower().replace(" ", "_")

            pos_action_map = {
                "left": WindowActionType.SNAP_LEFT,
                "right": WindowActionType.SNAP_RIGHT,
                "top": WindowActionType.TOP_HALF,
                "bottom": WindowActionType.BOTTOM_HALF,
                "top_left": WindowActionType.TOP_LEFT,
                "left_top": WindowActionType.TOP_LEFT,
                "top_right": WindowActionType.TOP_RIGHT,
                "right_top": WindowActionType.TOP_RIGHT,
                "bottom_left": WindowActionType.BOTTOM_LEFT,
                "left_bottom": WindowActionType.BOTTOM_LEFT,
                "bottom_right": WindowActionType.BOTTOM_RIGHT,
                "right_bottom": WindowActionType.BOTTOM_RIGHT,
            }
            w_act = pos_action_map.get(pos_str, WindowActionType.SNAP_LEFT)
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.98,
                actions=[ActionRequest(
                    action_type=ActionType.WINDOW_ACTION,
                    target=target_raw,
                    window_action=w_act,
                )],
                reasoning=f"Position {'window' if not target_raw else f"'{target_raw}'"} to {w_act.value}",
            )

        if re.match(r"^(?:next\s+monitor|next\s+screen|move\s+to\s+next\s+(?:monitor|screen|display))$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="next_monitor")],
                reasoning="Move active window to next monitor (Win+Shift+Right)",
            )

        if re.match(r"^(?:prev(?:ious)?\s+monitor|prev(?:ious)?\s+screen|move\s+to\s+prev(?:ious)?\s+(?:monitor|screen|display))$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="prev_monitor")],
                reasoning="Move active window to previous monitor (Win+Shift+Left)",
            )

        if re.match(r"^(?:minimize\s+other(?:s|\s+windows)?|clean\s+workspace)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="minimize_others")],
                reasoning="Minimize other windows (Win+Home)",
            )

        if re.match(r"^(?:next\s+desktop|switch\s+to\s+next\s+desktop)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="next_desktop")],
                reasoning="Next virtual desktop (Ctrl+Win+Right)",
            )

        if re.match(r"^(?:prev(?:ious)?\s+desktop|switch\s+to\s+prev(?:ious)?\s+desktop)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="prev_desktop")],
                reasoning="Previous virtual desktop (Ctrl+Win+Left)",
            )

        if re.match(r"^(?:task\s+view|all\s+windows)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="task_view")],
                reasoning="Open Task View (Win+Tab)",
            )

        # 6. Browser Navigation & Web Shortcuts
        if re.match(r"^(?:go\s+back|back|navigate\s+back)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="go_back")],
                reasoning="Navigate back (Alt+Left)",
            )

        if re.match(r"^(?:go\s+forward|forward|navigate\s+forward)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="go_forward")],
                reasoning="Navigate forward (Alt+Right)",
            )

        if re.match(r"^(?:address\s+bar|url\s+bar|focus\s+url)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="address_bar")],
                reasoning="Focus address bar (Ctrl+L)",
            )

        if re.match(r"^(?:zoom\s+in|make\s+(?:it\s+)?bigger)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="zoom_in")],
                reasoning="Zoom in (Ctrl+=)",
            )

        if re.match(r"^(?:zoom\s+out|make\s+(?:it\s+)?smaller)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="zoom_out")],
                reasoning="Zoom out (Ctrl+-)",
            )

        if re.match(r"^(?:reset\s+zoom|normal\s+zoom|default\s+zoom)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="zoom_reset")],
                reasoning="Reset zoom (Ctrl+0)",
            )

        if re.match(r"^(?:next\s+tab|switch\s+tab)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="next_tab")],
                reasoning="Switch to next tab (Ctrl+Tab)",
            )

        if re.match(r"^(?:prev(?:ious)?\s+tab)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="prev_tab")],
                reasoning="Switch to previous tab (Ctrl+Shift+Tab)",
            )

        if re.match(r"^(?:find|find\s+on\s+page|search\s+page)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+f")],
                reasoning="Find on page (Ctrl+F)",
            )

        if re.match(r"^(?:bookmark|bookmark\s+this|add\s+bookmark)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+d")],
                reasoning="Bookmark page (Ctrl+D)",
            )

        if re.match(r"^(?:downloads|open\s+downloads)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+j")],
                reasoning="Open downloads (Ctrl+J)",
            )

        if re.match(r"^(?:history|open\s+history)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+h")],
                reasoning="Open browser history (Ctrl+H)",
            )

        if re.match(r"^(?:duplicate\s+tab|clone\s+tab)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="duplicate_tab")],
                reasoning="Duplicate tab (Ctrl+L, Alt+Enter)",
            )

        if re.match(r"^(?:(?:new\s+)?incognito(?:\s+window)?|(?:new\s+)?private\s+window|private\s+browsing)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="incognito_window")],
                reasoning="Open new Incognito window (Ctrl+Shift+N)",
            )

        if re.match(r"^(?:hard\s+refresh|force\s+reload)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="hard_refresh")],
                reasoning="Hard refresh page (Ctrl+F5)",
            )

        if re.match(r"^(?:view\s+source|view\s+page\s+source|page\s+source)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="view_source")],
                reasoning="View page source (Ctrl+U)",
            )

        if re.match(r"^(?:toggle\s+bookmarks\s+bar|bookmarks\s+bar|show\s+bookmarks\s+bar|hide\s+bookmarks\s+bar)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="toggle_bookmarks_bar")],
                reasoning="Toggle bookmarks bar (Ctrl+Shift+B)",
            )

        m_tab_num = re.match(r"^(?:(?:switch\s+to|go\s+to)\s+)?tab\s+([1-9]|one|two|three|four|five|six|seven|eight|nine|first|second|third|fourth|fifth|last)$", cleaned)
        if m_tab_num:
            t_raw = m_tab_num.group(1).lower()
            tab_map = {
                "1": 1, "one": 1, "first": 1,
                "2": 2, "two": 2, "second": 2,
                "3": 3, "three": 3, "third": 3,
                "4": 4, "four": 4, "fourth": 4,
                "5": 5, "five": 5, "fifth": 5,
                "6": 6, "six": 6,
                "7": 7, "seven": 7,
                "8": 8, "eight": 8,
                "9": 9, "nine": 9, "last": 9,
            }
            num = tab_map.get(t_raw, 1)
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action=f"tab_{num}")],
                reasoning=f"Switch to tab {num} (Ctrl+{num})",
            )

        # 7. Editing & Key presses
        if re.match(r"^(?:delete\s+line|clear\s+line|erase\s+line)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="delete_line")],
                reasoning="Delete line",
            )

        if re.match(r"^(?:delete\s+word|erase\s+word|backspace\s+word)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="delete_word")],
                reasoning="Delete word (Ctrl+Backspace)",
            )

        if re.match(r"^(?:select\s+line|highlight\s+line)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="select_line")],
                reasoning="Select line",
            )

        if re.match(r"^(?:line\s+start|start\s+of\s+line|beginning\s+of\s+line)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="line_start")],
                reasoning="Move cursor to line start (Home)",
            )

        if re.match(r"^(?:line\s+end|end\s+of\s+line)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="line_end")],
                reasoning="Move cursor to line end (End)",
            )

        if re.match(r"^(?:top\s+of\s+page|scroll\s+to\s+top|go\s+to\s+top)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="page_top")],
                reasoning="Scroll to top of page (Ctrl+Home)",
            )

        if re.match(r"^(?:bottom\s+of\s+page|scroll\s+to\s+bottom|go\s+to\s+bottom)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="page_bottom")],
                reasoning="Scroll to bottom of page (Ctrl+End)",
            )

        # 7. Editing & Key presses
        if re.match(r"^(?:clear\s+text|delete\s+all|clear\s+field|clear\s+input)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[
                    ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+a"),
                    ActionRequest(action_type=ActionType.KEY_PRESS, keys="backspace"),
                ],
                reasoning="Clear field text (Ctrl+A, Backspace)",
            )

        key_mappings = {
            "enter": ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
            "press enter": ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
            "hit enter": ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
            "press space": ActionRequest(action_type=ActionType.KEY_PRESS, keys="space"),
            "space": ActionRequest(action_type=ActionType.KEY_PRESS, keys="space"),
            "press tab": ActionRequest(action_type=ActionType.KEY_PRESS, keys="tab"),
            "tab": ActionRequest(action_type=ActionType.KEY_PRESS, keys="tab"),
            "press escape": ActionRequest(action_type=ActionType.KEY_PRESS, keys="esc"),
            "escape": ActionRequest(action_type=ActionType.KEY_PRESS, keys="esc"),
            "press backspace": ActionRequest(action_type=ActionType.KEY_PRESS, keys="backspace"),
            "backspace": ActionRequest(action_type=ActionType.KEY_PRESS, keys="backspace"),
            "delete": ActionRequest(action_type=ActionType.KEY_PRESS, keys="delete"),
            "press delete": ActionRequest(action_type=ActionType.KEY_PRESS, keys="delete"),
            "copy": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+c"),
            "copy that": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+c"),
            "paste": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+v"),
            "paste that": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+v"),
            "cut": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+x"),
            "cut that": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+x"),
            "select all": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+a"),
            "undo": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+z"),
            "undo that": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+z"),
            "redo": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+y"),
            "save": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+s"),
            "save this": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+s"),
            "save as": ActionRequest(action_type=ActionType.KEY_PRESS, keys="f12"),
            "print": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+p"),
            "print this": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+p"),
            "new tab": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+t"),
            "close tab": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+w"),
            "fullscreen": ActionRequest(action_type=ActionType.KEY_PRESS, keys="f11"),
            "full screen": ActionRequest(action_type=ActionType.KEY_PRESS, keys="f11"),
            "developer tools": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+shift+i"),
            "dev tools": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+shift+i"),
            "inspect element": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+shift+i"),
            "bookmarks": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+shift+o"),
            "open bookmarks": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+shift+o"),
            "find and replace": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+h"),
            "replace": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+h"),
            "new line": ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
            "newline": ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
            "indent": ActionRequest(action_type=ActionType.KEY_PRESS, keys="tab"),
            "unindent": ActionRequest(action_type=ActionType.SHORTCUT, keys="shift+tab"),
            "select line": ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="select_line"),
            "delete line": ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="delete_line"),
            "delete word": ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="delete_word"),
            "top of page": ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="page_top"),
            "bottom of page": ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="page_bottom"),
            "incognito": ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="incognito_window"),
            "duplicate tab": ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="duplicate_tab"),
        }

        if cleaned in key_mappings:
            req = key_mappings[cleaned]
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[req],
                reasoning=f"Shortcut/Key '{req.keys}' recognized",
            )

        # 8. Tab & Window shortcuts
        if re.match(r"^(?:(?:open|create)\s+)?(?:a\s+)?(?:new\s+)?tab$", cleaned) or cleaned in ("new tab", "open tab", "another tab", "a new tab"):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+t")],
                reasoning="Open new tab (Ctrl+T)",
            )

        if re.match(r"^(?:close|shut)\s+(?:this\s+|the\s+|current\s+)?tab$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+w")],
                reasoning="Close tab (Ctrl+W)",
            )

        if re.match(r"^(?:reopen|restore)\s+(?:closed\s+)?tab$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+shift+t")],
                reasoning="Reopen closed tab (Ctrl+Shift+T)",
            )

        if re.match(r"^(?:(?:open|create)\s+)?(?:a\s+)?(?:new\s+)?window$", cleaned) or cleaned in ("new window", "open window", "another window", "a new window"):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+n")],
                reasoning="Open new window (Ctrl+N)",
            )

        if re.match(r"^(?:refresh|reload)(?:\s+(?:the\s+|this\s+)?(?:page|tab|window))?$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+r")],
                reasoning="Refresh page (Ctrl+R)",
            )

        # 9. Window actions (close, minimize, maximize, switch)
        m_close = re.match(
            r"^(?:close|exit|quit|kill|terminate|shut down)\s+(?:the\s+)?([a-zA-Z0-9_\-\s\.]+?)(?:\s+(?:app|application|window|program))?$",
            cleaned,
            re.IGNORECASE,
        )
        if m_close:
            target_raw = m_close.group(1).strip()
            if not any(conj in target_raw for conj in (" and ", " then ", ",")):
                if target_raw in ("this", "the", "window", "app", "application", "program", "active", "current"):
                    return IntentResult(
                        raw_transcript=transcript,
                        source=self.name,
                        confidence=0.95,
                        actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.CLOSE)],
                        reasoning="Close active window",
                    )
                else:
                    return IntentResult(
                        raw_transcript=transcript,
                        source=self.name,
                        confidence=0.95,
                        actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, target=target_raw, window_action=WindowActionType.CLOSE)],
                        reasoning=f"Close application or window '{target_raw}'",
                    )

        if re.match(r"^(?:close|exit|quit)(\s+(?:this|the))?(\s+(?:application|app|window|program))?$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.CLOSE)],
                reasoning="Close active window",
            )

        # Target-aware Minimize ("minimize", "minimize window", "minimize chrome", "minimize vscode")
        m_min = re.match(
            r"^minimize(?:\s+(?:the\s+)?([a-zA-Z0-9_\-\s\.]+?)(?:\s+(?:app|application|window|program))?)?$",
            cleaned,
            re.IGNORECASE,
        )
        if m_min:
            t = (m_min.group(1) or "").strip()
            if not t or t in ("this", "the", "window", "app", "application", "program", "active", "current", "it", "this window"):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.MINIMIZE)],
                    reasoning="Minimize active window",
                )
            elif not any(conj in t for conj in (" and ", " then ", ",")):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, target=t, window_action=WindowActionType.MINIMIZE)],
                    reasoning=f"Minimize application or window '{t}'",
                )

        # Target-aware Maximize ("maximize", "maximize window", "maximize chrome", "full screen chrome")
        m_max = re.match(
            r"^(?:maximize|full\s*screen)(?:\s+(?:the\s+)?([a-zA-Z0-9_\-\s\.]+?)(?:\s+(?:app|application|window|program))?)?$",
            cleaned,
            re.IGNORECASE,
        )
        if m_max:
            t = (m_max.group(1) or "").strip()
            if not t or t in ("this", "the", "window", "app", "application", "program", "active", "current", "it", "this window"):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.MAXIMIZE)],
                    reasoning="Maximize active window",
                )
            elif not any(conj in t for conj in (" and ", " then ", ",")):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, target=t, window_action=WindowActionType.MAXIMIZE)],
                    reasoning=f"Maximize application or window '{t}'",
                )

        # Target-aware Restore ("restore", "restore window", "restore chrome", "unmaximize chrome")
        m_rest = re.match(
            r"^(?:restore|unmaximize)(?:\s+(?:the\s+)?([a-zA-Z0-9_\-\s\.]+?)(?:\s+(?:app|application|window|program))?)?$",
            cleaned,
            re.IGNORECASE,
        )
        if m_rest:
            t = (m_rest.group(1) or "").strip()
            if not t or t in ("this", "the", "window", "app", "application", "program", "active", "current", "it", "this window"):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.RESTORE)],
                    reasoning="Restore active window",
                )
            elif not any(conj in t for conj in (" and ", " then ", ",")):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, target=t, window_action=WindowActionType.RESTORE)],
                    reasoning=f"Restore application or window '{t}'",
                )

        # Switch to specific application
        m_focus = re.match(r"^(?:switch to|focus|bring up|go to)\s+(?:the\s+)?([a-zA-Z0-9_\-\s\.]+?)(?:\s+(?:app|application|window|program))?$", cleaned)
        if m_focus:
            target_app = m_focus.group(1).strip()
            if not any(conj in target_app for conj in (" and ", " then ", ",")):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, target=target_app, window_action=WindowActionType.SWITCH)],
                    reasoning=f"Switch to window '{target_app}'",
                )

        if re.match(r"^(switch\s+window|next\s+window|alt\s+tab)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="alt+tab")],
                reasoning="Switch window",
            )

        # 10. Application Launching vs On-Screen Element / Profile Selection
        m_launch = re.match(r"^(?:open|launch|start|run)\s+(?:the\s+)?(.+?)(?:\s+(?:app|application|program))?$", cleaned)
        if m_launch:
            app_name = m_launch.group(1).strip()
            if not any(conj in app_name for conj in (" and ", " then ", ",")):
                # Guard: Detect if app_name is actually an on-screen UI element, card, or profile selection
                ui_markers = (
                    "profile", "prfile", "profle", "card", "item", "option", "selection",
                    "tile", "button", "link", "icon", "avatar", "dropdown", "box",
                    "from the selection", "from selection", "from the list", "from list",
                )
                is_ui_element = any(m in app_name for m in ui_markers) or bool(
                    re.match(r"^(?:first|second|third|fourth|fifth|last|1st|2nd|3rd)\b", app_name)
                )

                if is_ui_element:
                    target = app_name
                    target = re.sub(r"^(?:a|an|the)\s+", "", target)
                    target = re.sub(r"\s+from\s+(?:the\s+)?(?:selection|list)$", "", target)
                    # Strip prefix (e.g. "profile sonu" -> "sonu")
                    m_pref = re.match(r"^(?:profile|prfile|profle|card|item|tile|option)\s+(.+)$", target, re.IGNORECASE)
                    if m_pref and m_pref.group(1).strip() not in ("from the selection", "from selection", "from the list", "from list"):
                        target = m_pref.group(1).strip()
                    else:
                        for suf in (" profile", " prfile", " profle", " card", " item", " tile", " option"):
                            if target.endswith(suf) and len(target) > len(suf):
                                target = target[:-len(suf)].strip()
                                break
                    return IntentResult(
                        raw_transcript=transcript,
                        source=self.name,
                        confidence=0.95,
                        actions=[ActionRequest(action_type=ActionType.CLICK, target=target)],
                        reasoning=f"Select UI element '{target}'",
                    )

                if "tab" not in app_name and app_name not in ("new tab", "tab", "a new tab") and not app_name.endswith(" menu"):
                    return IntentResult(
                        raw_transcript=transcript,
                        source=self.name,
                        confidence=0.95,
                        actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=app_name)],
                        reasoning=f"Launch application '{app_name}'",
                    )

        # 11. Mouse Movement Commands
        m_move_mouse = re.match(r"^(?:move\s+(?:the\s+)?mouse|cursor)\s+(center|left|right|up|down)$", cleaned)
        if m_move_mouse:
            direction = m_move_mouse.group(1).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.MOVE_MOUSE, target=direction)],
                reasoning=f"Move mouse to {direction}",
            )

        # 12. Typing Text
        m_type = re.match(r"^(type|write|enter text|input|dictate)\s+(.+)$", cleaned)
        if m_type:
            text_to_type = m_type.group(2).strip()
            # If spoken text ends with recipient pronoun ('to her', 'to him', 'to them'), route to chat input
            m_pronoun = re.match(r"^(.+?)\s+to\s+(?:her|him|them)$", text_to_type, re.IGNORECASE)
            if m_pronoun:
                raw_content = m_pronoun.group(1).strip()
                cleaned_text = clean_spoken_text(raw_content, capitalize_first=False)
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[
                        ActionRequest(action_type=ActionType.CLICK, target="Type a message", target_type="edit"),
                        ActionRequest(action_type=ActionType.TYPE, text=cleaned_text, target=None),
                    ],
                    reasoning=f"Focus message box and type '{cleaned_text}'",
                )

            m_in_target = re.match(r"^(this\s+in\s+the\s+([a-zA-Z0-9_\s]+)\s*[:]\s*)(.+)$", text_to_type)
            if m_in_target:
                raw_content = m_in_target.group(3).strip()
                cleaned_content = clean_spoken_text(raw_content, capitalize_first=False)
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.9,
                    actions=[
                        ActionRequest(action_type=ActionType.CLICK, target=m_in_target.group(2).strip(), target_type="edit"),
                        ActionRequest(action_type=ActionType.TYPE, text=cleaned_content, target=None),
                    ],
                    reasoning="Click target field and type text",
                )

            cleaned_text = clean_spoken_text(text_to_type, capitalize_first=False)
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.TYPE, text=cleaned_text, target=None)],
                reasoning=f"Type '{cleaned_text}' directly at cursor",
            )

        # 13. Tree & Menu Interactions
        m_expand = re.match(r"^expand(\s+(the|item|node))?\s+(.+)$", cleaned)
        if m_expand:
            target = m_expand.group(3).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.EXPAND, target=target)],
                reasoning=f"Expand element '{target}'",
            )

        m_collapse = re.match(r"^collapse(\s+(the|item|node))?\s+(.+)$", cleaned)
        if m_collapse:
            target = m_collapse.group(3).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.COLLAPSE, target=target)],
                reasoning=f"Collapse element '{target}'",
            )

        m_open_menu = re.match(r"^(open|select)(\s+the)?\s+(.+?)\s+menu$", cleaned)
        if m_open_menu:
            menu_name = m_open_menu.group(3).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SELECT, menu_path=menu_name, target=menu_name, target_type="menu")],
                reasoning=f"Open menu '{menu_name}'",
            )

        m_select_val = re.match(r"^select\s+(.+?)\s+(from|in)(\s+the)?\s+(.+)$", cleaned)
        if m_select_val:
            val = m_select_val.group(1).strip()
            tgt = m_select_val.group(4).strip()
            tgt_type = "combobox"
            for suffix in (" dropdown", " combobox", " list", " menu"):
                if tgt.endswith(suffix):
                    tgt_type = suffix.strip()
                    tgt = tgt[:-len(suffix)].strip()
                    break
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SELECT, target=tgt, target_type=tgt_type, select_value=val)],
                reasoning=f"Select '{val}' in '{tgt}'",
            )

        # 14. Mouse Clicks & Hovers
        m_hover = re.match(r"^(?:hover|move\s+to|point\s+at)(\s+(?:on|over|the))?\s+(.+)$", cleaned)
        if m_hover:
            target = m_hover.group(2).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.9,
                actions=[ActionRequest(action_type=ActionType.HOVER, target=target)],
                reasoning=f"Hover on element '{target}'",
            )

        m_middle_click = re.match(r"^(?:middle\s+click)(\s+(?:on|the))?\s+(.+)$", cleaned)
        if m_middle_click:
            target = m_middle_click.group(2).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.9,
                actions=[ActionRequest(action_type=ActionType.MIDDLE_CLICK, target=target)],
                reasoning=f"Middle-click element '{target}'",
            )

        m_double_click = re.match(r"^(?:double\s+click)(\s+(?:on|the))?\s+(.+)$", cleaned)
        if m_double_click:
            target = m_double_click.group(2).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.9,
                actions=[ActionRequest(action_type=ActionType.DOUBLE_CLICK, target=target)],
                reasoning=f"Double-click element '{target}'",
            )

        m_right_click = re.match(r"^(?:right\s+click)(\s+(?:on|the))?\s+(.+)$", cleaned)
        if m_right_click:
            target = m_right_click.group(2).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.9,
                actions=[ActionRequest(action_type=ActionType.RIGHT_CLICK, target=target)],
                reasoning=f"Right-click element '{target}'",
            )

        m_click = re.match(r"^(?:click|press|tap|hit|select|pick|choose)(?:\s+(?:on|in|at|onto|the|on\s+the|in\s+the|a|an))?\s+(.+)$", cleaned, re.IGNORECASE)
        if m_click:
            target = m_click.group(1).strip()
            if not any(conj in target for conj in (" and ", " then ", ",")):
                target_type = None
                spatial_landmark = None
                relative_anchor = None
                relative_relation = None

                # 1. Extract spatial landmark zones: "in top right corner", "at the bottom right", etc.
                zone_pattern = r"\s+(?:in|at|on|towards)\s+(?:the\s+)?(top\s+right|upper\s+right|top\s+left|upper\s+left|bottom\s+right|lower\s+right|bottom\s+left|lower\s+left|top|upper|bottom|lower|left|right|center|middle)(?:\s+corner|\s+side|\s+area|\s+part|\s+region)?$"
                m_zone = re.search(zone_pattern, target, re.IGNORECASE)
                if m_zone:
                    raw_zone = m_zone.group(1).lower().replace("upper", "top").replace("lower", "bottom").replace("middle", "center")
                    spatial_landmark = "_".join(raw_zone.split())
                    target = target[:m_zone.start()].strip()

                # 2. Extract relative anchor relations: "next to sonu", "below prompt", etc.
                rel_pattern = r"\s+(next\s+to|beside|to\s+the\s+right\s+of|right\s+of|to\s+the\s+left\s+of|left\s+of|below|under|underneath|above|near|close\s+to)\s+(?:the\s+)?(.+)$"
                m_rel = re.search(rel_pattern, target, re.IGNORECASE)
                if m_rel:
                    raw_rel = m_rel.group(1).lower().strip().replace("to the ", "").replace(" ", "_")
                    relative_relation = raw_rel
                    relative_anchor = m_rel.group(2).strip()
                    target = target[:m_rel.start()].strip()

                target = re.sub(r"^(?:the|a|an)\s+", "", target).strip()
                target = re.sub(r"\s+from\s+(?:the\s+)?(?:selection|list)$", "", target).strip()
                m_pref = re.match(r"^(?:profile|prfile|profle|card|item|tile|option)\s+(.+)$", target, re.IGNORECASE)
                if m_pref and m_pref.group(1).strip() not in ("from the selection", "from selection", "from the list", "from list"):
                    target = m_pref.group(1).strip()
                else:
                    for suffix, stype in (
                        (" button", "button"),
                        (" menu", "menu"),
                        (" tab", "tab"),
                        (" link", "link"),
                        (" profile", None),
                        (" prfile", None),
                        (" profle", None),
                        (" icon", None),
                        (" card", None),
                        (" item", None),
                        (" option", None),
                        (" tile", None),
                        (" selection", None),
                    ):
                        if target.lower().endswith(suffix) and len(target) > len(suffix):
                            if stype:
                                target_type = stype
                            target = target[:-len(suffix)].strip()
                            break

                # If target is generic (e.g. "button", "icon") but spatial landmark is specified, keep target_type
                if target.lower() in ("button", "icon", "control"):
                    target_type = "button"

                reasoning_parts = [f"Click element '{target}'"]
                if spatial_landmark:
                    reasoning_parts.append(f"in zone '{spatial_landmark}'")
                if relative_anchor:
                    reasoning_parts.append(f"'{relative_relation}' anchor '{relative_anchor}'")

                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.9,
                    actions=[ActionRequest(
                        action_type=ActionType.CLICK,
                        target=target,
                        target_type=target_type,
                        spatial_landmark=spatial_landmark,
                        relative_anchor=relative_anchor,
                        relative_relation=relative_relation,
                    )],
                    reasoning=" ".join(reasoning_parts),
                )


        # 15. Scrolling
        m_scroll = re.match(
            r"^(?:please\s+)?(?:just\s+)?(?:mouse\s+)?scroll\s*(?:the\s+page\s*)?(down|up)?(?:\s+(?:a\s+bit|a\s+little|more|a\s+lot|slowly|fast))?$",
            cleaned,
            re.IGNORECASE,
        )
        if not m_scroll:
            m_scroll = re.match(r"^(page\s+down|page\s+up)$", cleaned, re.IGNORECASE)

        if m_scroll:
            direction_str = (m_scroll.group(1) or "down").lower()
            direction = "up" if "up" in direction_str else "down"
            amount = 4
            if "a bit" in cleaned or "a little" in cleaned:
                amount = 2
            elif "a lot" in cleaned or "more" in cleaned:
                amount = 8
            elif "page" in cleaned:
                amount = 6

            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SCROLL, scroll_direction=direction, scroll_amount=amount)],
                reasoning=f"Scroll {direction} (amount={amount})",
            )

        # If no deterministic rule matched, return None to trigger LLM tier
        return None
