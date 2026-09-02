from lumen.agent.planner import Planner
from lumen.config import Config


class DummyClient:
    def chat(self, *args, **kwargs):
        raise AssertionError("simple plans should not call the model")


def make_planner():
    return Planner(Config(), DummyClient())


def test_open_app_simple_plan():
    plan = make_planner().plan("open Safari")

    assert plan.actions[0].tool == "open_app"
    assert plan.actions[0].args == {"app_name": "Safari"}


def test_default_web_search_simple_plan():
    plan = make_planner().plan("search for Apple Silicon MLX Whisper")

    assert plan.actions[0].tool == "web_search"
    assert plan.actions[0].args["query"] == "Apple Silicon MLX Whisper"
    assert plan.actions[0].args["browser"] == "Safari"


def test_browser_web_search_simple_plan():
    plan = make_planner().plan("open chrome and search for local LLM agents")

    assert plan.actions[0].tool == "web_search"
    assert plan.actions[0].args["browser"] == "Google Chrome"
    assert plan.actions[0].args["query"] == "local LLM agents"


def test_youtube_search_simple_plan():
    plan = make_planner().plan("open youtube and search mit")

    assert plan.actions[0].tool == "open_url"
    assert plan.actions[0].args["url"] == "https://www.youtube.com/results?search_query=mit"


def test_open_youtube_simple_plan_opens_url():
    plan = make_planner().plan("open youtube")

    assert plan.actions[0].tool == "open_url"
    assert plan.actions[0].args["url"] == "https://www.youtube.com"


def test_new_tab_simple_plan():
    plan = make_planner().plan("new tab")

    assert plan.actions[0].tool == "browser_new_tab"
    assert plan.actions[0].args == {"browser": "Safari", "url": ""}


def test_new_chrome_tab_with_url_simple_plan():
    plan = make_planner().plan("open new chrome tab with example.com")

    assert plan.actions[0].tool == "browser_new_tab"
    assert plan.actions[0].args == {"browser": "Google Chrome", "url": "example.com"}


def test_close_tab_simple_plan():
    plan = make_planner().plan("close tab")

    assert plan.actions[0].tool == "browser_close_tab"
    assert plan.actions[0].args == {"browser": "Safari"}


def test_next_tab_simple_plan():
    plan = make_planner().plan("next tab")

    assert plan.actions[0].tool == "browser_switch_tab"
    assert plan.actions[0].args == {"browser": "Safari", "direction": "next"}


def test_reload_tab_simple_plan():
    plan = make_planner().plan("reload tab")

    assert plan.actions[0].tool == "browser_reload_tab"
    assert plan.actions[0].args == {"browser": "Safari"}


def test_screenshot_simple_plan():
    plan = make_planner().plan("take a screenshot called approval-smoke")

    assert plan.actions[0].tool == "screenshot"
    assert plan.actions[0].args == {"filename": "approval-smoke"}
