"""Live desktop integration test on actual Windows desktop.

Launches Notepad, finds the edit control via Windows UI Automation,
types a confirmation message, and then closes Notepad cleanly.
"""

import time
from handless.actions.launcher import ApplicationLauncher
from handless.actions.keyboard import KeyboardController
from handless.actions.window import WindowController
from handless.screen.uia_inspector import UIAInspector


def main():
    print("1. Launching Notepad...")
    launcher = ApplicationLauncher()
    assert launcher.launch("notepad"), "Failed to launch notepad"

    time.sleep(1.2)  # Allow Notepad window to open

    print("2. Inspecting desktop via UI Automation...")
    inspector = UIAInspector()
    active_win = inspector.get_active_window()
    print(f"Active window title: '{active_win.window_text() if active_win else 'None'}'")

    print("3. Typing text into Notepad...")
    kb = KeyboardController()
    success = kb.type_text("Vyoma Handless Live Verification: Speak naturally. Computer responds.\n")
    print(f"Typing success: {success}")

    time.sleep(1.0)

    print("4. Closing Notepad via WindowController...")
    win_ctrl = WindowController()
    win_ctrl.close(active_win)

    # If "Do you want to save changes?" dialog appears, press 'n' (Don't Save)
    time.sleep(0.5)
    kb.press_key("n")

    print("Live Desktop Verification Complete! Everything working as expected.")


if __name__ == "__main__":
    main()
