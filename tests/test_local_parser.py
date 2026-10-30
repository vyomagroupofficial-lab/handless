import pytest
from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType, WindowActionType


@pytest.fixture
def parser():
    return LocalRuleParser()


def test_open_application(parser):
    res = parser.interpret("Open Chrome")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[0].target == "chrome"

    res = parser.interpret("launch notepad")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[0].target == "notepad"


def test_click_element(parser):
    res = parser.interpret("Click the search button")
    assert res is not None
    assert res.actions[0].action_type == ActionType.CLICK
    assert res.actions[0].target == "search"
    assert res.actions[0].target_type == "button"

    res = parser.interpret("double click the folder")
    assert res is not None
    assert res.actions[0].action_type == ActionType.DOUBLE_CLICK
    assert res.actions[0].target == "folder"


def test_type_text(parser):
    res = parser.interpret("Type Minecraft")
    assert res is not None
    assert res.actions[0].action_type == ActionType.TYPE
    assert res.actions[0].text == "minecraft"


def test_window_management(parser):
    res = parser.interpret("close this application")
    assert res is not None
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.CLOSE

    res = parser.interpret("minimize window")
    assert res is not None
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.MINIMIZE


def test_emergency_stop(parser):
    res = parser.interpret("stop")
    assert res is not None
    assert res.actions[0].target == "emergency_stop"


def test_shortcuts(parser):
    res = parser.interpret("copy that")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SHORTCUT
    assert res.actions[0].keys == "ctrl+c"

    res = parser.interpret("press enter")
    assert res is not None
    assert res.actions[0].action_type == ActionType.KEY_PRESS
    assert res.actions[0].keys == "enter"


def test_select_combobox(parser):
    res = parser.interpret("select Arial from the font dropdown")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SELECT
    assert res.actions[0].select_value == "arial"
    assert res.actions[0].target == "font"
    assert res.actions[0].target_type == "dropdown"

    res = parser.interpret("select Bold in font style")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SELECT
    assert res.actions[0].select_value == "bold"
    assert res.actions[0].target == "font style"


def test_menu_navigation(parser):
    res = parser.interpret("open the File menu")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SELECT
    assert res.actions[0].menu_path == "file"
    assert res.actions[0].target_type == "menu"


def test_expand_and_collapse(parser):
    res = parser.interpret("expand the project tree")
    assert res is not None
    assert res.actions[0].action_type == ActionType.EXPAND
    assert res.actions[0].target == "project tree"

    res = parser.interpret("collapse project tree")
    assert res is not None
    assert res.actions[0].action_type == ActionType.COLLAPSE
    assert res.actions[0].target == "project tree"


def test_conversational_commands(parser):
    res = parser.interpret("ok now close WhatsApp")
    assert res is not None
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].target == "whatsapp"
    assert res.actions[0].window_action == WindowActionType.CLOSE

    res = parser.interpret("hey please open Chrome")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[0].target == "chrome"

    res = parser.interpret("bro just type hello world")
    assert res is not None
    assert res.actions[0].action_type == ActionType.TYPE
    assert res.actions[0].text == "hello world"

    res = parser.interpret("now click the search button")
    assert res is not None
    assert res.actions[0].action_type == ActionType.CLICK
    assert res.actions[0].target == "search"


def test_click_profile_and_scroll(parser):
    res = parser.interpret("click on the fff profile")
    assert res is not None
    assert res.actions[0].action_type == ActionType.CLICK
    assert res.actions[0].target == "fff"

    res = parser.interpret("scroll down")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SCROLL
    assert res.actions[0].scroll_direction == "down"

    res = parser.interpret("mouse scroll up a bit")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SCROLL
    assert res.actions[0].scroll_direction == "up"
    assert res.actions[0].scroll_amount == 2

    res = parser.interpret("scroll the page")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SCROLL


