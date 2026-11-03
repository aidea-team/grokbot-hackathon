# Gotchas (cose che ci faranno perdere tempo domani)

> Verificato il: **2026-11-03**. Ogni punto indica la fonte; ⚠️ = esperienza generale / non verificato su Grok.

## Account, accesso, limiti
1. **Custom Voices solo USA (esclusa l'Illinois)** e verifica del consenso con passphrase: niente cloni di personaggi da registrazioni esistenti. API di creazione solo Enterprise. → Pianificare i personaggi con voci built-in. Chiedere al team SpaceXAI se abilitano la feature per l'evento. *(custom-voices docs, blog)*
2. **Concorrenza Tier 0 = 10 sessioni realtime** per team. Se più demo/membri usano la stessa key, si arriva al limite. *(rate-limits)*
3. **Con `server_vad` si paga la durata della sessione**, silenzi inclusi ($0.08/min = $4.80/h). Una sessione lasciata aperta 8 ore in museo = ~$38. Aprire la sessione quando qualcuno alza la cornetta / preme il pulsante; `idle_timeout_ms` o un timer nostro per chiuderla. *(models/speech-to-speech)*
4. **Max 120 minuti** per sessione → errore `max_duration`. Riconnettere con `conversation_id` + `resumption.enabled` (history tenuta 30 min). *(models/speech-to-speech, S2S docs)*
5. Ogni `conversation.item.create` testuale costa $0.004 (non i `function_call_output`). Telemetria del simulatore iniettata 10 volte al secondo = $0.04/s: aggregare. *(models/speech-to-speech)*
6. Server in **us-east-1**: da Pavia c'è RTT transatlantico (~100 ms ⚠️ stima) su ogni scambio. Aprire la WebSocket in anticipo, non al momento del bisogno. *(models pages)*
7. L'endpoint "US data residency" **non** serve le voice API: usare `api.x.ai`. *(regions)*

## Connessione e protocollo
8. **Non mandare audio prima di `session.updated`**: il formato (es. μ-law) non è ancora applicato. *(cookbook phone/web)*
9. **~1 connessione su 10 si apre e non manda mai `session.created`** (osservato dal cookbook live-interpreter, sia con token sia con API key). Timeout 5 s + retry (con token nuovo: un token = una sessione). Già implementato negli esempi.
10. Con ephemeral token arriva prima un `session.updated` con le impostazioni del token (senza instructions): aspettare quello con le vostre `instructions`. *(cookbook live-interpreter)*
11. **Impostare sempre `turn_detection: {"type": "server_vad"}`** esplicitamente: la doc lo presenta come l'automatismo, ma il cookbook dice "Turn detection is off by default". Senza, l'agente non risponde mai all'audio. ⚠️ incoerenza documentale.
12. Formato tool: usare quello piatto `{type, name, description, parameters}` (guida + cookbook); lo schema JSON mostra un formato annidato `function:{...}`. ⚠️
13. Function call: gestire **o** `response.function_call_arguments.done` **o** `response.output_item.done` (type `function_call`), non entrambi → doppia esecuzione (doppio movimento del robot!).
14. Parallel tool calls: un solo `response.create` dopo **tutti** i `function_call_output`. *(S2S docs)*
15. Gestire sia `response.text.delta` sia `response.output_text.delta`; per l'audio sia `response.output_audio.delta` sia l'alias `response.audio.delta`. *(API reference)*
16. Libreria Python `websockets`: dalla 14 `websockets.connect` usa `additional_headers=`; con versioni vecchie (legacy) il parametro era `extra_headers=` → `TypeError`. Usare `from websockets.asyncio.client import connect` e `websockets>=14`. ⚠️ esperienza libreria.
17. Lingua: spagnolo/portoghese vogliono la regione nel `language_hint` (`es-ES`), codici sconosciuti ignorati **in silenzio**. Per noi `"it"` va bene. *(S2S docs)*
18. ⚠️ Cambiare `voice` a metà sessione non è documentato: per cambiare personaggio, aprire una nuova sessione (pre-aprirla in parallelo per non avere attesa).
19. Mai mettere la API key nel browser/app: ephemeral token. Ephemeral token non funziona per SIP `call_id`. Per TTS/STT non esistono token effimeri documentati → proxy server. *(ephemeral tokens, TTS docs)*

## Audio, eco, interruzioni
20. **Eco con casse aperte**: senza echo cancellation il microfono riprende la voce di Grok → il server VAD la scambia per l'utente → l'agente si interrompe da solo o "si risponde". Opzioni in ordine di robustezza:
    - **Cuffie / cornetta del telefono** (mic e altoparlante separati): full-duplex ok.
    - **Speakerphone USB da conferenza con AEC hardware** ⚠️ (es. categoria Jabra Speak / Anker PowerConf) → full-duplex.
    - Browser: `getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}})` (AEC software del browser funziona solo se il playback passa dallo stesso browser).
    - Linux: modulo AEC di PulseAudio/PipeWire (`module-echo-cancel`) ⚠️.
    - **Half-duplex** (fallback sicuro, usato dal cookbook live-interpreter): non inviare microfono mentre l'agente parla + 300 ms di coda. Si perde il barge-in. Default in `voice_agent_local.py`.
21. **Barge-in lato client è obbligatorio**: l'audio arriva più veloce del tempo reale, quindi alla `speech_started` bisogna svuotare il buffer locale (browser: stop delle sorgenti; Twilio: `clear`). Altrimenti l'agente "continua a parlare" per secondi dopo l'interruzione. *(cookbook)*
22. Dopo un barge-in, inviare `conversation.item.truncate` con i ms effettivamente riprodotti, altrimenti il modello crede di aver detto tutta la frase. *(schema)*
23. **Audio sovrapposto dopo un tool**: aspettare la fine della riproduzione prima del `response.create`. *(S2S best practices)*
24. Rumore del museo (macchine d'epoca, folla): microfono direzionale vicino alla bocca; `keyterms` per i nomi propri; prompt "If the input is unclear, ask a short clarification". Non ci sono soglie VAD documentate per il realtime. ⚠️
25. Sample rate: molte schede USB non aprono 24 kHz → `--rate 48000` (l'API accetta 8k–48k PCM); ricordarsi di usare lo **stesso** rate per output e playback.
26. Safari: `AudioContext` va creato nel click handler; i codec raw TTS non si riproducono con `<audio>`. *(TTS docs)*
27. Chunk da 100 ms (consigliato). Chunk troppo grandi aumentano la latenza percepita.
28. Twilio: audio in uscita deve essere μ-law 8 kHz base64 senza header; usare `audio/pcmu` in **entrambe** le direzioni della sessione per passthrough puro. *(Twilio docs, cookbook)*

## Twilio / telefonia
29. Numeri italiani Twilio richiedono un regulatory bundle (giorni). Usare un numero USA o Twilio dal browser. ⚠️ *(Twilio regulatory)*
30. Account trial: messaggio "trial" prima della chiamata e solo numeri verificati. ⚠️
31. ngrok free cambia host a ogni avvio → aggiornare webhook Twilio e `PUBLIC_HOST`. Il TwiML deve puntare a `wss://` (non `ws://`).
32. Il Wi-Fi del museo potrebbe bloccare WebSocket/porte: avere un hotspot 4G/5G di backup. ⚠️

## Latenza: cosa aspettarsi e come ridurla
- Ufficiale: "under one second" (Voice 3.0); TTFA 0.70 s (Voice 2.0, blog); cookbook: 0.7–1 s dalla fine del parlato.
- Leve: connessione pre-aperta; parallel init (mic + WS insieme, bufferizzare l'audio iniziale); stesso formato in/out; `reasoning.effort: "none"` per compiti semplici; preambolo vocale prima dei tool; prompt "1–2 short sentences"; `audio.output.speed` > 1 per personaggi rapidi.

## Fonti
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech.md
- https://docs.x.ai/developers/model-capabilities/audio/custom-voices.md · https://x.ai/news/grok-custom-voices
- https://docs.x.ai/developers/rate-limits.md · https://docs.x.ai/developers/pricing.md
- https://docs.x.ai/llms-full.txt (`/developers/models/speech-to-speech`)
- https://docs.x.ai/developers/advanced-api-usage/regions.md
- https://github.com/xai-org/xai-cookbook/tree/main/examples/live-interpreter (README + public/index.html)
- https://github.com/xai-org/xai-cookbook/tree/main/examples/voice-agent-phone/xai
- https://www.twilio.com/docs/voice/media-streams/websocket-messages
- https://www.twilio.com/en-us/guidelines/regulatory
- https://x.ai/news/grok-voice-3 · https://x.ai/news/grok-voice-think-fast-2
