# SDK quickstart (Python e TypeScript) e setup per Claude Code

> **Verificato il:** 2026-11-03. Versioni controllate su PyPI, npm e GitHub lo stesso giorno.
> ⚠️ Snippet tratti dai docs ufficiali e **non eseguiti** contro l'API. Le firme di `xai-sdk 1.21.0` le ho ispezionate installando il pacchetto.
> ✅ **Dal 2026-11-04 abbiamo una API key xAI** (`xai-...`, in `.env` come `XAI_API_KEY`). Verificato con una `curl` su `POST /v1/responses` con `grok-4.3` e `reasoning.effort: "none"`: HTTP 200 in ~1,1 s. Gli snippet qui sotto restano da provare uno per uno.

## Stato attuale e SDK da usare (2026-11-04)

- **Oggi** il prototipo gira con l'**SDK `openai`** su un modello OpenAI (`gpt6luna`). **Dopo** deve passare a un modello Grok.
- **Usare l'SDK `openai` con `base_url="https://api.x.ai/v1"`**, non `xai-sdk`: la migrazione si riduce a cambiare tre valori (`api_key`, `base_url`, `model`), senza riscrivere il codice. `xai-sdk` serve solo se servono funzioni che l'SDK OpenAI non copre (collections, management, voice).
- Tenere i tre valori in `.env`/config, mai nel codice:
  ```python
  client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])
  # oggi:  LLM_BASE_URL=https://api.openai.com/v1   LLM_MODEL=gpt6luna
  # poi:   LLM_BASE_URL=https://api.x.ai/v1         LLM_MODEL=grok-4.3   (o grok-4.7)
  ```
- Preferire la **Responses API** (`client.responses.create`): funziona uguale su OpenAI e su xAI. Per bassa latenza `grok-4.3` con `reasoning.effort: "none"`.
- **Chiavi `grok_...` non servono per Grok.** Quelle create su grok.com/dashboard/api-keys con Type "Cursor" valgono solo per le API Cursor Cloud Agents (`api.cursor.com`), non per `api.x.ai`, dove rispondono `400 Incorrect API key`. La chiave giusta inizia con `xai-`.

## Quale SDK usare

| SDK | Install | Versione al 2026-11-03 | Trasporto | Note |
|---|---|---|---|---|
| **xai-sdk** (ufficiale Python) | `pip install xai-sdk` / `uv add xai-sdk` | **1.21.0** (23/10/2026), Python ≥ 3.10 | gRPC | Copre tutto: chat, tool server-side, collections, files, voice, management. Client sync e async. |
| **openai** (Python) | `pip install openai` | 3.42.1 | REST | `base_url="https://api.x.ai/v1"`. Ideale se il codice esistente è già OpenAI. |
| **openai** (JS) | `npm install openai` | 7.47.0 | REST | `baseURL: "https://api.x.ai/v1"` |
| **Vercel AI SDK** | `npm install ai @ai-sdk/xai zod` | `ai` 7.0.162, `@ai-sdk/xai` 5.0.38 | REST | `xai.responses('grok-4.7')`. Tool loop automatico con `stopWhen`. |
| **@xai-official/sdk** (ufficiale TS) | `npm install @xai-official/sdk` | 0.2.7, **sperimentale** | REST | Node ≥ 22.13, solo ESM, classe `SpaceXSI`. Va fissata la versione esatta. |

La variabile d'ambiente `XAI_API_KEY` viene letta in automatico da xai-sdk, `@xai-official/sdk` e `@ai-sdk/xai`. Con l'SDK OpenAI va passata esplicitamente.

