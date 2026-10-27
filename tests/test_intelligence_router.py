import pytest
from handless.intelligence.router import IntentRouter
from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType


def test_intent_router_local_tier():
    router = IntentRouter()
    res = router.interpret("Open Chrome")
    assert res is not None
    assert res.source == "local_rule"
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[0].target == "chrome"


def test_intent_router_click():
    router = IntentRouter()
    res = router.interpret("Click the search button")
    assert res is not None
    assert res.source == "local_rule"
    assert res.actions[0].action_type == ActionType.CLICK
    assert res.actions[0].target == "search"
