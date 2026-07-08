"""CLI entrypoint for the modular Lumen agent."""

from __future__ import annotations

import sys
from typing import NamedTuple

from lumen.agent.executor import Executor
from lumen.agent.planner import Planner
from lumen.config import Config
from lumen.llm.ollama_client import OllamaClient
from lumen.tools import TOOLS
from lumen.ui.overlay import start_overlay
from lumen.ui.overlay import OverlayHandle
from lumen.ui.server import PresenceServer
from lumen.ui.state import PresenceState
from lumen.voice.recorder import VoiceDependencyError, record_command_wav, record_wav
from lumen.voice.stt import MlxWhisperTranscriber, SpeechToTextError
from lumen.voice.tts import speak


def main() -> int:
    config = Config()
    planner = Planner(config, OllamaClient(config.ollama_url))
    executor = Executor()
    presence = PresenceState()
    ui_server = _start_presence_ui(config, presence)
    overlay = _start_overlay(config, ui_server)

    print("Lumen v3 initialized")
    print(f"Planner: {config.planner_model}")
    print(f"Router:  {config.router_model}")
    print(f"Ollama:  {config.ollama_url}")
    if ui_server is not None:
        print(f"UI:      {ui_server.url}")
    if overlay is not None:
        print("Overlay: bottom-right native orb enabled")
    print("Tools:   " + ", ".join(sorted(TOOLS)))
    print("Type 'quit' or 'exit' to stop.")
    print("Type '/voice' for auto-stop voice, or '/voice 5' for fixed 5 seconds.")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except KeyboardInterrupt:
            print("\nShutting down Lumen.")
            presence.update("idle", "Lumen is shutting down.", detail="Terminal interrupted.")
            _shutdown_presence(ui_server, overlay)
            return 0
        except EOFError:
            presence.update("idle", "Lumen is shutting down.", detail="Terminal input closed.")
            print()
            _shutdown_presence(ui_server, overlay)
            return 0

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            print("Shutting down Lumen.")
            presence.update("idle", "Lumen is shutting down.", detail="Goodbye.")
            _shutdown_presence(ui_server, overlay)
            return 0

        if user_input.startswith("/voice"):
            response = handle_voice_command(user_input, planner, executor, presence)
            if response:
                _speak_with_presence(response, presence)
            continue

        process_command(user_input, planner, executor, presence)


def process_command(
    user_input: str,
    planner: Planner,
    executor: Executor,
    presence: PresenceState | None = None,
) -> str:
    _presence_update(
        presence,
        "thinking",
        "Thinking through the request.",
        detail=user_input,
        transcript=user_input,
    )
    plan = planner.plan(user_input)
    spoken_parts: list[str] = []
    if plan.response:
        print(f"Lumen: {plan.response}")
        _presence_update(presence, "speaking", plan.response, detail="Drafting a response.")
        spoken_parts.append(plan.response)

    observations: list[str] = []
    tools_run: list[str] = []
    for action in plan.actions:
        print(f"Action: {action.tool} {action.args}")
        tools_run.append(action.tool)
        _presence_update(
            presence,
            "acting",
            f"Using {action.tool}.",
            detail=action.reason or "Running a tool.",
        )
        result = executor.execute(action)
        status = "OK" if result.ok else "ERR"
        print(f"{status}: {result.observation}")
        _presence_update(
            presence,
            "thinking" if result.ok else "error",
            result.observation,
            detail="Tool observation received.",
        )
        planner.observe(action, result)
        observations.append(result.observation)

    if observations:
        _presence_update(presence, "thinking", "Reviewing the result.", detail=observations[-1])

    if observations and _can_ack_without_llm(tools_run):
        final = observations[-1]
    else:
        final = planner.final_response(user_input, observations)
    if final and final != (plan.response or ""):
        print(f"Lumen: {final}")
        _presence_update(presence, "speaking", final, detail="Responding.")
        spoken_parts.append(final)

    spoken = " ".join(spoken_parts).strip()
    _presence_update(
        presence,
        "idle",
        spoken or "Done.",
        detail="Waiting for the next command.",
    )
    return spoken