def test_fundamental_pc_controls(parser):
    # Audio & Media
    res = parser.interpret("volume up")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "volume_up"

    res = parser.interpret("turn the volume down")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "volume_down"

    res = parser.interpret("mute")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "mute"

    res = parser.interpret("play music")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "play_pause"

    res = parser.interpret("next song")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "next_track"

    # Lock & Power
    res = parser.interpret("lock computer")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "lock_pc"

    res = parser.interpret("sleep pc")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "sleep_pc"

    # Shell & Desktop
    res = parser.interpret("show desktop")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "show_desktop"

    res = parser.interpret("open task manager")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "task_manager"

    res = parser.interpret("open file explorer")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "file_explorer"

    res = parser.interpret("take screenshot")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "screenshot"

    # Snapping & Desktops
    res = parser.interpret("snap window left")
    assert res is not None
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.SNAP_LEFT

    res = parser.interpret("snap right")
    assert res is not None
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.SNAP_RIGHT

    res = parser.interpret("next desktop")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "next_desktop"

    # Browser Navigation
    res = parser.interpret("go back")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "go_back"

    res = parser.interpret("zoom in")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "zoom_in"

    # Editing & Mouse
    res = parser.interpret("clear text")
    assert res is not None
    assert len(res.actions) == 2
    assert res.actions[0].action_type == ActionType.SHORTCUT
    assert res.actions[1].action_type == ActionType.KEY_PRESS

    res = parser.interpret("move mouse center")
    assert res is not None
    assert res.actions[0].action_type == ActionType.MOVE_MOUSE
    assert res.actions[0].target == "center"

    res = parser.interpret("hover on submit")
    assert res is not None
    assert res.actions[0].action_type == ActionType.HOVER
    assert res.actions[0].target == "submit"


def test_compound_commands(parser):
    # 1. The exact command reported by the user
    res = parser.interpret("open chrome and open a new tab")
    assert res is not None
    assert len(res.actions) == 2
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[0].target == "chrome"
    assert res.actions[1].action_type == ActionType.SHORTCUT
    assert res.actions[1].keys == "ctrl+t"

    # 2. Alternative conjunction phrasings
    res = parser.interpret("open chrome then new tab")
    assert res is not None
    assert len(res.actions) == 2
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[1].action_type == ActionType.SHORTCUT

    res = parser.interpret("open chrome, and a new tab")
    assert res is not None
    assert len(res.actions) == 2
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[1].action_type == ActionType.SHORTCUT

    # 3. Audio & Media compound command
    res = parser.interpret("volume up and next song")
    assert res is not None
    assert len(res.actions) == 2
    assert res.actions[0].system_action == "volume_up"
    assert res.actions[1].system_action == "next_track"

    # 4. Text typing + keyboard enter
    res = parser.interpret("type hello world and press enter")
    assert res is not None
    assert len(res.actions) == 2
    assert res.actions[0].action_type == ActionType.TYPE
    assert res.actions[0].text == "hello world"
    assert res.actions[1].action_type == ActionType.KEY_PRESS
    assert res.actions[1].keys == "enter"

    # 5. Type text with conjunction preserved when not followed by command
    res = parser.interpret("type apples and oranges")
    assert res is not None
    assert len(res.actions) == 1
    assert res.actions[0].action_type == ActionType.TYPE
    assert res.actions[0].text == "apples and oranges"

    # 6. Shortcut chaining
    res = parser.interpret("copy and paste")
    assert res is not None
    assert len(res.actions) == 2
    assert res.actions[0].keys == "ctrl+c"
    assert res.actions[1].keys == "ctrl+v"

    # 7. Window control + app launch
    res = parser.interpret("minimize this and open notepad")
    assert res is not None
    assert len(res.actions) == 2
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.MINIMIZE
    assert res.actions[1].action_type == ActionType.LAUNCH_APP
    assert res.actions[1].target == "notepad"


def test_dictation_mode_toggles(parser):
    res = parser.interpret("start dictation")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "start_dictation"

    res = parser.interpret("dictation mode")
    assert res is not None
    assert res.actions[0].system_action == "start_dictation"

    res = parser.interpret("stop dictation")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "stop_dictation"

    res = parser.interpret("command mode")
    assert res is not None
    assert res.actions[0].system_action == "stop_dictation"


def test_fast_web_searches(parser):
    # YouTube search
    res = parser.interpret("search youtube for lofi beats")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://www.youtube.com/results?search_query=lofi+beats" in res.actions[0].target

    res = parser.interpret("find funny cats on youtube")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://www.youtube.com/results?search_query=funny+cats" in res.actions[0].target

    # Google search
    res = parser.interpret("search google for python tutorial")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://www.google.com/search?q=python+tutorial" in res.actions[0].target

    # Generic web search
    res = parser.interpret("search the web for current weather")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://www.google.com/search?q=current+weather" in res.actions[0].target


