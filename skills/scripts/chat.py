# skills/scripts/chat.py
#!/usr/bin/env python3
"""Skill bridge: chat — get persona context for a user message."""
import argparse
import json
import sys

import httpx

from server_utils import SERVER_URL, ensure_server_running


def main():
    parser = argparse.ArgumentParser(description="girlfriend-agent chat")
    parser.add_argument("message", help="User message")
    parser.add_argument("--level", type=int, default=1, choices=[1, 2, 3])
    parser.add_argument("--type", default="daily_chat",
                        choices=["daily_chat", "deep_conversation",
                                 "collaborative_task", "emotion_companion", "light_chat"])
    args = parser.parse_args()

    if not ensure_server_running():
        sys.exit(1)

    resp = httpx.post(f"{SERVER_URL}/chat", json={
        "user_message": args.message,
        "level": args.level,
        "interaction_type": args.type,
    }, timeout=30)

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print("=== 人格Prompt ===")
    print(data["persona_prompt"])
    print()
    if data["memory_fragments"]:
        print("=== 相关记忆 ===")
        for frag in data["memory_fragments"]:
            print(f"  - {frag}")
        print()
    print("=== 关系状态 ===")
    print(data["relationship_summary"])
    print()
    if data["de_ai_instructions"]:
        print("=== 去AI味指令 ===")
        print(data["de_ai_instructions"])


if __name__ == "__main__":
    main()