## Python, xai-sdk: hello world, streaming e async
```python
# pip install xai-sdk
import os
from xai_sdk import Client
from xai_sdk.chat import system, user

client = Client(api_key=os.getenv("XAI_API_KEY"), timeout=120)  # default 1620 s (27 min)
chat = client.chat.create(
    model="grok-4.3",
    reasoning_effort="none",   # valori accettati dall'SDK: none|low|medium|high|xhigh
    messages=[system("You are the voice of a robot dog in a museum. Answer in Italian, max 2 sentences.")],
)
chat.append(user("Ciao! Chi sei?"))

for response, chunk in chat.stream():
    print(chunk.content, end="", flush=True)
print()
chat.append(response)  # mantiene la history, incluso l'eventuale reasoning cifrato
```
```python
import asyncio
from xai_sdk import AsyncClient
from xai_sdk.chat import user

async def main():
    chat = AsyncClient().chat.create(model="grok-4.7")
    chat.append(user("Hello"))
    r = await chat.sample()
    print(r.content)

asyncio.run(main())
```
Parametri di `client.chat.create(...)` verificati nella v1.21.0: `model`, `messages`, `tools`, `tool_choice`, `parallel_tool_calls`, `response_format` (anche una classe Pydantic), `reasoning_effort`, `temperature`, `top_p`, `max_tokens`, `store_messages`, `previous_response_id`, `use_encrypted_content`, `max_turns`, `include`, `service_tier` (`default` | `priority`), `safety_identifier`, `guidelines`, `agent_count` (4 | 16), `conversation_id`, `seed`, `stop`.
Costruttore `Client(...)`: `api_key`, `management_api_key`, `api_host="api.x.ai"`, `management_api_host`, `metadata` (es. `(("x-grok-conv-id", "<uuid>"),)` per la cache), `channel_options`, `timeout`.
- Timeout: si imposta **solo** sul client, non per singola chiamata. Allo scadere si riceve `grpc.RpcError` con `DEADLINE_EXCEEDED`.
- Retry: sono automatici solo su `UNAVAILABLE` (backoff da 0,1 s fino a 1 s, al massimo 5 tentativi). Il 429 (`RESOURCE_EXHAUSTED`) non viene ritentato di default. Per disattivare i retry: `channel_options=[("grpc.enable_retries", 0)]`.
- ⚠️ Nella v1.21.0 il `Literal` dei model id non include ancora `grok-4.7`, ma il parametro accetta qualsiasi `str` e i docs lo usano. Il type checker può segnalare un warning che si può ignorare.

## Python, OpenAI SDK
```python
# pip install openai
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")

stream = client.responses.create(
    model="grok-4.7",
    reasoning={"effort": "low"},
    input=[{"role": "user", "content": "Say hi in Italian."}],
    stream=True,
    prompt_cache_key="session-123",  # kwarg accettato da openai 3.42.1; con SDK vecchi: extra_body={"prompt_cache_key": ...}
)
for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
```

## JS/TS, OpenAI SDK
```javascript
// npm install openai
import OpenAI from "openai";
const client = new OpenAI({ apiKey: process.env.XAI_API_KEY, baseURL: "https://api.x.ai/v1" });

const response = await client.responses.create({
  model: "grok-4.7",
  reasoning: { effort: "low" },
  input: "Say hi in Italian.",
  prompt_cache_key: "session-123",
});
console.log(response.output_text);
```

## TS, Vercel AI SDK
```javascript
// npm install ai @ai-sdk/xai zod
import { xai } from '@ai-sdk/xai';
import { generateText, streamText } from 'ai';

const { text } = await generateText({ model: xai.responses('grok-4.7'), prompt: 'Hello' });

const result = streamText({ model: xai.responses('grok-4.7'), prompt: 'Explain PID in 2 sentences.' });
for await (const chunk of result.textStream) process.stdout.write(chunk);
```
- `xai.responses(...)` usa la Responses API, `xai(...)` usa Chat Completions (legacy).
- Endpoint custom: `createXai({ baseURL: 'https://us.api.x.ai/v1' })`.
- Tool server-side: `tools: { web_search: xai.tools.webSearch(), x_search: xai.tools.xSearch(), code_execution: xai.tools.codeExecution() }`.