def test_direct_typing_with_dictation(parser):
    res = parser.interpret("type how are you doing")
    assert res is not None
    assert res.actions[0].action_type == ActionType.TYPE
    assert res.actions[0].text == "how are you doing"
    assert res.actions[0].target is None

    res = parser.interpret("dictate testing one two three")
    assert res is not None
    assert res.actions[0].action_type == ActionType.TYPE
    assert res.actions[0].text == "testing one two three"
    assert res.actions[0].target is None


def test_resume_and_reset_stop(parser):
    for phrase in ("resume", "continue", "reset stop", "clear stop", "unfreeze", "enable controls"):
        res = parser.interpret(phrase)
        assert res is not None
        assert res.actions[0].action_type == ActionType.NONE
        assert res.actions[0].target == "reset_stop"


def test_expanded_platform_searches(parser):
    res = parser.interpret("search github for vyoma")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://github.com/search?q=vyoma" in res.actions[0].target

    res = parser.interpret("search wikipedia for quantum computing")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://en.wikipedia.org/wiki/Special:Search?search=quantum+computing" in res.actions[0].target

    res = parser.interpret("search reddit for technology")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://www.reddit.com/search/?q=technology" in res.actions[0].target

    res = parser.interpret("search amazon for wireless mouse")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://www.amazon.com/s?k=wireless+mouse" in res.actions[0].target

    res = parser.interpret("search twitter for artificial intelligence")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://twitter.com/search?q=artificial+intelligence" in res.actions[0].target

    res = parser.interpret("search maps for coffee shop")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert "https://www.google.com/maps/search/coffee+shop" in res.actions[0].target


def test_direct_url_navigation(parser):
    res = parser.interpret("go to reddit.com")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[0].target == "https://reddit.com"

    res = parser.interpret("open github.com")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[0].target == "https://github.com"


def test_media_commands_expanded(parser):
    res = parser.interpret("rewind 10 seconds")
    assert res is not None
    assert res.actions[0].system_action == "rewind"

    res = parser.interpret("fast forward")
    assert res is not None
    assert res.actions[0].system_action == "forward"

    res = parser.interpret("speed up")
    assert res is not None
    assert res.actions[0].system_action == "speed_up"

    res = parser.interpret("slow down")
    assert res is not None
    assert res.actions[0].system_action == "slow_down"

    res = parser.interpret("toggle captions")
    assert res is not None
    assert res.actions[0].system_action == "captions"

    res = parser.interpret("theater mode")
    assert res is not None
    assert res.actions[0].system_action == "theater_mode"

    res = parser.interpret("fullscreen video")
    assert res is not None
    assert res.actions[0].system_action == "fullscreen_media"

    res = parser.interpret("mute video")
    assert res is not None
    assert res.actions[0].system_action == "mute_media"

    res = parser.interpret("max volume")
    assert res is not None
    assert res.actions[0].system_action == "volume_up"
    assert res.actions[0].scroll_amount == 25


def test_corner_snapping_and_monitors(parser):
    res = parser.interpret("snap top left")
    assert res is not None
    assert res.actions[0].system_action == "snap_top_left"

    res = parser.interpret("snap top right")
    assert res is not None
    assert res.actions[0].system_action == "snap_top_right"

    res = parser.interpret("snap bottom left")
    assert res is not None
    assert res.actions[0].system_action == "snap_bottom_left"

    res = parser.interpret("snap bottom right")
    assert res is not None
    assert res.actions[0].system_action == "snap_bottom_right"

    res = parser.interpret("next monitor")
    assert res is not None
    assert res.actions[0].system_action == "next_monitor"

    res = parser.interpret("move to next screen")
    assert res is not None
    assert res.actions[0].system_action == "next_monitor"

    res = parser.interpret("previous monitor")
    assert res is not None
    assert res.actions[0].system_action == "prev_monitor"

    res = parser.interpret("minimize other windows")
    assert res is not None
    assert res.actions[0].system_action == "minimize_others"


def test_browser_advanced_commands(parser):
    res = parser.interpret("duplicate tab")
    assert res is not None
    assert res.actions[0].system_action == "duplicate_tab"

    res = parser.interpret("new incognito window")
    assert res is not None
    assert res.actions[0].system_action == "incognito_window"

    res = parser.interpret("hard refresh")
    assert res is not None
    assert res.actions[0].system_action == "hard_refresh"

    res = parser.interpret("view page source")
    assert res is not None
    assert res.actions[0].system_action == "view_source"

    res = parser.interpret("toggle bookmarks bar")
    assert res is not None
    assert res.actions[0].system_action == "toggle_bookmarks_bar"

    res = parser.interpret("switch to tab 2")
    assert res is not None
    assert res.actions[0].system_action == "tab_2"

    res = parser.interpret("tab 5")
    assert res is not None
    assert res.actions[0].system_action == "tab_5"


