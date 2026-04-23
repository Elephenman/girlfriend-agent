---
name: gf-chat
description: "Use when the user wants to chat with the girlfriend character. Processes the message through the personality engine, updates intimacy, and returns a complete persona prompt with memory context for LLM response generation."
---

# Chat with Girlfriend Character

Process a user message through the girlfriend-agent personality engine to generate a character-driven context prompt.

## When to Use

- User wants to chat with the girlfriend character
- User sends a message that should be interpreted as interaction with the character
- Need to generate persona context for character-driven response

## How to Use

Call the MCP tool **chat_girlfriend** with:

- `user_message` (required) — the user's message to the character
- `level` (optional, default 1) — injection depth:
  - 1 = basic (~600 chars, personality + speech style)
  - 2 = deep (~2500 chars, + graph memory + de-AI instructions)
  - 3 = full (~5000 chars, + all memory fragments + full context)
- `interaction_type` (optional, default "daily_chat") — affects intimacy gain rate:
  - `daily_chat` — casual everyday conversation
  - `deep_conversation` — meaningful emotional exchange
  - `collaborative_task` — working on something together
  - `emotion_companion` — comforting during difficult times
  - `light_chat` — brief playful interaction

## Response Format

The tool returns:
- **persona_prompt** — the complete personality prompt to feed into your LLM
- **memory_fragments** — relevant recalled memories
- **relationship_summary** — current relationship state summary
- **de_ai_instructions** — anti-AI-sounding instructions for natural responses

## After Receiving the Prompt

1. Use the `persona_prompt` as your system/context prompt
2. Generate a character-driven response that follows the personality, speech style, and de-AI instructions
3. Reference relevant memory fragments naturally (don't just list them)
4. Match the relationship level's expected behavior patterns

## Interaction Type Guide

Choose `interaction_type` based on message content:
- Greetings, small talk → `daily_chat`
- Deep feelings, life discussion → `deep_conversation`
- Code help, task collaboration → `collaborative_task`
- Sadness, stress, comfort needed → `emotion_companion`
- Quick joke, brief reply → `light_chat`