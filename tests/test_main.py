from lumen.main import _can_ack_without_llm, _should_run_without_stdin


def test_quick_tools_can_ack_without_llm():
    assert _can_ack_without_llm(["open_app"])
    assert _can_ack_without_llm(["web_search", "open_url"])
    assert _can_ack_without_llm(["browser_new_tab", "browser_switch_tab"])


def test_risky_or_unknown_tools_do_not_ack_without_llm():
    assert not _can_ack_without_llm([])
    assert not _can_ack_without_llm(["read_file"])
    assert not _can_ack_without_llm(["run_shell"])


def test_app_mode_disables_terminal_input():
    assert _should_run_without_stdin(["--app"])
    assert _should_run_without_stdin(["--no-stdin"])
    assert not _should_run_without_stdin([])
