from lumen.ui.state import ChatBridge, PresenceState


def test_presence_state_updates_snapshot():
    presence = PresenceState()

    presence.update(
        "speaking",
        "Hello from Lumen.",
        detail="Testing the presence layer.",
        transcript="open Safari",
    )

    snapshot = presence.as_dict()
    assert snapshot["state"] == "speaking"
    assert snapshot["message"] == "Hello from Lumen."
    assert snapshot["detail"] == "Testing the presence layer."
    assert snapshot["transcript"] == "open Safari"
    assert snapshot["updated_at"]


def test_chat_bridge_queues_user_messages():
    bridge = ChatBridge()

    bridge.post_user_message("open youtube and search mit")
    bridge.append_lumen_message("Searching YouTube for mit.")

    assert bridge.get_next(timeout=0.01) == "open youtube and search mit"
    snapshot = bridge.snapshot()
    assert snapshot["messages"][-1]["text"] == "Searching YouTube for mit."
