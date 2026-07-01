"""CLI entrypoint for the modular Lumen agent."""

from __future__ import annotations

import sys

from lumen.agent.executor import Executor
from lumen.agent.planner import Planner
from lumen.config import Config
from lumen.llm.ollama_client import OllamaClient
from lumen.tools import TOOLS
from lumen.voice.recorder import VoiceDependencyError, record_wav
from lumen.voice.stt import MlxWhisperTranscriber, SpeechToTextError
from lumen.voice.tts import speak


def main() -> int:
    config = Config()
    planner = Planner(config, OllamaClient(config.ollama_url))
    executor = Executor()

    print("Lumen v3 initialized")
    print(f"Planner: {config.planner_model}")
    print(f"Router:  {config.router_model}")
    print(f"Ollama:  {config.ollama_url}")
    print("Tools:   " + ", ".join(sorted(TOOLS)))
    print("Type 'quit' or 'exit' to stop.")
    print("Type '/voice 5' to record a 5 second voice command.")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except KeyboardInterrupt:
            print("\nShutting down Lumen.")
            return 0
        except EOFError:
            print()
            return 0

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            print("Shutting down Lumen.")
            return 0

        if user_input.startswith("/voice"):
            response = handle_voice_command(user_input, planner, executor)
            if response:
                speak(response)
            continue

        process_command(user_input, planner, executor)


def process_command(user_input: str, planner: Planner, executor: Executor) -> str:
    plan = planner.plan(user_input)
    spoken_parts: list[str] = []
    if plan.response:
        print(f"Lumen: {plan.response}")
        spoken_parts.append(plan.response)

    observations: list[str] = []
    for action in plan.actions:
        print(f"Action: {action.tool} {action.args}")
        result = executor.execute(action)
        status = "OK" if result.ok else "ERR"
        print(f"{status}: {result.observation}")
        planner.observe(action, result)
        observations.append(result.observation)

    final = planner.final_response(user_input, observations)
    if final and final != (plan.response or ""):
        print(f"Lumen: {final}")
        spoken_parts.append(final)

    return " ".join(spoken_parts).strip()


def handle_voice_command(command: str, planner: Planner, executor: Executor) -> str:
    seconds = _parse_voice_seconds(command)
    try:
        audio_path = record_wav(seconds)
        transcription = MlxWhisperTranscriber().transcribe(audio_path)
    except (ValueError, VoiceDependencyError, SpeechToTextError) as exc:
        message = str(exc)
        print(f"Voice error: {message}")
        return message

    print(f"You said: {transcription.text}")
    return process_command(transcription.text, planner, executor)


def _parse_voice_seconds(command: str) -> float:
    parts = command.split(maxsplit=1)
    if len(parts) == 1:
        return 5.0
    try:
        seconds = float(parts[1])
    except ValueError as exc:
        raise ValueError("Usage: /voice [seconds]") from exc
    return max(1.0, min(seconds, 30.0))


if __name__ == "__main__":
    sys.exit(main())
