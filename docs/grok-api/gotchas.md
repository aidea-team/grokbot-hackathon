# Gotchas, errori comuni, limiti e latenza (robot real-time)

> **Verificato il:** 2026-11-03 su docs.x.ai. Le parti marcate "consiglio" sono mie deduzioni, non frasi dei docs.

## Errori HTTP / gRPC

| Codice | Causa tipica | Cosa fare |
|---|---|---|
| **400** | Schema JSON non supportato (radice dei tool non object, `enum` vuoto, `items` come array…), `stop`/`presence_penalty`/`frequency_penalty` con un modello reasoning | Semplificare lo schema; togliere quei parametri |
| **401** | Key mancante o errata | `Authorization: Bearer $XAI_API_KEY` |
| **403** | Permessi del team o della key | Admin del team in console |
| **404** | Model id sbagliato o non disponibile sull'endpoint (es. `grok-latest` o `grok-4.3` sull'endpoint US) | `GET /v1/models` |
| **422** | Campo del body nel formato sbagliato | Confrontare con la API reference |
| **429** | Rate limit (RPS o TPM per modello) | Backoff esponenziale; il tier sale con la spesa |
| **5xx / UNAVAILABLE** | Problema lato servizio | Retry con backoff; https://status.x.ai |
| gRPC `DEADLINE_EXCEEDED` | Timeout del client xai-sdk (default 1620 s) | Aumentare `timeout` del `Client` |
| gRPC `RESOURCE_EXHAUSTED` | Equivale a 429 | Backoff (xai-sdk non lo ritenta di default) |
| WS `previous_response_not_found` | `previous_response_id` non in cache con `store=false` | Ripartire con l'input completo |
| Violazione delle usage policy | Contenuto bloccato | Si paga comunque. Se la violazione è intercettata prima della generazione (Responses), c'è un fee di $0.05 |

## Trappole frequenti (soprattutto quando il codice lo scrive un agente)
1. **Model id vecchi.** Molti esempi online usano `grok-4-1-fast-reasoning`, `grok-4-fast-non-reasoning`, `grok-3`, `grok-2-vision-1212`, `grok-code-fast-1`. Dal 15/05/2026 sono ritirati e reindirizzati: costano e si comportano come `grok-4.3` o `grok-build-0.1`. Vanno usati gli id in [models.md](models.md).
2. **Il nome è `grok-4.7`**, con il punto. `grok-4-7` compare solo negli URL dei docs. `grok-4.7-fast` non esiste sull'API.
3. **Formato dei tool diverso** tra Responses (piatto, `function_call`/`function_call_output`) e Chat Completions (annidato, `tool_calls`/`role: tool`). Vedi [tools-and-structured-output.md](tools-and-structured-output.md).
4. **Il reasoning di grok-4.7/4.6/4.5 non si disattiva.** `effort: "none"` è documentato **solo** per `grok-4.3`. ⚠️ Non so cosa succeda passando `none` a `grok-4.7`: potrebbe dare errore o essere ignorato.
5. **Reasoning item da ripassare invariati** nei multi-turn stateless. Estrarre solo `output_text` peggiora la qualità e rompe la cache.
6. **`store` è true di default** sulla Responses API (conservazione 30 giorni), ma l'SDK TS `@xai-official/sdk` manda `store:false` di default. Con le immagini conviene `store:false`, perché i docs avvisano che altrimenti la richiesta può fallire.
7. **`instructions` non si può combinare con `previous_response_id`**: viene usato il system prompt della risposta precedente.
8. **Chat Completions è deprecata**: niente reasoning cifrato e niente tool server-side. Va usata solo se una libreria lo richiede.
9. **Anthropic SDK (`/v1/messages`) "fully deprecated"**: da evitare.
10. **`additionalProperties` è false di default** negli structured outputs; regex ancorate e senza lookaround.
11. **Le function call in streaming arrivano intere** in un chunk, non come delta.
12. **Parallel tool calls attive di default**: un robot potrebbe ricevere "cammina" e "siediti" nello stesso turno. Si può impostare `parallel_tool_calls: false` oppure validare la sequenza.
13. **Timeout:** i docs suggeriscono timeout lunghi (900–3600 s) per il reasoning `high`. Per il real-time conviene il contrario: modello veloce e timeout corto con fallback.
14. **`temperature` sopra 1 viene trattata come 1.** La raccomandazione ufficiale è 0.7 / 0.95.
15. **Remote MCP** richiede un server raggiungibile da Internet (Streamable HTTP o SSE). `require_approval` non è supportato.
16. **Collections** richiedono una Management key separata per crearle o gestirle.
17. **Brand:** i docs e il codice parlano di **"SpaceXSI"** (SpaceX Super Intelligence LLC). In alcuni repo GitHub compare ancora "SpaceXAI", e la classe TS `SpaceXAI` è un alias deprecato. Domini, key ed env var restano `x.ai`, `XAI_API_KEY`, `xai_sdk`.

