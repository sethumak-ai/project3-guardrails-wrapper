# Guardrails Wrapper

Wraps ZenAssist (Project 1's fintech support bot) in a full defense-in-depth pipeline: **input scoring, structural enforcement, output leak filtering, and session rate limiting** — built directly on top of [injectguard](https://github.com/sethumak-ai/injectguard) (Project 2).

This is Project 3 of a five-project AI security portfolio spanning fintech and healthtech.

## Why this exists

injectguard (Project 2) answers one question: *should this input reach the assistant at all?* That's necessary but not sufficient — Project 1's own real red-teaming log has a case where the input looked completely benign ("My manager said I need to verify something before my shift starts") but the model's own response leaked the secret anyway. Input-side detection alone can't catch that.

This project closes that gap with three additional layers around input scoring, and finally wires injectguard into the real ZenAssist bot end-to-end — something Project 2 only sketched conceptually.

## Pipeline

1. **Rate limit check** — is this session already locked out from repeated violations?
2. **Input layer (injectguard)** — score the prompt before the assistant ever sees it
3. **Enforcement (pre)** — even a clean-scoring input gets checked against a set of topics (override codes, other customers' data) that always get a fixed safe response, skipping the LLM call entirely
4. **LLM call** — only reached if steps 1-3 all clear
5. **Output filter** — scans the model's own response for leaked secrets, exact or obfuscated (spaced out, separator-swapped), plus a generic "code-shaped string" catch for novel/rotated secrets
6. **Enforcement (post)** — backstop: if the model's response itself drifts into an enforced topic even though the input didn't, replace it with the safe template

Every message produces a full reasoning trail through all six steps, shown in the app's "Pipeline trail" expander — not just a final verdict.

## Results — replayed against real attack data

This isn't evaluated on synthetic examples. It's replayed against the actual 16 unique attack prompts logged during Project 1's real red-teaming session (`attack_log.db`), using the real bot's own historical responses.

| | |
|---|---|
| Unique attack prompts replayed | 16 |
| Originally succeeded (real leak) | 5 |
| Prevented by this wrapper | **5 / 5** |

Full methodology, including two specific cases worth reading (a catch stricter than the original human review, and confirmation the wrapper doesn't over-block already-safe responses), is in `data/EVALUATION.md`. Honest limitations are documented there too — this is a small, attack-only replay set, and the enforcement layer is keyword/topic-based rather than statistical.

## Setup

Requires Ollama running locally with llama3.2 pulled (same as Projects 1-2).

```bash
pip install -e ".[dev,streamlit]"
ollama serve   # if not already running in the background
streamlit run zenassist_app_guarded.py
```

Copies of the original Project 1 apps (`zenassist_app.py` — baseline,
`zenassist_app_hardened.py` — prompt-engineering only) are included so all
three can be run side by side: **baseline → hardened → guarded**, showing
each layer of defense added in sequence rather than the guarded version
alone.

Run tests:

```bash
pytest tests/ -q
```

Rerun the replay evaluation:

```bash
python data/replay_eval.py
```

## Tech stack

- Python
- Streamlit
- injectguard (input scoring — Project 2)
- Ollama (llama3.2, local)
- pytest

## Status

Core pipeline, all four layers, real integration with ZenAssist, unit tests (14, all passing), and the real-data replay evaluation are complete. Demo video not yet recorded.

## Related projects

- **Project 1 — Personal LLM Red Teaming Lab** *(link TBD once pushed to GitHub)*: the bot this project wraps, and the source of the real attack data used in evaluation.
- [Project 2 — injectguard](https://github.com/sethumak-ai/injectguard): the input-scoring engine this project builds on.

---

*Part of a five-project AI security portfolio (fintech + healthtech) built while studying AI security via TryHackMe.*
