---
name: gf-persona
description: "Use when the user wants to view, update, or apply a template to the girlfriend character's persona configuration — personality dimensions, speech style, likes/dislikes."
---

# Persona Management

Manage the girlfriend character's personality configuration.

## When to Use

- User wants to see current personality settings
- User wants to adjust a specific personality trait
- User wants to apply a preset persona template (tsundere, gentle, etc.)
- User wants to switch character style

## Persona Operations

| Tool | Purpose |
|------|---------|
| persona_get_girlfriend | View current persona configuration |
| persona_update_girlfriend | Update a specific field |
| persona_apply_template_girlfriend | Apply a preset template |

## Viewing Persona

`persona_get_girlfriend` returns the full persona configuration including:
- **personality_base** — 7 dimensions (warmth/rationality/independence/humor/patience/curiosity/expressiveness)
- **speech_style** — character's speaking patterns
- **likes** / **dislikes** — preferences list

## Updating a Field

`persona_update_girlfriend` parameters:
- `field` (required) — field path using dot notation:
  - `personality_base.warmth` — adjust warmth (0.0-1.0)
  - `personality_base.humor` — adjust humor level
  - `nickname` — change the nickname
  - `speech_style.tone` — change speech tone
  - Any valid persona field path
- `value` (required) — new value for the field

The tool pre-validates before mutation — invalid values are rejected without corrupting state.

## Template Presets

`persona_apply_template_girlfriend` applies a complete personality preset:
- `default` — balanced, warm baseline
- `tsundere` — outwardly cold, inwardly caring
- `gentle` — soft, nurturing, patient
- `lively` — energetic, playful, humorous
- `intellectual` — thoughtful, rational, curious
- `little_sister` — playful, dependent, affectionate
- `custom_skeleton` — blank template for full customization

Applying a template resets personality dimensions to preset values and commits to git.