## Latenza per robot real-time: cosa fare

**Architettura (consiglio):** Grok **non** deve stare nel loop di controllo a bassa latenza (PID, equilibrio, evitamento ostacoli). Conviene usarlo come **planner o dialogo ad alto livello** che emette comandi strutturati (function call o JSON schema). Un layer locale li valida (whitelist, limiti di velocità, e-stop) e li esegue.

**Leve documentate per ridurre la latenza:**

| Leva | Dettaglio | Fonte |
|---|---|---|
| Modello senza reasoning o con reasoning minimo | `grok-4.3` + `reasoning.effort: "none"`, oppure `grok-4.20-0309-non-reasoning`. Su `grok-4.7` il minimo è `"low"` ("Latency-sensitive agentic use and simple tool calling") | reasoning.md, may-15-retirement.md |
| Streaming | `stream: true`, per mostrare o sintetizzare il testo man mano | streaming.md |
| Prompt caching | `prompt_cache_key` stabile per ogni sessione, system prompt e definizioni dei tool **statici e all'inizio**, solo append. La cache riduce costo e TTFT | best-practices.md, prompt-caching |
| WebSocket mode | `wss://api.x.ai/v1/responses`, fino a circa -20% end-to-end nei loop con molti tool; warmup con `generate:false` | websocket-mode.md |
| Priority processing | `service_tier: "priority"`, TTFT e latenza inter-token più bassi sotto carico, costo 2x | priority-processing.md |
| Context compaction | Contesto più piccolo, TTFT più basso nelle sessioni lunghe | context-compaction.md |
| Immagini leggere | `detail: "low"`, JPEG ridimensionati, un frame solo quando serve | vision.md |
| Niente tool server-side nel percorso caldo | Ogni tool aggiunge turni di inferenza; se servono, `max_turns: 1-2` | tool-usage-details.md |
| `parallel_tool_calls: false` + pochi tool | Meno definizioni nel contesto e azioni deterministiche | function-calling.md |

⚠️ **Non documentato:** TTFT e tokens/s per modello, e latenza di rete dall'Italia (non c'è un endpoint EU; quello globale non garantisce la regione). Vanno misurati sul posto, con un piccolo benchmark come quello qui sotto.

### Snippet: mini-benchmark TTFT (Python, OpenAI SDK)
```python
import os, time
from openai import OpenAI
client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")

def ttft(model, effort):
    t0 = time.perf_counter()
    kwargs = {"reasoning": {"effort": effort}} if effort else {}
    stream = client.responses.create(model=model, input="Rispondi solo: ok", stream=True, store=False, **kwargs)
    first = None
    for ev in stream:
        if ev.type == "response.output_text.delta" and first is None:
            first = time.perf_counter() - t0
    return first, time.perf_counter() - t0

for model, effort in [("grok-4.3", "none"), ("grok-4.20-0309-non-reasoning", None), ("grok-4.7", "low")]:
    print(model, effort, ttft(model, effort))
```

