# grokbot-hackathon

Team **aidea** al **Grok Hackathon at the Museum**: Ctrl+Alt Museum, Pavia, 4–5 novembre 2026.

> Pick a piece of hardware, an API, connect it to Grok (the API, Grok Voice, or the bot framework), and by Thursday afternoon show us something that didn't work when you started.

## Cosa c'è qui

- [`docs/`](docs/README.md): tutta la ricerca preparatoria (Grok API, Grok Voice, Grok Bot, Imagine, SDK dell'hardware, evento, giuria, idee). Parti da [docs/README.md](docs/README.md).
- [`CLAUDE.md`](CLAUDE.md): contesto e fatti chiave per Claude Code, con la mappa dei docs.
- [`docs/voice/examples/`](docs/voice/examples/): client vocali pronti (locale con mic/casse, browser con token effimero, bridge Twilio, TTS streaming).

## Primi 15 minuti all'evento

```bash
cp .env.example .env            # e incolla la XAI_API_KEY dell'evento
python -m venv .venv && source .venv/bin/activate
pip install -r docs/voice/examples/requirements.txt xai-sdk openai
set -a && source .env && set +a
python docs/voice/examples/voice_agent_local.py --text   # primo smoke test della Voice API
```

Poi: giro dell'hardware con [docs/ideas/staff-questions.md](docs/ideas/staff-questions.md) alla mano e **video del "prima"**.

## Il progetto

Da decidere mercoledì mattina dopo il giro dell'hardware. Candidati: vedi [docs/ideas/ideas.md](docs/ideas/ideas.md).