def handle_voice_command(
    command: str,
    planner: Planner,
    executor: Executor,
    presence: PresenceState | None = None,
) -> str:
    voice_mode = _parse_voice_command(command)
    try:
        detail = (
            f"Recording {voice_mode.seconds:g} seconds of audio."
            if voice_mode.seconds is not None
            else f"Listening until silence, up to {voice_mode.max_seconds:g} seconds."
        )
        _presence_update(
            presence,
            "listening",
            "Listening.",
            detail=detail,
        )
        if voice_mode.seconds is None:
            audio_path = record_command_wav(
                max_seconds=voice_mode.max_seconds,
                silence_seconds=voice_mode.silence_seconds,
                silence_threshold=voice_mode.silence_threshold,
            )
        else:
            audio_path = record_wav(voice_mode.seconds)
        _presence_update(
            presence,
            "thinking",
            "Transcribing your voice.",
            detail="Running local speech-to-text.",
        )
        transcription = MlxWhisperTranscriber(model=voice_mode.stt_model).transcribe(audio_path)
    except (ValueError, VoiceDependencyError, SpeechToTextError) as exc:
        message = str(exc)
        print(f"Voice error: {message}")
        _presence_update(presence, "error", "Voice command failed.", detail=message)
        return message

    print(f"You said: {transcription.text}")
    _presence_update(
        presence,
        "thinking",
        "Heard you.",
        detail=transcription.text,
        transcript=transcription.text,
    )
    return process_command(transcription.text, planner, executor, presence)


class VoiceMode(NamedTuple):
    seconds: float | None
    max_seconds: float
    silence_seconds: float
    silence_threshold: float
    stt_model: str


def _start_presence_ui(config: Config, presence: PresenceState) -> PresenceServer | None:
    if not config.ui_enabled:
        return None

    server = PresenceServer(presence, host=config.ui_host, port=config.ui_port)
    try:
        server.start(open_browser=config.ui_open_browser)
    except RuntimeError as exc:
        print(f"UI unavailable: {exc}")
        return None
    return server


def _start_overlay(config: Config, ui_server: PresenceServer | None) -> OverlayHandle | None:
    if not config.overlay_enabled or ui_server is None:
        return None
    return start_overlay(state_url=f"{ui_server.url}/state", size=config.overlay_size)


def _shutdown_presence(ui_server: PresenceServer | None, overlay: OverlayHandle | None) -> None:
    if overlay is not None:
        overlay.process.terminate()
        try:
            overlay.process.wait(timeout=1)
        except Exception:
            overlay.process.kill()
    if ui_server is not None:
        ui_server.stop()


def _presence_update(
    presence: PresenceState | None,
    state: str,
    message: str,
    *,
    detail: str = "",
    transcript: str | None = None,
) -> None:
    if presence is not None:
        presence.update(state, message, detail=detail, transcript=transcript)


def _speak_with_presence(text: str, presence: PresenceState | None) -> None:
    _presence_update(presence, "speaking", text, detail="Speaking out loud.")
    speak(text)
    _presence_update(presence, "idle", "Done speaking.", detail="Waiting for the next command.")


def _can_ack_without_llm(tool_names: list[str]) -> bool:
    if not tool_names:
        return False
    quick_ack_tools = {"open_app", "open_url", "web_search", "screenshot"}
    return all(name in quick_ack_tools for name in tool_names)


def _parse_voice_command(command: str, config: Config | None = None) -> VoiceMode:
    config = config or Config()
    parts = command.split(maxsplit=1)
    if len(parts) == 1:
        return VoiceMode(
            None,
            config.voice_auto_max_seconds,
            config.voice_silence_seconds,
            config.voice_silence_threshold,
            config.voice_stt_model,
        )
    if parts[1].strip().lower() in {"auto", "vad"}:
        return VoiceMode(
            None,
            config.voice_auto_max_seconds,
            config.voice_silence_seconds,
            config.voice_silence_threshold,
            config.voice_stt_model,
        )
    try:
        seconds = float(parts[1])
    except ValueError as exc:
        raise ValueError("Usage: /voice [seconds|auto]") from exc
    return VoiceMode(
        max(1.0, min(seconds, 30.0)),
        config.voice_auto_max_seconds,
        config.voice_silence_seconds,
        config.voice_silence_threshold,
        config.voice_stt_model,
    )


def _parse_voice_seconds(command: str) -> float:
    """Backward-compatible helper for tests and callers using fixed voice mode."""
    mode = _parse_voice_command(command)
    return 5.0 if mode.seconds is None else mode.seconds


if __name__ == "__main__":
    sys.exit(main())
