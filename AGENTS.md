# AGENTS.md

Le istruzioni per gli agenti di coding di questa repo (Cursor, Grok Build, Codex…) stanno in [CLAUDE.md](CLAUDE.md): leggilo per primo. La documentazione è indicizzata in [docs/README.md](docs/README.md).

Regole essenziali (dettagli in CLAUDE.md):
- Il codice di runtime chiama **solo** Grok (API, Voice, Imagine, Bot), mai SDK o modelli Anthropic.
- Il codice che muove hardware passa sempre da un validatore deterministico, ha un kill switch locale e si prova prima in mock (vedi `.claude/skills/robot-safety/SKILL.md`).
- I segreti stanno solo in `.env`, mai nel repo.
