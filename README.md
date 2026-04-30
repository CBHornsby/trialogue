# Trialogue

A local tool for running disciplined multi-model review on hard questions. One model proposes an answer, a second model independently establishes review criteria and critiques against them, and a third adjudicates and synthesizes a final answer.

Built for technical power users — developers, analysts, researchers, technical writers — who already do this kind of review work manually across browser tabs and want to make it repeatable, auditable, and structured. Not aimed at casual chatbot use; for that, the native Claude.ai and ChatGPT interfaces are better.

## What it does

Each question runs through these stages:

1. **Proposer** drafts the initial answer
2. **Critic Criteria** generates review criteria from the question alone, before seeing the proposed answer (independent baseline)
3. **Critic** reviews the proposed answer against those criteria with severity and confidence ratings
4. **Judge** adjudicates each critic point (accept/reject/modify/uncertain), leads with the final answer, and surfaces remaining uncertainty in structured form

You watch the proposer, critic, and judge stream live in their own panels. The criteria-generation step runs in parallel with the proposer in the background, so it adds no perceived latency — the criteria are ready by the time the critic stage begins. Token usage is shown per-role and total. If any role fails or is stopped, you can retry just that role without re-running the earlier ones.

## What's new

- **Truly independent critic criteria**: the criteria are generated from the question alone in a separate call, before the model sees the proposed answer — preventing the anchoring effect of inline criteria steps
- **Calibrated critic**: severity and confidence ratings on each issue, with explicit "no significant issues" as a valid output
- **Adjudicating judge**: each critic point is explicitly accepted, rejected, modified, or marked uncertain, with reasoning visible in the output
- **Structured uncertainty**: judge output surfaces context gaps, version dependencies, definitions to confirm, and claims to verify before production use
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

## Token usage

Trialogue reports token usage per role and total after each debate completes. Actual API cost depends on your provider, model, account tier, and current pricing — Trialogue makes no assumption about pricing because providers change it. Tokens are stable; cost is a moving interpretation. Check your provider's current per-token pricing if you want to estimate cost.

The criteria-independence step adds a small criteria-generation call before the main critic review, modestly increasing total tokens per debate compared to a single critic call. Because the criteria step runs in parallel with the proposer (both depend only on the question), it does not add latency — the criteria finish before the proposer does in most cases.

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
