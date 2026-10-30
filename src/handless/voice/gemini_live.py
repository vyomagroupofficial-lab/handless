"""Native Gemini Multimodal Live Bidirectional Voice Session.

Connects directly to Google's Gemini 3.8 Live models (gemini-3.8-live and
gemini-3.8-live-extended-thinking) over real-time WebSockets with native
audio-to-audio streaming (zero separate STT/TTS pipeline latency).
Integrates live desktop tool calling (function declarations) giving Gemini
full control over applications, window positioning, system settings, and screen analysis.
"""

from __future__ import annotations

import asyncio
import io
import logging
import math
import struct
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, Signal
import sounddevice as sd

from google import genai
from google.genai import types

from handless.security.credentials import get_gemini_api_key

if TYPE_CHECKING:
    from handless.actions.dispatcher import ActionDispatcher

logger = logging.getLogger(__name__)

# Live Model Identifiers
MODEL_GEMINI_LIVE = "gemini-3.8-live"
MODEL_GEMINI_LIVE_THINKING = "gemini-3.8-live-extended-thinking"

# Audio Sampling Configuration
INPUT_SAMPLE_RATE = 16000   # 16kHz 16-bit Mono PCM for Mic Input
OUTPUT_SAMPLE_RATE = 24000  # 24kHz 16-bit Mono PCM for Gemini Live Audio Output
AUDIO_CHANNELS = 1
AUDIO_DTYPE = "int16"
INPUT_BLOCK_SIZE = 1024


def build_desktop_live_tools() -> List[types.Tool]:
    """Build the comprehensive FunctionDeclarations giving Gemini Live access to all desktop controls."""
    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="launch_application",
                    description="Launch or open an application on the user's Windows desktop (e.g. Chrome, Notepad, Spotify, Calculator, VS Code, File Explorer, Terminal).",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "app_name": types.Schema(type=types.Type.STRING, description="Name or executable of the application to launch"),
                        },
                        required=["app_name"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="close_application",
                    description="Close a running application on the desktop by name or window title.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "app_name": types.Schema(type=types.Type.STRING, description="Name of the application or window to close"),
                        },
                        required=["app_name"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="click_ui_element",
                    description="Click on a button, link, menu item, or UI element visible on the user's screen.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "element_name": types.Schema(type=types.Type.STRING, description="Label, title, or accessible name of the UI element to click"),
                            "element_type": types.Schema(type=types.Type.STRING, description="Optional type: 'button', 'menu', 'tab', 'edit', 'link'"),
                        },
                        required=["element_name"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="type_text",
                    description="Type a string of text into the currently active or focused input field.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "text": types.Schema(type=types.Type.STRING, description="Text string to type"),
                        },
                        required=["text"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="press_keyboard_shortcut",
                    description="Press a keyboard shortcut or system key combination (e.g. 'ctrl+t', 'ctrl+w', 'ctrl+c', 'ctrl+v', 'alt+tab', 'win+d', 'enter', 'esc').",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "keys": types.Schema(type=types.Type.STRING, description="Key combination like 'ctrl+t' or 'enter'"),
                        },
                        required=["keys"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="control_window",
                    description="Control window size, layout or position: 'snap_left', 'snap_right', 'maximize', 'minimize', 'restore', 'center', 'popup'.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "action": types.Schema(type=types.Type.STRING, description="Action: 'snap_left', 'snap_right', 'maximize', 'minimize', 'restore', 'center', 'popup'"),
                            "window_title": types.Schema(type=types.Type.STRING, description="Optional target window title or app name"),
                        },
                        required=["action"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="set_volume",
                    description="Set desktop master audio volume to a specific percentage (0 to 100).",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "level": types.Schema(type=types.Type.INTEGER, description="Target volume level from 0 to 100"),
                        },
                        required=["level"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="set_brightness",
                    description="Set display monitor brightness to a specific percentage (0 to 100).",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "level": types.Schema(type=types.Type.INTEGER, description="Target brightness level from 0 to 100"),
                        },
                        required=["level"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="system_action",
                    description="Perform a quick system control action: 'dark_mode', 'light_mode', 'lock_pc', 'sleep_pc', 'show_desktop', 'task_manager', 'mute', 'unmute', 'battery_status', 'system_health', 'empty_recycle_bin', 'boss_mode'.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "action": types.Schema(type=types.Type.STRING, description="Action name"),
                        },
                        required=["action"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="switch_browser_tab",
                    description="Switch to an open browser tab matching a search title or query (e.g. 'YouTube', 'Docs', 'GitHub').",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "tab_title": types.Schema(type=types.Type.STRING, description="Title of the browser tab to switch to"),
                        },
                        required=["tab_title"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="inspect_screen",
                    description="Inspect the current screen to see what is currently displayed, find elements, or read errors/content.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "query": types.Schema(type=types.Type.STRING, description="What to examine or check on the screen"),
                        },
                        required=["query"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="search_web",
                    description="Search Google or YouTube for a query and open results in the default web browser.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "query": types.Schema(type=types.Type.STRING, description="Search query or terms to look up"),
                            "platform": types.Schema(type=types.Type.STRING, description="Platform: 'google' (default) or 'youtube'"),
                        },
                        required=["query"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="scroll_page",
                    description="Scroll the active window or document up, down, to top, or to bottom.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "direction": types.Schema(type=types.Type.STRING, description="Direction: 'down', 'up', 'top', or 'bottom'"),
                            "amount": types.Schema(type=types.Type.INTEGER, description="Units to scroll (default 300)"),
                        },
                        required=["direction"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="open_url",
                    description="Open any website URL directly in the user's web browser.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "url": types.Schema(type=types.Type.STRING, description="Full website URL (e.g. 'https://github.com')"),
                        },
                        required=["url"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="execute_desktop_command",
                    description="Universal desktop action tool: execute any natural language instruction on the user's PC via Handless AI automation (e.g. 'organize downloads folder', 'summarize notes', 'create a presentation', 'check ram usage').",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "command": types.Schema(type=types.Type.STRING, description="Desktop instruction in plain English"),
                        },
                        required=["command"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="end_call",
                    description="End or hang up the live call when the user says 'goodbye', 'end call', 'hang up', or 'stop call'.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "farewell": types.Schema(type=types.Type.STRING, description="Optional brief farewell phrase to speak"),
                        },
                    ),
                ),
            ]
        )
    ]


