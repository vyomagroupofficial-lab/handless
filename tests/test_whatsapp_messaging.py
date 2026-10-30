import pytest
from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType


@pytest.fixture
def parser():
    return LocalRuleParser()


def test_select_contact_and_type_message(parser):
    """'select vaishu and type hi to her' -> Click contact, click message box, type 'hi' (do not send)."""
    res = parser.interpret("select vaishu and type hi to her")
    assert res is not None
    assert len(res.actions) == 3

    # 1. Click contact
    assert res.actions[0].action_type == ActionType.CLICK
    assert res.actions[0].target.lower() == "vaishu"
    assert res.actions[0].target_type == "contact"

    # 2. Focus message input box
    assert res.actions[1].action_type == ActionType.CLICK
    assert res.actions[1].target == "Type a message"
    assert res.actions[1].target_type == "edit"

    # 3. Type message (stripped of 'to her')
    assert res.actions[2].action_type == ActionType.TYPE
    assert res.actions[2].text == "hi"


def test_select_contact_and_send_message(parser):
    """'select vaishu and send her hi' -> Click contact, click message box, type 'hi', press enter (send)."""
    res = parser.interpret("select vaishu and send her hi")
    assert res is not None
    assert len(res.actions) == 4

    assert res.actions[0].action_type == ActionType.CLICK
    assert res.actions[0].target.lower() == "vaishu"

    assert res.actions[1].action_type == ActionType.CLICK
    assert res.actions[1].target == "Type a message"

    assert res.actions[2].action_type == ActionType.TYPE
    assert res.actions[2].text == "hi"

    # 4. Press enter to send
    assert res.actions[3].action_type == ActionType.KEY_PRESS
    assert res.actions[3].keys == "enter"


def test_type_contact_and_send_message(parser):
    """'type vaishu and send her hi' -> Click contact, click message box, type 'hi', send."""
    res = parser.interpret("type vaishu and send her hi")
    assert res is not None
    assert len(res.actions) == 4
    assert res.actions[0].target.lower() == "vaishu"
    assert res.actions[2].text == "hi"
    assert res.actions[3].action_type == ActionType.KEY_PRESS


def test_send_message_to_contact(parser):
    """'send hi to vaishu' -> Click contact, click message box, type 'hi', send."""
    res = parser.interpret("send hi to vaishu")
    assert res is not None
    assert len(res.actions) == 4
    assert res.actions[0].target.lower() == "vaishu"
    assert res.actions[2].text == "hi"
    assert res.actions[3].action_type == ActionType.KEY_PRESS


def test_type_message_to_her(parser):
    """'type hi to her' -> Focus message box, type 'hi', do not send."""
    res = parser.interpret("type hi to her")
    assert res is not None
    assert len(res.actions) == 2
    assert res.actions[0].target == "Type a message"
    assert res.actions[1].action_type == ActionType.TYPE
    assert res.actions[1].text == "hi"


def test_send_her_message(parser):
    """'send her hi' -> Focus message box, type 'hi', press enter."""
    res = parser.interpret("send her hi")
    assert res is not None
    assert len(res.actions) == 3
    assert res.actions[0].target == "Type a message"
    assert res.actions[1].action_type == ActionType.TYPE
    assert res.actions[1].text == "hi"
    assert res.actions[2].action_type == ActionType.KEY_PRESS