def test_text_cursor_advanced_commands(parser):
    res = parser.interpret("delete line")
    assert res is not None
    assert res.actions[0].system_action == "delete_line"

    res = parser.interpret("delete word")
    assert res is not None
    assert res.actions[0].system_action == "delete_word"

    res = parser.interpret("select line")
    assert res is not None
    assert res.actions[0].system_action == "select_line"

    res = parser.interpret("line start")
    assert res is not None
    assert res.actions[0].system_action == "line_start"

    res = parser.interpret("line end")
    assert res is not None
    assert res.actions[0].system_action == "line_end"

    res = parser.interpret("top of page")
    assert res is not None
    assert res.actions[0].system_action == "page_top"

    res = parser.interpret("bottom of page")
    assert res is not None
    assert res.actions[0].system_action == "page_bottom"


def test_profile_and_selection_commands(parser):
    # Test conversational trailing "ok" stripping + selection routing
    res1 = parser.interpret("open a profile from the selection ok")
    assert res1 is not None
    assert res1.actions[0].action_type == ActionType.CLICK
    assert res1.actions[0].target == "profile"

    # Test speech typo "prfile" normalization + click routing
    res2 = parser.interpret("select the ff prfile")
    assert res2 is not None
    assert res2.actions[0].action_type == ActionType.CLICK
    assert res2.actions[0].target == "ff"

    # Test named profile click
    res3 = parser.interpret("open profile sonu")
    assert res3 is not None
    assert res3.actions[0].action_type == ActionType.CLICK
    assert res3.actions[0].target == "sonu"

    # Test pick / choose aliases
    res4 = parser.interpret("pick the first profile")
    assert res4 is not None
    assert res4.actions[0].action_type == ActionType.CLICK
    assert res4.actions[0].target == "first"


def test_new_tab_and_web_searches(parser):
    # Test "now search youtube"
    res1 = parser.interpret("now search youtube")
    assert res1 is not None
    assert res1.actions[0].action_type == ActionType.LAUNCH_APP
    assert "youtube.com" in res1.actions[0].target

    # Test "search youtube lofi beats"
    res2 = parser.interpret("search youtube lofi beats")
    assert res2 is not None
    assert res2.actions[0].action_type == ActionType.LAUNCH_APP
    assert "lofi+beats" in res2.actions[0].target

    # Test "in the new tab open youtube"
    res3 = parser.interpret("in the new tab open youtube")
    assert res3 is not None
    assert len(res3.actions) == 3
    assert res3.actions[0].action_type == ActionType.SHORTCUT
    assert res3.actions[0].keys == "ctrl+t"
    assert res3.actions[1].action_type == ActionType.TYPE
    assert "youtube.com" in res3.actions[1].text
    assert res3.actions[2].action_type == ActionType.KEY_PRESS
    assert res3.actions[2].keys == "enter"

    # Test "open chatgpt in a new tab"
    res4 = parser.interpret("open chatgpt in a new tab")
    assert res4 is not None
    assert len(res4.actions) == 3
    assert res4.actions[0].keys == "ctrl+t"
    assert "chatgpt.com" in res4.actions[1].text

    # Test "go to youtube"
    res5 = parser.interpret("go to youtube")
    assert res5 is not None
    assert res5.actions[0].action_type == ActionType.LAUNCH_APP
    assert "youtube.com" in res5.actions[0].target


def test_send_and_inspector_commands(parser):
    # Test "now send it"
    res1 = parser.interpret("now send it")
    assert res1 is not None
    assert res1.actions[0].action_type == ActionType.KEY_PRESS
    assert res1.actions[0].keys == "enter"

    # Test "send"
    res2 = parser.interpret("send")
    assert res2 is not None
    assert res2.actions[0].action_type == ActionType.KEY_PRESS
    assert res2.actions[0].keys == "enter"

    # Test "send message"
    res3 = parser.interpret("send message")
    assert res3 is not None
    assert res3.actions[0].action_type == ActionType.KEY_PRESS
    assert res3.actions[0].keys == "enter"

    # Test "submit"
    res4 = parser.interpret("submit")
    assert res4 is not None
    assert res4.actions[0].action_type == ActionType.KEY_PRESS
    assert res4.actions[0].keys == "enter"

    # Test "ctrl enter"
    res5 = parser.interpret("ctrl enter")
    assert res5 is not None
    assert res5.actions[0].action_type == ActionType.SHORTCUT
    assert res5.actions[0].keys == "ctrl+enter"

    # Test "open element inspector"
    res6 = parser.interpret("open element inspector")
    assert res6 is not None
    assert res6.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res6.actions[0].system_action == "open_inspector"

    # Test "inspect elements"
    res7 = parser.interpret("inspect elements")
    assert res7 is not None
    assert res7.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res7.actions[0].system_action == "open_inspector"


