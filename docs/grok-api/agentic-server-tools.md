# Tool server-side (agentic): web search, X search, code execution, collections, files, remote MCP

> **Verificato il:** 2026-11-03 su docs.x.ai e sulle firme di `xai-sdk 1.21.0`.
> ⚠️ Snippet tratti dai docs ufficiali e **non eseguiti** contro l'API.

## Come funzionano
Si passano nell'array `tools` della **Responses API** (oppure con xai-sdk). SpaceXSI esegue il loop agentico **lato server**: il modello decide, chiama il tool, legge il risultato e risponde con le citazioni. I tool server-side **non sono disponibili su Chat Completions**, che supporta solo function calling.
- Si possono mischiare con le function client-side. I tool server-side vengono eseguiti da soli, mentre le function custom mettono in pausa il loop e restituiscono il controllo a noi.
- `max_turns` limita i turni del loop agentico (non il numero di singole chiamate). I valori consigliati sono 1–2 per lookup rapidi e 3–5 per un buon compromesso. Senza `max_turns` si applica un cap globale di default.
- Gli output dei tool server-side **non** vengono restituiti di default: si vedono solo le invocazioni (`response.tool_calls`) e i conteggi (`server_side_tool_usage`). Con xai-sdk si può chiedere `include=["web_search_call_output", ...]` e `include=["verbose_streaming"]` per vedere le chiamate in streaming.
- La documentazione raccomanda di usarli **in streaming**, per avere visibilità durante richieste che possono essere lunghe.
- ⚠️ **Latenza:** ogni tool aggiunge almeno un giro di inferenza più l'esecuzione del tool. Vanno **tenuti fuori** dal percorso real-time del robot.

## Nomi dei tool e prezzi

| Tool | Responses API (`type`) | xai-sdk | Vercel AI SDK | Costo invocazione |
|---|---|---|---|---|
| Web Search | `web_search` | `web_search()` | `xai.tools.webSearch()` | $5 / 1k chiamate |
| X Search | `x_search` | `x_search()` | `xai.tools.xSearch()` | $5 / 1k **post** + $10 / 1k **profili** recuperati |
| Code Execution | `code_interpreter` | `code_execution()` | `xai.tools.codeExecution()` | $5 / 1k |
| Collections Search | `file_search` (con `vector_store_ids`) | `collections_search(collection_ids=[...])` | via `@ai-sdk/openai` `fileSearch` | $2.50 / 1k |
| File attachments | automatico (`attachment_search`) quando si allega un `input_file` | `file(...)` | — | $5 / 1k |
| Remote MCP | `mcp` | `mcp(server_url=..., server_label=...)` | — | solo token |
| Image Generation | `image_generation` | `image_generation()` | — | tariffe Imagine |
| view_image / view_x_video | si abilitano con `enable_image_understanding` / `enable_video_understanding` | — | — | solo token immagine |

A questi costi si aggiungono **sempre** i token: input (cumulativo su tutti i passi del loop), reasoning e output. Si pagano solo le esecuzioni riuscite (`server_side_tool_usage`). In gRPC (xai-sdk) i nomi `code_interpreter` e `file_search` non sono supportati: vanno usati `code_execution` e `collections_search`.

## Web Search
Parametri: `allowed_domains` (max 5) **oppure** `excluded_domains` (max 5), non entrambi; `enable_image_understanding`; `enable_image_search` (immagini restituite come Markdown `![alt](url)`, non esposto dal Vercel AI SDK). xai-sdk accetta anche `user_location_country/city/region/timezone`.
```python
# OpenAI SDK
response = client.responses.create(
    model="grok-4.7",
    input=[{"role": "user", "content": "What exhibits are at the Ctrl+Alt Museum in Pavia?"}],
    tools=[{"type": "web_search", "filters": {"allowed_domains": ["example.org"]}}],
)
```
⚠️ Nell'OpenAI SDK i domini vanno dentro `filters: {allowed_domains: [...]}`, mentre in xai-sdk sono argomenti diretti: `web_search(allowed_domains=[...])`.

## X Search
Parametri: `allowed_x_handles` **oppure** `excluded_x_handles` (max 20, senza `@`), `from_date`/`to_date` (`YYYY-MM-DD`; con xai-sdk sono oggetti `datetime`), `enable_image_understanding`, `enable_video_understanding`.
```python
response = client.responses.create(
    model="grok-4.7",
    input=[{"role": "user", "content": "What has SpaceX posted about Starship recently?"}],
    tools=[{"type": "x_search", "allowed_x_handles": ["SpaceX"]}],
)
```
Il billing è per elemento: dal 21/09/2026 si contano i post recuperati (inclusi parent e quoted) e i profili. I conteggi sono in `usage.server_side_tool_usage_details.x_posts_fetched` / `x_users_fetched`.

## Code Execution
Sandbox Python stateless con le librerie comuni (NumPy, Pandas, Matplotlib, SciPy), **senza rete** e con file system limitato. I limiti di tempo e memoria non sono quantificati ⚠️.
```python
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import code_execution

chat = Client().chat.create(model="grok-4.7", tools=[code_execution()])
chat.append(user("Calculate the compound interest for $10,000 at 5% annually for 10 years"))
print(chat.sample().content)
```

