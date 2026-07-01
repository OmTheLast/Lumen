#!/usr/bin/env python3
"""
Lumen Phase 2: Core Daemon + Tool Layer
- Persistent terminal loop
- Connects to local Ollama instance
- Uses qwen3:latest as the default orchestrator
- Maintains in-memory conversation history (capped to prevent context overflow)
- ReAct-style tool execution loop with safety prompts
- Designed for easy layer extension (tools, routing, memory, voice)
"""

import requests
import sys
import os
import subprocess
import re

# ─── Configuration ───────────────────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = "qwen3:latest"
SYSTEM_PROMPT = (
    "You are Lumen, a persistent ambient AI assistant. "
    "You are concise, precise, and proactive. "
    "You handle tedium, automate workflows, and stay in control. "
    "You only speak when necessary, and you always explain your reasoning if you take action.\n\n"
    "REACT EXECUTION PROTOCOL:\n"
    "1. If your response requires a system action, output exactly one tool call in this format:\n"
    "   TOOL: <tool_name> | INPUT: <arguments>\n"
    "2. Available tools: run_shell, open_app, screenshot, read_file, write_file\n"
    "3. After a tool outputs an observation, continue reasoning or respond naturally.\n"
    "4. If no tool is needed, just respond directly.\n"
    "Note: write_file expects arguments in 'path|content' format."
)
MAX_HISTORY_TURNS = 10  # <-- ADDED: Keeps context window bounded


# ─── Core Functions ──────────────────────────────────────────────────────────
def init_history():
    """Initialize conversation history with system prompt."""
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def trim_history(history: list[dict]) -> list[dict]:
    """Keep only the system prompt + last N user/assistant pairs."""
    if len(history) <= 1:
        return history
    non_system = [m for m in history if m["role"] != "system"]
    if len(non_system) > MAX_HISTORY_TURNS * 2:
        kept = non_system[-(MAX_HISTORY_TURNS * 2):]
        return [history[0]] + kept
    return history


def send_to_ollama(messages: list[dict]) -> str:
    """Send message history to Ollama and return assistant response."""
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False  # Phase 1: non-streaming for simplicity. Will add streaming in Phase 5.
    }
    try:
        response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        # Safely extract content
        msg = data.get("message", {})
        content = msg.get("content", "[No response from model]")
        return content if content else "[No response from model]"
    except requests.exceptions.ConnectionError:
        return "[Error: Ollama is not running. Start it with `ollama serve`]"
    except requests.exceptions.Timeout:
        return "[Error: Request timed out. The model may be loading or under heavy load.]"
    except Exception as e:
        return f"[Error: {e}]"