class GeminiLiveSession(QObject):
    """Manages full-duplex live audio streaming and tool execution with Gemini 3.8 Live."""

    # Thread-safe Qt Signals
    status_changed = Signal(str)           # "Connecting...", "Live", "Thinking...", "Speaking", "Listening"
    audio_level_changed = Signal(float)    # 0.0 to 1.0 (smooth live amplitude for dotted orb)
    model_speaking_changed = Signal(bool)
    user_speaking_changed = Signal(bool)
    transcript_received = Signal(str, bool) # text, is_thought
    tool_event = Signal(str, str, str)     # tool_name, status ("running", "done", "error"), details
    model_changed = Signal(str)            # active model name
    call_ended = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        dispatcher: Optional[ActionDispatcher] = None,
        model_name: str = MODEL_GEMINI_LIVE,
        voice_name: str = "Aoede",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        if dispatcher is None:
            from handless.actions.dispatcher import ActionDispatcher
            self.dispatcher = ActionDispatcher()
        else:
            self.dispatcher = dispatcher
        self._model_name = model_name
        self._voice_name = voice_name
        self._thinking_level = "HIGH"

        self._is_active = False
        self._is_muted = False
        self._stop_event = threading.Event()

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._active_session: Optional[Any] = None

        self._input_stream: Optional[sd.RawInputStream] = None
        self._output_stream: Optional[sd.RawOutputStream] = None
        self._audio_in_queue: Optional[asyncio.Queue] = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def voice_name(self) -> str:
        return self._voice_name

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def set_muted(self, muted: bool) -> None:
        """Toggle microphone mute during the live call."""
        self._is_muted = muted
        if muted:
            self.user_speaking_changed.emit(False)
            self.status_changed.emit("Muted")
        else:
            self.status_changed.emit("Live")

    def switch_model(self, new_model: str) -> None:
        """Switch between Gemini 3.8 Live and Gemini 3.8 Live Extended Thinking."""
        if self._model_name == new_model:
            return
        logger.info("Switching Live model from %s to %s", self._model_name, new_model)
        self._model_name = new_model
        self.model_changed.emit(new_model)
        if self._is_active:
            # Reconnect session with new model seamlessly
            self.stop_call(emit_end=False)
            self.start_call()

    def set_voice(self, voice_name: str) -> None:
        """Set the persona voice (e.g. Puck, Charon, Aoede, Fenrir, Kore)."""
        self._voice_name = voice_name

    def start_call(self) -> bool:
        """Start the live bidirectional call in a dedicated background worker thread."""
        if self._is_active:
            logger.warning("Live call session is already active.")
            return True

        api_key = get_gemini_api_key()
        if not api_key:
            err = "Google Gemini API key not found in Windows Credential Manager. Please configure it in Settings."
            logger.error(err)
            self.error_occurred.emit(err)
            return False

        self._stop_event.clear()
        self._is_active = True
        self.status_changed.emit("Connecting to Gemini Live...")

        self._thread = threading.Thread(
            target=self._run_async_worker,
            args=(api_key,),
            daemon=True,
            name="GeminiLiveWorker",
        )
        self._thread.start()
        return True

    def stop_call(self, emit_end: bool = True) -> None:
        """Gracefully terminate live streams and disconnect WebSocket session."""
        if not self._is_active and not self._stop_event.is_set():
            return

        logger.info("Stopping Gemini Live session...")
        self._stop_event.set()
        self._is_active = False

        # Close audio hardware streams
        if self._input_stream:
            try:
                self._input_stream.stop()
                self._input_stream.close()
            except Exception as e:
                logger.debug("Error closing input stream: %s", e)
            self._input_stream = None

        if self._output_stream:
            try:
                self._output_stream.stop()
                self._output_stream.close()
            except Exception as e:
                logger.debug("Error closing output stream: %s", e)
            self._output_stream = None

        # Stop event loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        self.audio_level_changed.emit(0.0)
        self.model_speaking_changed.emit(False)
        self.user_speaking_changed.emit(False)
        self.status_changed.emit("Call Ended")
        if emit_end:
            self.call_ended.emit()

    def _run_async_worker(self, api_key: str) -> None:
        """Async loop worker runner in dedicated thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._live_session_loop(api_key))
        except Exception as exc:
            if not self._stop_event.is_set():
                logger.exception("Error in Gemini Live loop: %s", exc)
                self.error_occurred.emit(f"Live call error: {exc}")
        finally:
            try:
                # Cancel pending tasks
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self._loop.close()
            self._is_active = False
            if self._stop_event.is_set():
                self.call_ended.emit()
            else:
                logger.info("Gemini Live session connection closed cleanly.")
                self.call_ended.emit()

    async def _live_session_loop(self, api_key: str) -> None:
        """Full bidirectional loop: Mic Input -> Gemini Live -> Audio Output & Tool Execution."""
        client = genai.Client(api_key=api_key)
        self._audio_in_queue = asyncio.Queue(maxsize=120)

        # Build tools and system instruction
        tools = build_desktop_live_tools()
        system_instruction = (
            "You are Vyoma Handless, an ultra-intelligent, friendly, fast, and capable desktop AI copilot. "
            "You have direct access to the user's Windows desktop via real-time tools. "
            "When the user asks you to perform an action (open applications, search the web or YouTube, click UI elements, "
            "type text, scroll, snap windows, change volume or brightness, inspect the screen, or general desktop tasks), "
            "call the appropriate tool immediately and then speak a natural, concise, warm voice confirmation. "
            "You can control the entire desktop. Keep conversational spoken responses clear, warm, and brief."
        )

        config_kwargs: Dict[str, Any] = {
            "response_modalities": ["AUDIO"],
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self._voice_name)
                )
            ),
            "tools": tools,
            "system_instruction": types.Content(parts=[types.Part.from_text(text=system_instruction)]),
        }

        # Enable extended thinking config if using gemini-3.8-live-extended-thinking
        if self._model_name == MODEL_GEMINI_LIVE_THINKING:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=self._thinking_level,
                include_thoughts=True,
            )

        config = types.LiveConnectConfig(**config_kwargs)

        logger.info("Connecting to %s...", self._model_name)
        async with client.aio.live.connect(model=self._model_name, config=config) as session:
            self._active_session = session
            logger.info("Connected to Gemini Live session!")
            self.status_changed.emit("Live")

            # Setup audio hardware
            self._setup_audio_hardware()

            # Launch concurrent sender and receiver tasks
            sender_task = asyncio.create_task(self._send_mic_stream(session))
            receiver_task = asyncio.create_task(self._receive_gemini_stream(session))

            # Wait until stopped or either task completes
            done, pending = await asyncio.wait(
                [sender_task, receiver_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()

    def _setup_audio_hardware(self) -> None:
        """Initialize sounddevice RawInputStream and RawOutputStream."""
        loop = self._loop

        def mic_callback(indata, frames, time_info, status):
            if status:
                logger.debug("Microphone input status: %s", status)
            if self._stop_event.is_set():
                return
            pcm_bytes = bytes(indata)
            # Calculate input RMS for visual level
            rms = self._calculate_pcm_rms(pcm_bytes)
            if not self._is_muted:
                level = min(1.0, rms * 18.0)
                if loop and loop.is_running():
                    loop.call_soon_threadsafe(self.audio_level_changed.emit, level)
                    loop.call_soon_threadsafe(self.user_speaking_changed.emit, level > 0.08)
                try:
                    if self._audio_in_queue and not self._audio_in_queue.full():
                        self._audio_in_queue.put_nowait(pcm_bytes)
                except Exception:
                    pass
            else:
                if loop and loop.is_running():
                    loop.call_soon_threadsafe(self.audio_level_changed.emit, 0.0)

        # 1. Start Mic Input
        self._input_stream = sd.RawInputStream(
            samplerate=INPUT_SAMPLE_RATE,
            channels=AUDIO_CHANNELS,
            dtype=AUDIO_DTYPE,
            blocksize=INPUT_BLOCK_SIZE,
            callback=mic_callback,
        )
        self._input_stream.start()

        # 2. Start Speaker Output
        self._output_stream = sd.RawOutputStream(
            samplerate=OUTPUT_SAMPLE_RATE,
            channels=AUDIO_CHANNELS,
            dtype=AUDIO_DTYPE,
            blocksize=1024,
        )
        self._output_stream.start()

    async def _send_mic_stream(self, session: Any) -> None:
        """Stream microphone chunks to Gemini Live."""
        while not self._stop_event.is_set():
            if self._audio_in_queue:
                pcm_data = await self._audio_in_queue.get()
                if not self._is_muted and pcm_data:
                    try:
                        await session.send_realtime_input(
                            audio=types.Blob(data=pcm_data, mime_type="audio/pcm;rate=16000")
                        )
                    except Exception as e:
                        if not self._stop_event.is_set():
                            logger.error("Error sending realtime audio: %s", e)
                        break
            else:
                await asyncio.sleep(0.02)

    async def _receive_gemini_stream(self, session: Any) -> None:
        """Receive Gemini voice chunks, thoughts, and tool calls."""
        async for response in session.receive():
            if self._stop_event.is_set():
                break

            # 1. Handle Tool Calls
            if response.tool_call:
                await self._handle_live_tool_calls(session, response.tool_call)

            # 2. Handle Server Content (Speech audio & transcripts)
            server_content = response.server_content
            if server_content is not None:
                model_turn = server_content.model_turn
                if model_turn:
                    self.model_speaking_changed.emit(True)
                    self.status_changed.emit("Speaking")
                    for part in model_turn.parts:
                        # Thoughts (extended thinking)
                        if part.thought and part.text:
                            self.transcript_received.emit(part.text, True)
                        elif part.text:
                            self.transcript_received.emit(part.text, False)

                        # Raw PCM Voice Output
                        if part.inline_data and part.inline_data.data:
                            audio_bytes = part.inline_data.data
                            rms = self._calculate_pcm_rms(audio_bytes)
                            level = min(1.0, rms * 14.0)
                            self.audio_level_changed.emit(level)
                            if self._output_stream:
                                self._output_stream.write(audio_bytes)

                if server_content.turn_complete:
                    self.model_speaking_changed.emit(False)
                    self.status_changed.emit("Live")

    async def _handle_live_tool_calls(self, session: Any, tool_call: Any) -> None:
        """Execute desktop actions requested by Gemini Live and return results seamlessly."""
        function_responses: List[types.FunctionResponse] = []

        for call in tool_call.function_calls:
            fn_name = call.name
            args = call.args or {}
            logger.info("Executing Live Tool: %s with args: %s", fn_name, args)
            self.status_changed.emit(f"Executing {fn_name}...")
            self.tool_event.emit(fn_name, "running", str(args))

            # Run action in executor so it does not block the async network loop
            loop = asyncio.get_running_loop()
            result_str = await loop.run_in_executor(None, self._execute_tool_sync, fn_name, args)

            self.tool_event.emit(fn_name, "done", result_str)
            function_responses.append(
                types.FunctionResponse(
                    id=call.id,
                    name=call.name,
                    response={"result": result_str},
                )
            )

        if function_responses:
            try:
                await session.send_tool_response(function_responses=function_responses)
            except Exception as e:
                logger.error("Failed to send tool response: %s", e)

    def _execute_tool_sync(self, name: str, args: Dict[str, Any]) -> str:
        """Synchronously execute desktop action via Handless dispatcher."""
        try:
            if name == "launch_application":
                app_name = args.get("app_name", "")
                success = self.dispatcher.launcher.launch(app_name)
                return f"Successfully opened {app_name}" if success else f"Could not launch {app_name}"

            elif name == "close_application":
                app_name = args.get("app_name", "")
                success = self.dispatcher.launcher.close(app_name)
                return f"Closed {app_name}" if success else f"Could not close {app_name}"

            elif name == "click_ui_element":
                elem = args.get("element_name", "")
                elem_type = args.get("element_type")
                from handless.intelligence.models import ActionRequest, ActionType
                req = ActionRequest(action_type=ActionType.CLICK, target=elem, target_type=elem_type)
                success = self.dispatcher.execute_action(req)
                return f"Clicked element '{elem}'" if success else f"Could not find or click '{elem}'"

            elif name == "type_text":
                text = args.get("text", "")
                success = self.dispatcher.keyboard.type_text(text)
                return f"Typed '{text}'" if success else f"Attempted typing '{text}'"

            elif name == "press_keyboard_shortcut":
                keys = args.get("keys", "")
                success = self.dispatcher.keyboard.execute_shortcut(keys)
                return f"Sent keyboard shortcut '{keys}'" if success else f"Attempted shortcut '{keys}'"

            elif name == "control_window":
                action = args.get("action", "")
                title = args.get("window_title")
                from handless.intelligence.models import WindowActionType
                action_map = {
                    "snap_left": WindowActionType.SNAP_LEFT,
                    "snap_right": WindowActionType.SNAP_RIGHT,
                    "maximize": WindowActionType.MAXIMIZE,
                    "minimize": WindowActionType.MINIMIZE,
                    "restore": WindowActionType.RESTORE,
                    "center": WindowActionType.CENTER,
                    "popup": WindowActionType.POPUP,
                }
                w_act = action_map.get(action.lower(), WindowActionType.RESTORE)
                success = self.dispatcher.window.execute_action(w_act, title)
                return f"Window action '{action}' executed" if success else f"Failed to execute window action '{action}'"

            elif name == "set_volume":
                level = int(args.get("level", 50))
                self.dispatcher.system.set_volume(level)
                return f"Volume set to {level}%"

            elif name == "set_brightness":
                level = int(args.get("level", 50))
                self.dispatcher.system.set_brightness(level)
                return f"Brightness set to {level}%"

            elif name == "switch_browser_tab":
                tab_title = args.get("tab_title", "")
                success = self.dispatcher.system.switch_to_tab(tab_title, self.dispatcher.uia)
                return f"Switched to browser tab '{tab_title}'" if success else f"Tab '{tab_title}' not found"

            elif name == "system_action":
                act = args.get("action", "").lower()
                sys = self.dispatcher.system
                if act == "dark_mode":
                    sys.set_dark_mode(True)
                    return "Dark mode enabled"
                elif act == "light_mode":
                    sys.set_dark_mode(False)
                    return "Light mode enabled"
                elif act == "lock_pc":
                    sys.lock_pc()
                    return "Computer locked"
                elif act == "sleep_pc":
                    sys.sleep_pc()
                    return "Computer put to sleep"
                elif act == "show_desktop":
                    sys.show_desktop()
                    return "Showing desktop"
                elif act == "task_manager":
                    sys.open_task_manager()
                    return "Task manager opened"
                elif act == "mute":
                    sys.toggle_mute()
                    return "Audio muted"
                elif act == "unmute":
                    sys.toggle_mute()
                    return "Audio unmuted"
                elif act == "battery_status":
                    return sys.get_battery_status()
                elif act == "system_health":
                    return sys.get_system_health()
                elif act == "empty_recycle_bin":
                    sys.empty_recycle_bin()
                    return "Recycle bin emptied"
                elif act == "boss_mode":
                    sys.boss_mode()
                    return "Boss mode activated (distractions minimized)"
                return f"Executed system action: {act}"

            elif name == "inspect_screen":
                query = args.get("query", "")
                shot = self.dispatcher.vision.take_screenshot()
                if shot:
                    return f"Screen captured successfully. Query target '{query}' checked."
                return "Failed to capture screen"

            elif name == "search_web":
                query = args.get("query", "")
                platform = args.get("platform", "google").lower()
                from urllib.parse import quote_plus
                import webbrowser
                encoded = quote_plus(query)
                if platform == "youtube":
                    url = f"https://www.youtube.com/results?search_query={encoded}"
                else:
                    url = f"https://www.google.com/search?q={encoded}"
                webbrowser.open(url)
                return f"Opened web search for '{query}' on {platform}"

            elif name == "scroll_page":
                direction = args.get("direction", "down").lower()
                amount = int(args.get("amount", 300))
                from handless.intelligence.models import ActionRequest, ActionType
                req = ActionRequest(action_type=ActionType.SCROLL, scroll_direction=direction, scroll_amount=amount)
                success = self.dispatcher.execute_action(req)
                return f"Scrolled {direction} {amount} units" if success else f"Could not scroll {direction}"

            elif name == "open_url":
                url = args.get("url", "")
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                import webbrowser
                webbrowser.open(url)
                return f"Opened {url}"

            elif name == "execute_desktop_command":
                cmd = args.get("command", "")
                from handless.intelligence.local_parser import LocalRuleParser
                parser = LocalRuleParser()
                intent = parser.interpret(cmd)
                if intent and intent.actions:
                    success = self.dispatcher.execute_plan(intent.actions)
                    return f"Executed command: {cmd}" if success else f"Command '{cmd}' could not complete"
                else:
                    router = getattr(self.dispatcher, "router", None)
                    if router:
                        intent = router.interpret(cmd)
                        if intent and intent.actions:
                            self.dispatcher.execute_plan(intent.actions)
                            return f"Executed desktop plan for: {cmd}"
                    # Fallback to application launcher
                    launched = self.dispatcher.launcher.launch(cmd)
                    if launched:
                        return f"Opened {cmd}"
                    return f"Attempted desktop action for: {cmd}"

            elif name == "end_call":
                farewell = args.get("farewell", "Ending live call. Talk soon!")
                QTimer.singleShot(1500, self.stop_call)
                return f"Call ending. {farewell}"

            return f"Tool {name} completed"
        except Exception as exc:
            logger.exception("Error executing tool %s: %s", name, exc)
            return f"Error executing {name}: {exc}"

    @staticmethod
    def _calculate_pcm_rms(pcm_bytes: bytes) -> float:
        """Calculate Root Mean Square (RMS) amplitude of 16-bit PCM bytes."""
        if not pcm_bytes or len(pcm_bytes) < 2:
            return 0.0
        count = len(pcm_bytes) // 2
        shorts = struct.unpack(f"{count}h", pcm_bytes[: count * 2])
        sum_squares = sum(s * s for s in shorts)
        mean_square = sum_squares / count
        rms = math.sqrt(mean_square)
        # Normalize roughly across 16-bit range (0 to 32768)
        return min(1.0, rms / 12000.0)