## Files API (allegati in chat)
- Upload: `POST /v1/files` (multipart con `file` e `purpose`). Con xai-sdk: `client.files.upload(bytes_or_path, filename=...)`. È possibile impostare un TTL con `expires_after`/`expires_at`.
- In chat: `{"type": "input_file", "file_id": "file-..."}` oppure `{"type": "input_file", "file_url": "https://..."}`. Con xai-sdk: `file(uploaded.id)` oppure `file(url=...)`.
- Allegare un file attiva **automaticamente** `attachment_search` e trasforma la richiesta in una richiesta agentica, che si paga come un tool.
- Limiti: **512 MB per file**; formati testuali (txt, md, codice, csv, json, pdf, …); niente batch (`n>1`); servono modelli agentici (`grok-4.20`, `4.5`, `4.6`, `4.7`).
- Storage: $0.025 / GiB / giorno. Download: $0.20 / GiB.
```python
from xai_sdk import Client
from xai_sdk.chat import user, file
client = Client()
up = client.files.upload(b"Robot manual: max speed 1.2 m/s", filename="manual.txt")
chat = client.chat.create(model="grok-4.7")
chat.append(user("What is the max speed?", file(up.id)))
print(chat.sample().content)
client.files.delete(up.id)
```

## Collections (RAG persistente)
- Una collection è un gruppo di file con un indice di embedding e ricerca semantica, ibrida o per keyword. Si possono aggiungere metadata fields per filtrare.
- Per **creare e gestire** le collection serve la **Management API key** (`XAI_MANAGEMENT_API_KEY`, host `management-api.x.ai`), oppure la console: console.x.ai → Collections. La **ricerca** invece usa la normale API key.
- Limite: 100 MB per file nelle collection. Storage: $0.10 / GiB / giorno.
```python
# xai-sdk (estratto dall'esempio ufficiale, che è async)
client = AsyncClient(api_key=os.getenv("XAI_API_KEY"), management_api_key=os.getenv("XAI_MANAGEMENT_API_KEY"))
coll = await client.collections.create("museum-docs")
# upload: await client.collections.upload_document(collection_id=coll.collection_id, ...)  -> poi polling dello stato fino a DOCUMENT_STATUS_PROCESSED
chat = client.chat.create(model="grok-4.7", tools=[collections_search(collection_ids=[coll.collection_id])])
```
```python
# OpenAI SDK (collection già creata)
client.responses.create(model="grok-4.7", input="...",
    tools=[{"type": "file_search", "vector_store_ids": ["collection_..."], "max_num_results": 10}])
```
⚠️ Per gli argomenti esatti di `upload_document` serve l'esempio completo in https://docs.x.ai/developers/tools/collections-search.md, che non ho riportato qui per intero. Per un hackathon conviene creare la collection **dalla console**.

## Remote MCP
- Parametri: `server_url` (obbligatorio, solo transport **Streamable HTTP** o **SSE**), `server_label` (obbligatorio sulla Responses API), `server_description`, `allowed_tools` (xai-sdk: `allowed_tool_names`), `authorization` (finisce nell'header Authorization verso il server MCP), `headers` (xai-sdk: `extra_headers`).
- **Non supportati:** `require_approval` e `connector_id` dell'OpenAI Responses API.
- È SpaceXSI che si collega al server MCP, quindi **il server deve essere raggiungibile pubblicamente via HTTPS**. Per un MCP che gira sul laptop o sul robot serve un tunnel (ngrok, cloudflared). ⚠️ Questa è una deduzione dall'architettura, non è scritta esplicitamente.
- Si pagano solo i token, ma senza `allowed_tools` tutte le definizioni dei tool del server finiscono nel contesto.
```python
response = client.responses.create(
    model="grok-4.7",
    input=[{"role": "user", "content": "What can you do with https://github.com/xai-org/xai-sdk-python?"}],
    tools=[{"type": "mcp", "server_url": "https://mcp.deepwiki.com/mcp", "server_label": "deepwiki"}],
)
```
```python
from xai_sdk.tools import mcp
chat = client.chat.create(model="grok-4.7", tools=[
    mcp(server_url="https://my-robot.example.com/mcp", server_label="robot",
        allowed_tool_names=["get_status", "sit"], authorization="Bearer <token>")])
```
**Idea per l'hackathon:** esporre il robot come server MCP (Streamable HTTP) dietro un tunnel e farlo usare sia a Grok API sia a Grok Voice. La pagina Remote MCP cita il supporto anche nella Speech to Speech API. Resta da valutare la latenza.

## Identificare chi esegue un tool (necessario nei loop misti)
- **Responses API:** in `output[].type`, `function_call` va eseguito da noi; `web_search_call`, `code_interpreter_call`, `file_search_call` e `mcp_call` sono server-side; `custom_tool_call` con `call_id` che inizia per `xs_` è X search, con `as_` è attachment search.
- **xai-sdk:** `get_tool_call_type(tc)` restituisce `"client_side_tool"`, `"web_search_tool"`, `"x_search_tool"`, `"code_execution_tool"`, `"collections_search_tool"` o `"mcp_tool"`.

## Citazioni
L'API restituisce le URL delle fonti: con xai-sdk in `response.citations`, con il Vercel AI SDK in `sources`. Con xai-sdk le citazioni inline si chiedono con `include=["inline_citations"]`. Dettagli: https://docs.x.ai/developers/tools/citations.md

## Fonti
- https://docs.x.ai/developers/tools/overview.md
- https://docs.x.ai/developers/tools/web-search.md
- https://docs.x.ai/developers/tools/x-search.md
- https://docs.x.ai/developers/tools/code-execution.md
- https://docs.x.ai/developers/tools/collections-search.md
- https://docs.x.ai/developers/tools/remote-mcp.md
- https://docs.x.ai/developers/tools/tool-usage-details.md
- https://docs.x.ai/developers/tools/streaming-and-sync.md
- https://docs.x.ai/developers/tools/citations.md
- https://docs.x.ai/developers/files.md
- https://docs.x.ai/developers/model-capabilities/files/chat-with-files.md
- https://docs.x.ai/developers/files/collections.md
- https://docs.x.ai/developers/pricing.md (Tools Pricing, Files and Collections Pricing)