def test_macro_recording_commands(parser):
    # Test "Handless, watch what I do"
    res1 = parser.interpret("Handless, watch what I do")
    assert res1 is not None
    assert res1.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res1.actions[0].system_action == "start_macro_recording"

    # Test "watch me"
    res2 = parser.interpret("watch me")
    assert res2 is not None
    assert res2.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res2.actions[0].system_action == "start_macro_recording"

    # Test "Call this 'Morning Report Workflow'"
    res3 = parser.interpret("Call this 'Morning Report Workflow'")
    assert res3 is not None
    assert res3.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res3.actions[0].system_action == "save_macro"
    assert res3.actions[0].target == "Morning Report Workflow"

    # Test "save workflow as Daily Standup"
    res4 = parser.interpret("save workflow as Daily Standup")
    assert res4 is not None
    assert res4.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res4.actions[0].system_action == "save_macro"
    assert res4.actions[0].target == "Daily Standup"

    # Test "discard workflow"
    res5 = parser.interpret("discard workflow")
    assert res5 is not None
    assert res5.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res5.actions[0].system_action == "stop_macro_recording"

    # Test "stop macro recording"
    res6 = parser.interpret("stop macro recording")
    assert res6 is not None
    assert res6.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res6.actions[0].system_action == "stop_macro_recording"


def test_screen_lens_commands(parser):
    # Test "screen lens"
    res1 = parser.interpret("screen lens")
    assert res1 is not None
    assert res1.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res1.actions[0].system_action == "open_screen_lens"

    # Test "inspect screen"
    res2 = parser.interpret("inspect screen")
    assert res2 is not None
    assert res2.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res2.actions[0].system_action == "open_screen_lens"

    # Test "what's on my screen"
    res3 = parser.interpret("what's on my screen")
    assert res3 is not None
    assert res3.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res3.actions[0].system_action == "open_screen_lens"


def test_whatsapp_compound_messaging_commands(parser):
    # 1. "select vaishu and type hi to her" -> types "hi", does NOT send (waits for user)
    res1 = parser.interpret("Okay, now select Vaishu and type hi to her")
    assert res1 is not None
    assert len(res1.actions) == 3
    assert res1.actions[0].action_type == ActionType.CLICK
    assert res1.actions[0].target == "vaishu"
    assert res1.actions[0].target_type == "contact"
    assert res1.actions[1].action_type == ActionType.CLICK
    assert res1.actions[1].target == "Type a message"
    assert res1.actions[2].action_type == ActionType.TYPE
    assert res1.actions[2].text == "hi"
    assert res1.actions[2].target == "Type a message"

    # 2. "type vaishu and send her hi" -> types "hi" and sends (Enter)
    res2 = parser.interpret("type vaishu and send her hi")
    assert res2 is not None
    assert len(res2.actions) == 4
    assert res2.actions[0].action_type == ActionType.CLICK
    assert res2.actions[0].target == "vaishu"
    assert res2.actions[1].target == "Type a message"
    assert res2.actions[2].action_type == ActionType.TYPE
    assert res2.actions[2].text == "hi"
    assert res2.actions[3].action_type == ActionType.KEY_PRESS
    assert res2.actions[3].keys == "enter"

    # 3. "select vaishu and type hi to her and wait for me to send" -> does NOT send
    res3 = parser.interpret("select vaishu and type hi to her and wait for me to send")
    assert res3 is not None
    assert len(res3.actions) == 3
    assert res3.actions[2].text == "hi"

    # 4. "send hello to vaishu" -> sends hello
    res4 = parser.interpret("send hello to vaishu")
    assert res4 is not None
    assert len(res4.actions) == 4
    assert res4.actions[0].target == "vaishu"
    assert res4.actions[2].text == "hello"
    assert res4.actions[3].keys == "enter"