## TS, `@xai-official/sdk` (sperimentale)
```ts
// npm install @xai-official/sdk@0.2.7   (fissare la versione: le API possono cambiare prima della 1.0)
import { SpaceXSI } from "@xai-official/sdk";
import { webSearch } from "@xai-official/sdk/tools";

const client = new SpaceXSI({ timeout: 60_000, idleTimeout: 30_000, maxRetries: 2 });

const stream = await client.responses.create({
  model: "grok-4.7",
  input: "Write a short story about a curious robot.",
  reasoning: { effort: "low" },
  stream: true,
});
const response = await stream.on("text", (t) => process.stdout.write(t)).done();
```
- ⚠️ Questo SDK invia **`store: false` di default**, al contrario dell'API che ha `store: true`. Per la history si usa `response.toInput()`.
- Ha `toText()`, `toJson(zodSchema)`, gli eventi `client_tool_call` e `server_tool_call`, il tool `shell`, `XAI_DEBUG=1` per stampare le richieste in formato curl e le classi d'errore (`RateLimitError`, `AuthenticationError`, …).
- Di default **blocca l'uso da browser**: la key va tenuta sul server.
- Il vecchio nome della classe `SpaceXAI` resta disponibile come alias deprecato.

## Verifica rapida della key e dei modelli (prima cosa da fare in hackathon)
```bash
export XAI_API_KEY="xai-..."
curl -s https://api.x.ai/v1/api-key -H "Authorization: Bearer $XAI_API_KEY"        # info sulla key
curl -s https://api.x.ai/v1/models  -H "Authorization: Bearer $XAI_API_KEY" | python3 -m json.tool | grep '"id"'
```

## Setup per Claude Code durante l'hackathon
1. **Docs MCP server ufficiale** (Streamable HTTP, stateless): `https://docs.x.ai/api/mcp`. In Claude Code si aggiunge così:
   ```bash
   claude mcp add --transport http xai-docs https://docs.x.ai/api/mcp
   ```
   (La pagina ufficiale mostra la configurazione per Grok Build, Cursor, Zed, Windsurf e OpenCode. Il comando per Claude Code è verificato il 2026-11-03: `initialize` e `tools/list` rispondono senza chiavi, 4 tool `list_doc_pages`, `get_doc_page`, `search_docs`, `get_llms_txt`. È già configurato nel `.mcp.json` della repo.)
2. **Docs come markdown:** si aggiunge `.md` a qualsiasi URL di docs.x.ai, per esempio `curl -sL https://docs.x.ai/developers/tools/function-calling.md`. Con l'header `Accept-Language: en, python-xai` (oppure `python-openai`, `javascript-ai-sdk`, `javascript-openai`) si ricevono solo gli esempi del linguaggio scelto. L'indice completo è su https://docs.x.ai/llms.txt.
3. **OpenAPI spec:** https://docs.x.ai/openapi.json
4. **Plugin ufficiale "Grok Build ↔ Claude Code"** (`xai-org/grok-build-plugin-cc`) per delegare review e task a Grok Build da dentro Claude Code: vedi [grok-build.md](grok-build.md).
5. **Cookbook:** https://github.com/xai-org/xai-cookbook. Esempi utili per l'evento: `voice-agent-web`, `voice-agent-webrtc`, `voice-agent-mobile`, `live-interpreter`, `screenshot-to-component`, `database-over-mcp`, `refund-agent-human-approval` (pattern human-in-the-loop), `prompt-caching`, `reasoning-effort-evals`.

## Fonti
- https://docs.x.ai/developers/quickstart.md
- https://github.com/xai-org/xai-sdk-python (README: Timeouts, Retries) e https://pypi.org/project/xai-sdk/ (1.21.0)
- https://github.com/xai-org/xai-sdk-ts e https://www.npmjs.com/package/@xai-official/sdk (0.2.7)
- https://www.npmjs.com/package/@ai-sdk/xai (5.0.38)
- https://docs.x.ai/developers/docs-mcp.md
- https://docs.x.ai/llms.txt
- https://docs.x.ai/developers/advanced-api-usage/regions.md
- https://github.com/xai-org/xai-cookbook