# ─── Phase 2: Tool Layer ─────────────────────────────────────────────────────
def run_shell(command: str) -> str:
    """Runs a terminal command and returns combined stdout and stderr."""
    try:
        confirm = input(f"\n🔧 Lumen: About to run: `{command}`\nConfirm? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "⛔ Execution cancelled (stdin closed)."
    if confirm != 'y':
        return "⛔ Execution cancelled by user."
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout.strip() or result.stderr.strip()
        return output if output else "✅ Command executed successfully (no output)."
    except subprocess.TimeoutExpired:
        return "⏳ Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"⚠️ Error: {e}"


def open_app(app_name: str) -> str:
    """Opens a macOS application by name using the 'open' command."""
    app_name = app_name.strip().strip('"\'')  # 👈 ADDED
    try:
        subprocess.run(["open", "-a", app_name], check=True, capture_output=True, text=True)
        return f"✅ Opened application: {app_name}"
    except subprocess.CalledProcessError as e:
        return f"⚠️ Error opening '{app_name}': {e.stderr.strip()}"
    except Exception as e:
        return f"⚠️ Error: {e}"



def screenshot(filename: str) -> str:
    """Takes a screenshot using screencapture and saves it to ~/Documents/lumen/screenshots/."""
    dir_path = os.path.expanduser("~/Documents/lumen/screenshots")
    os.makedirs(dir_path, exist_ok=True)
    save_path = os.path.join(dir_path, filename if filename.endswith('.png') else f"{filename}.png")
    try:
        subprocess.run(["screencapture", save_path], check=True, capture_output=True, text=True)
        return f"✅ Screenshot saved to: {save_path}"
    except subprocess.CalledProcessError as e:
        return f"⚠️ Error taking screenshot: {e.stderr.strip()}"
    except Exception as e:
        return f"⚠️ Error: {e}"


def read_file(path: str) -> str:
    """Reads and returns the contents of any file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"⚠️ Error: File not found: {path}"
    except PermissionError:
        return f"⚠️ Error: Permission denied: {path}"
    except Exception as e:
        return f"⚠️ Error: {e}"


def write_file(path: str, content: str) -> str:
    """Writes content to a file, creating it if it doesn't exist."""
    try:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Successfully wrote {len(content)} chars to: {path}"
    except Exception as e:
        return f"⚠️ Error: {e}"


# Tool registry mapping names to callables
TOOLS = {
    "run_shell": run_shell,
    "open_app": open_app,
    "screenshot": screenshot,
    "read_file": read_file,
    "write_file": write_file,
}


def parse_tool_calls(text: str) -> list[tuple[str, str]]:
    """Extracts tool calls from LLM response using the TOOL: <name> | INPUT: <args> format."""
    pattern = r"TOOL:\s*(\w+)\s*\|\s*INPUT:\s*(.+?)(?=\n|$)"
    return [(m[0].strip(), m[1].strip()) for m in re.findall(pattern, text, re.IGNORECASE)]


# ─── Main Loop ───────────────────────────────────────────────────────────────
def main():
    print("🤖 Lumen Phase 2 Initialized")
    print("   Model:  " + MODEL_NAME)
    print("   API:    " + OLLAMA_URL)
    print("   Tools:  " + ", ".join(TOOLS.keys()))
    print("   Type 'quit' or 'exit' to stop.\n")
    history = init_history()

    while True:
        try:
            user_input = input("👤 You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("\n👋 Shutting down Lumen.")
                break

            # Append user message to history
            history.append({"role": "user", "content": user_input})

            # Trim history to prevent context overflow
            history = trim_history(history)

            # Get initial assistant response
            current_response = send_to_ollama(history)
            print("🤖 Lumen: ", end="", flush=True)
            print(current_response)

            # ReAct-style tool execution loop
            max_iterations = 5
            iteration = 0
            while iteration < max_iterations:
                tool_calls = parse_tool_calls(current_response)
                if not tool_calls:
                    break  # No more tools to execute

                for tool_name, tool_input in tool_calls:
                    if tool_name not in TOOLS:
                        print(f"⚠️ Unknown tool: {tool_name}")
                        continue

                    try:
                        # Handle write_file's two-argument signature
                        if tool_name == "write_file":
                            parts = tool_input.split("|", 1)
                            if len(parts) == 2:
                                observation = TOOLS[tool_name](parts[0].strip(), parts[1].strip())
                            else:
                                observation = "⚠️ write_file expects 'path|content' format."
                        else:
                            observation = TOOLS[tool_name](tool_input)

                        # Append observation to history and re-prompt
                        history.append({"role": "assistant", "content": f"OBSERVATION: {observation}"})
                        current_response = send_to_ollama(history)
                        print("🤖 Lumen: ", end="", flush=True)
                        print(current_response)
                        iteration += 1

                    except Exception as e:
                        print(f"⚠️ Tool execution error: {e}")
                        history.append({"role": "assistant", "content": f"OBSERVATION: Tool error: {e}"})
                        current_response = send_to_ollama(history)
                        print("🤖 Lumen: ", end="", flush=True)
                        print(current_response)
                        iteration += 1

            # Append final response to history
            history.append({"role": "assistant", "content": current_response})

        except KeyboardInterrupt:
            print("\n👋 Interrupted. Shutting down.")
            sys.exit(0)
        except Exception as e:
            print(f"\n⚠️ Unexpected error: {e}")

       
if __name__ == "__main__":
    main()
