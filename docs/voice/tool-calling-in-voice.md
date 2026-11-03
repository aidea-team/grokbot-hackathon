# Tool / function calling nel Voice Agent

> Verificato il: **2026-11-03** (docs.x.ai Speech to Speech + schema WS + cookbook phone). ⚠️ = non verificato.

È il pezzo che collega la voce all'hardware: il modello decide di chiamare `move_robot(...)`, il vostro codice muove il cane robot / il simulatore e restituisce il risultato, il modello lo commenta a voce.

## Tipi di tool in `session.tools`

| type | Dove gira | Gestione client |
|---|---|---|
| `function` | **vostro codice** | sì: eseguire e restituire `function_call_output` |
| `web_search` | xAI | no (opz. `allowed_domains`/`excluded_domains` max 5, `location`, `enable_image_understanding`) |
| `x_search` | xAI | no (`allowed_x_handles` max 20, `from_date`/`to_date`, image/video understanding) |
| `file_search` | xAI (Collections) | no (`vector_store_ids`, `max_num_results`) |
| `mcp` | xAI chiama il vostro MCP server (Streamable HTTP o SSE) | no (`server_url`, `server_label` senza punti, `allowed_tools`, `authorization`, `headers`) |
| `function` `send_dtmf` (senza parameters) | xAI, solo SIP | no: non rispondere alle sue call |

Idea per l'hackathon: esporre il robot come **MCP server** pubblico (via ngrok) → zero codice di gestione tool nel client voce. Ma il server MCP deve essere raggiungibile da xAI (internet) e la latenza include il giro xAI → vostro server. Con `function` il tool gira in locale accanto al robot (più semplice e più veloce per una demo LAN).

## Definizione di una function

Formato **piatto** (come OpenAI Realtime; usato dalla guida e dal cookbook ufficiale funzionante):
```json
{
  "type": "function",
  "name": "move_robot",
  "description": "Make the robot dog perform a movement or trick.",
  "parameters": {
    "type": "object",
    "properties": {
      "action": {"type": "string", "enum": ["sit", "stand", "walk_forward", "turn_left", "turn_right", "wave", "dance"]},
      "duration_s": {"type": "number", "description": "Duration in seconds"}
    },
    "required": ["action"]
  }
}
```
⚠️ Lo schema JSON `voice-realtime.ws.json` descrive invece `{"type":"function","function":{"name","description","parameters"}}` (annidato). Guida e cookbook usano il formato piatto: usate quello; se ricevete `error` su `session.update`, provate l'annidato.

## Flusso

1. Server → `response.function_call_arguments.done` con `call_id`, `name`, `arguments` (stringa JSON). (In alternativa `response.output_item.done` con `item.type == "function_call"`: lo usa il cookbook phone. **Scegliete uno dei due**, non entrambi, o eseguirete il tool due volte.)
2. Eseguite il tool.
3. Client → `conversation.item.create` con `{"type": "function_call_output", "call_id": ..., "output": "<stringa JSON>"}` (non fatturato come text input).
4. Client → `response.create` perché l'agente continui a parlare.

### Parallel tool calls
Il modello può emettere **più** `function_call_arguments.done` nella stessa risposta, prima dell'audio. Regola ufficiale: inviare **tutti** i `function_call_output`, poi **un solo** `response.create`. Pattern robusto (usato negli esempi di questa cartella): accumulare le call fino a `response.done`, poi eseguire e rispondere.

### Evitare audio sovrapposto
"Il server invia tutti i delta audio prima, poi gli eventi function call insieme a `response.done`." Se mandate subito `response.create`, la nuova risposta parte mentre state ancora riproducendo la frase precedente ("Ok, ci penso io!"). Raccomandazione ufficiale:
1. ricevere la call → eseguire
2. inviare `function_call_output`
3. **aspettare la fine della riproduzione locale** (browser: `audioContext.currentTime >= playhead`; Twilio: usare `mark` e attendere l'eco)
4. poi `response.create`.

## Codice minimo (Python)
```python
pending = []
async for raw in ws:
    ev = json.loads(raw)
    if ev["type"] == "response.function_call_arguments.done":
        pending.append(ev)
    elif ev["type"] == "response.done" and pending:
        calls, pending = pending, []
        for c in calls:
            result = await asyncio.to_thread(run_tool, c["name"], json.loads(c["arguments"] or "{}"))
            await ws.send(json.dumps({"type": "conversation.item.create", "item": {
                "type": "function_call_output", "call_id": c["call_id"], "output": json.dumps(result)}}))
        await wait_playback()                       # vedi sopra
        await ws.send(json.dumps({"type": "response.create"}))
```
Esempio completo testato contro mock: [examples/voice_agent_local.py](examples/voice_agent_local.py).

## Consigli di prompting per i tool (guida ufficiale)
- Nominare nel prompt **solo** tool presenti in `tools`; nomi brevi snake_case; descrizioni coerenti con lo schema.
- Preambolo per mascherare la latenza: "Before any tool call, say one short line such as 'Subito!' then call the tool immediately." Oppure frasi specifiche nella `description` del tool.
- Tool read-only: chiamarli senza chiedere conferma; tool che cambiano lo stato (es. "corri verso il pubblico"): chiedere conferma.
- Blog Voice 2.0: "Tool calls usually finish before the agent's first sentence ends" e il modello "reason while speaking".

## Pattern utili per l'hackathon
- **Stato del mondo → voce**: iniettare telemetria del simulatore come testo (`conversation.item.create` role `user` o `system` + `response.create`), oppure con `response.create.response.instructions` (override per un turno). Ogni `conversation.item.create` testuale costa $0.004.
- **Tool lunghi** (il cane impiega 5 s a sedersi): restituire subito `{"status": "started"}` e notificare il completamento con un nuovo item testuale, invece di bloccare la conversazione. ⚠️ Pattern nostro, non documentato.
- **Sicurezza hardware**: validare sempre gli argomenti (enum, range) prima di muovere il robot; il modello può allucinare parametri.
- Seed della history con `function_call` + `function_call_output` creati dal client (supportato da `conversation.item.create`) per ripristinare contesto dopo reconnect senza resumption.

## Fonti
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech.md (sezioni "Using Tools", "Handling Function Call Responses", "Parallel Tool Calling", "Avoid Audio Overlap During Tool Calls")
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech/prompting-guide.md (sezione Tools)
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech/sip.md (`send_dtmf`)
- https://docs.x.ai/voice-realtime.ws.json
- https://docs.x.ai/developers/tools/remote-mcp.md
- https://github.com/xai-org/xai-cookbook/blob/main/examples/voice-agent-phone/xai/src/index.ts
- https://x.ai/news/grok-voice-think-fast-2
