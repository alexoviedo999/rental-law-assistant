---
title: Rental Law Assistant
emoji: 🏠
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.50.0
app_file: app.py
pinned: false
license: mit
short_description: Jev judgments. Draft shown only on success.
---

# Rental law assistant

A tenant question goes in. One sentence comes out.

Python walks the path and writes the stamp. Jev decides scope, whether one fact is missing, whether the policy passages are sufficient, and the three audit scores. OpenRouter writes the draft and the passage vectors. The draft is published only when the stamp is `success`. Prompt injection is refused.

The first question embeds the two PDFs, so it takes longer than the ones after it. If the assistant asks for one fact, paste that answer into Clarification and submit the same question again.

Space secrets, set in Settings and not stored in this repo:

- `TYPESAFE_API_KEY`
- `OPENROUTER_API_KEY`
