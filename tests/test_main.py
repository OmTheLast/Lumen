from lumen.main import _can_ack_without_llm


def test_quick_tools_can_ack_without_llm():
    assert _can_ack_without_llm(["open_app"])
    assert _can_ack_without_llm(["web_search", "open_url"])


def test_risky_or_unknown_tools_do_not_ack_without_llm():
    assert not _can_ack_without_llm([])
    assert not _can_ack_without_llm(["read_file"])
    assert not _can_ack_without_llm(["run_shell"])
