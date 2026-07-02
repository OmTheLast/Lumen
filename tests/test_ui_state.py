from lumen.ui.state import PresenceState


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

