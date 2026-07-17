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
