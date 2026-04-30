# Trialogue

A local desktop tool for asking questions to three frontier LLMs at once — one proposes an answer, one critiques it, one synthesizes the final result. Built for the kind of question where a single model's answer isn't quite enough.

## What it does

Each question runs through three roles in sequence:

1. **Proposer** drafts the initial answer
2. **Critic** independently establishes what a correct answer needs, then reviews against those criteria with severity and confidence ratings
3. **Judge** synthesizes both into a final answer, leading with the answer itself

You watch all three happen live, with each model's output streaming into its own panel. Token usage is shown per-role and total. If any role fails or is stopped, you can retry just that role without re-running the earlier ones.

## What's new

- **Calibrated critic**: independently lists correctness criteria before reviewing, reducing manufactured critiques
- **Judge leads with the answer**: final answer first, then "what changed" and "remaining uncertainty"
- **Terminal states**: clearly distinguishes complete, error, and stopped (no more misleading "complete" after a failure)
- **Retry from a role**: re-run just the critic or judge without re-spending the proposer
- **Token usage**: per-role and total token counts shown after each debate
- **Persistent debates**: every debate saved to `~/.debate-tool/debates/{id}.json` for inspection
- **Clear-key buttons**: explicitly remove a saved API key

## Requirements

- **Python 3.10+** — [download](https://www.python.org/downloads/)
- **Node.js 18+** — [download](https://nodejs.org/)
- API keys from any provider whose models you want to use:
  - [Anthropic](https://console.anthropic.com) (Claude)
  - [OpenAI](https://platform.openai.com/api-keys) (GPT)
  - [Google AI Studio](https://aistudio.google.com/app/apikey) (Gemini)

You don't need all three keys — just the ones for the models you'll use. Defaults are Claude/GPT/Gemini; you can change which model fills which role in the settings.

## First run

1. Extract the `debate-tool` folder anywhere on your machine.
2. Double-click `start.bat` (Windows) or `start.command` (Mac).
3. The first run installs dependencies — takes 2-3 minutes. Subsequent runs start in seconds.
4. Browser opens automatically to `http://localhost:3000`.
5. Click "settings" in the top right and paste your API keys.
6. Click "Save settings", go back to main, ask your first question.

## Cost

Each debate uses roughly 5-15 cents of API credit depending on question complexity. The models are billed per token by their respective providers — there's no markup or middleman.

## Where things live

- `backend/` — Python FastAPI server (port 8000), handles orchestration and SSE streaming
- `frontend/` — Next.js UI (port 3000)
- `~/.debate-tool/config.json` — your saved settings (API keys live here, encrypted only by your filesystem)
- `~/.debate-tool/debates/{id}.json` — every debate is persisted here, inspectable with any text editor, deletable individually
- Each launch script handles dependency installation automatically on first run

## Stopping

Close the two terminal windows that opened (backend and frontend), or Ctrl+C in the launcher window.

## Updating model strings

The settings page has dropdowns with fallback model names, plus a **"↻ fetch live"** button on each role that queries the provider's API directly with your saved key and shows the actual list of models available to your account. Use this when:

- A model errors with "not found" — your account may have access to a slightly different version
- You want to use the very latest model the provider just released
- Provider naming conventions have shifted since the fallback list was set

There's also a "custom" toggle if you want to type any model string directly.

## Known caveats

Provider model names drift. Anthropic and OpenAI tend to be stable; Google's Gemini naming changes more often (preview suffixes, version bumps). The "fetch live" button is the safest way to know what actually works.