### Snippet: pattern "comando robot" sicuro (Python, OpenAI SDK, Responses + function calling)
```python
import os, json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1", timeout=20.0)
SESSION = "robodog-session-1"
ALLOWED = {"walk", "turn", "sit", "stand", "bark"}

TOOLS = [{
    "type": "function",
    "name": "robot_action",
    "description": "Execute ONE physical action on the robot dog.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": sorted(ALLOWED)},
            "value": {"type": "number", "minimum": -1, "maximum": 1, "description": "speed or turn rate, normalized"},
            "duration_s": {"type": "number", "minimum": 0, "maximum": 3},
        },
        "required": ["action", "value", "duration_s"],
    },
}]
SYSTEM = "You control a robot dog in a museum. Be brief (Italian). Use robot_action for movement."

history = [{"role": "system", "content": SYSTEM}]

def turn(user_text, execute):
    history.append({"role": "user", "content": user_text})
    resp = client.responses.create(
        model="grok-4.3", reasoning={"effort": "none"},
        input=history, tools=TOOLS, parallel_tool_calls=False,
        store=False, prompt_cache_key=SESSION,
    )
    history.extend(resp.output)  # ripassa tutto invariato
    for item in resp.output:
        if item.type == "function_call" and item.name == "robot_action":
            args = json.loads(item.arguments)
            ok = args["action"] in ALLOWED          # validazione locale, sempre
            result = execute(args) if ok else {"error": "rejected"}
            history.append({"type": "function_call_output", "call_id": item.call_id, "output": json.dumps(result)})
            # Opzionale: una seconda chiamata per far commentare l'azione; si può saltare per la latenza
    return resp.output_text
```
⚠️ L'ho adattato dai pattern dei docs (function calling e history stateless con `store=False`) e non l'ho eseguito. Ho passato `prompt_cache_key` come kwarg diretto: `openai` 3.42.1 lo accetta, l'ho verificato dalla firma di `Responses.create`. Con versioni più vecchie va usato `extra_body={"prompt_cache_key": SESSION}`, come nei docs.

## Limiti numerici riassunti
- **Contesto:** 500k (`grok-4.7`/`4.6`/`4.5`), 1M (`grok-4.3`, `grok-4.20-*`), 256k (`grok-build-0.1`).
- **Output:** `max_output_tokens` default 128.000 (solo output visibile); per `grok-4.7` "no text output limit".
- **Immagini:** 20 MiB ciascuna, solo jpg/png, nessun limite sul numero.
- **File allegati:** 512 MB. **File nelle Collections:** 100 MB.
- **Tool:** 350 secondo la guida, 1000 secondo la reference ⚠️.
- **Web search:** al massimo 5 domini per allow/exclude. **X search:** al massimo 20 handle.
- **Responses salvate:** 30 giorni. **Connessione WebSocket:** al massimo 59 minuti.
- **Rate limit T0:** `grok-4.7` 150 RPS / 50M TPM; `grok-4.3` 37 RPS / 10M TPM.

## Fonti
- https://docs.x.ai/developers/debugging.md
- https://docs.x.ai/developers/rate-limits.md
- https://docs.x.ai/developers/model-capabilities/text/best-practices.md
- https://docs.x.ai/developers/model-capabilities/text/reasoning.md
- https://docs.x.ai/developers/advanced-api-usage/websocket-mode.md
- https://docs.x.ai/developers/advanced-api-usage/priority-processing.md
- https://docs.x.ai/developers/advanced-api-usage/prompt-caching.md (+ sotto-pagine)
- https://docs.x.ai/developers/advanced-api-usage/context-compaction.md
- https://docs.x.ai/developers/migration/may-15-retirement.md
- https://docs.x.ai/developers/pricing.md (Usage Guidelines Violation Fee)
- https://github.com/xai-org/xai-sdk-python (Timeouts / Retries)
- https://x.ai/news/grok-4-7 (footer: "SpaceX Super Intelligence LLC")
