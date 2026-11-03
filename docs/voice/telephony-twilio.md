# Telefonia: Twilio Media Streams e SIP diretto

> Verificato il: **2026-11-03** su docs.x.ai (SIP Phone Calls), cookbook `voice-agent-phone/xai` (commit `002788b`) e docs Twilio Media Streams. ⚠️ = non verificato.

Due strade per "chiamare il cane robot":

| | A) Twilio Media Streams + vostro bridge | B) SIP diretto verso xAI |
|---|---|---|
| Come | Twilio apre un WebSocket verso il vostro server, che inoltra a `wss://api.x.ai/v1/realtime` | Il carrier (Twilio Elastic SIP Trunking, Telnyx, ...) manda la chiamata a `sip.voice.x.ai`; xAI vi notifica via webhook; voi vi agganciate con `?call_id=` |
| Audio | μ-law 8 kHz passthrough (`audio/pcmu`) | gestito da xAI (bridge SIP) |
| Tool / hardware | nel bridge | nella vostra WS `?call_id=` (stesso protocollo) |
| Extra | controllo totale, barge-in con `clear` | DTMF nativo, `send_dtmf`, transfer (`refer`), `hangup` via REST |
| Setup | ngrok + webhook TwiML: **più veloce per l'hackathon** | registrazione numero `POST /v2/phone-numbers` (BYO trunk), webhook firmato, config trunk |
| Esempio ufficiale | sì (Node/TS) + porting Python in questa cartella | solo snippet doc |

**Consiglio hackathon: strada A.** Codice: [examples/twilio_bridge.py](examples/twilio_bridge.py) (porting Python del cookbook, testato con Twilio finto + xAI mock).

---

## A) Twilio Media Streams (passo passo)

### 1. Prerequisiti
- Account Twilio con un numero **Voice**.
  - ⚠️ **Numeri italiani**: Twilio richiede un *Regulatory Bundle* (documento d'identità, spesso indirizzo/partita IVA), revisione tipicamente giorni → non fattibile entro domani. Alternativa rapida: comprare un **numero USA** (acquisto immediato) e chiamarlo dall'Italia (chiamata internazionale), oppure usare Twilio **Client/WebRTC** o il "Call" del Twilio Console dal browser. ⚠️ Verificare costi e disponibilità sul proprio account.
  - ⚠️ Account **trial**: le chiamate in uscita vanno solo a numeri verificati e Twilio antepone un messaggio "trial account" alle chiamate. Fare upgrade (bastano pochi $) prima della demo.
- `XAI_API_KEY`, Python 3.10+ (o Node 18+ per l'esempio ufficiale), `ngrok`.

### 2. Avviare il bridge
```bash
pip install fastapi "uvicorn[standard]" "websockets>=14"
export XAI_API_KEY=xai-...
ngrok http 3000                                  # copia l'host https, es. abcd-1234.ngrok-free.app
export PUBLIC_HOST=abcd-1234.ngrok-free.app      # senza https://
uvicorn twilio_bridge:app --host 0.0.0.0 --port 3000
```
(Esempio ufficiale Node: `cd examples/voice-agent-phone/xai && npm install && cp .env.example .env && npm run dev`, con `XAI_API_KEY` e `HOSTNAME` nel `.env`.)

### 3. Collegare il numero
Twilio Console → **Phone Numbers → Manage → Active Numbers** → numero → sezione **Voice**:
- *A call comes in*: **Webhook**, URL `https://<PUBLIC_HOST>/twiml`, metodo **POST** → Save.

Il webhook risponde con TwiML:
```xml
<Response>
  <Connect>
    <Stream url="wss://<PUBLIC_HOST>/media-stream" />
  </Connect>
</Response>
```
`<Connect><Stream>` = stream **bidirezionale** (requisito per rimandare audio al chiamante e per `mark`/`clear`).

### 4. Cosa fa il bridge
| Twilio → bridge | Azione verso xAI |
|---|---|
| `connected`, `start` (`start.streamSid`, `callSid`, `mediaFormat audio/x-mulaw 8000`) | salva `streamSid` |
| `media` (track `inbound`, `payload` base64 μ-law) | `input_audio_buffer.append` con lo stesso payload (solo dopo `session.updated`) |
| `mark` (eco) | l'audio prima del mark è stato riprodotto → ok per `response.create` post-tool |
| `stop` | chiude la WS xAI |

| xAI → bridge | Azione verso Twilio |
|---|---|
| `conversation.created` | `session.update` con `audio.input/output.format.type = "audio/pcmu"`, `turn_detection: server_vad`, tools |
| `session.updated` | `response.create` (l'agente risponde al telefono per primo) |
| `response.output_audio.delta` | `{"event":"media","streamSid":..,"media":{"payload": delta}}` (già μ-law base64, **nessuna conversione**) |
| `input_audio_buffer.speech_started` | `{"event":"clear","streamSid":..}` → barge-in |
| `response.function_call_arguments.done` + `response.done` | esegue il tool (robot), `function_call_output`, attende il `mark`, `response.create` |

Requisiti Twilio sull'audio in uscita: "must be encoded `audio/x-mulaw` with a sample rate of `8000` and must be base64 encoded", senza header di file.

### 5. Chiamata in uscita (il robot chiama voi)
Dal cookbook:
```bash
curl -X POST https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Calls.json \
  --data-urlencode "Url=https://<PUBLIC_HOST>/twiml" \
  --data-urlencode "To=+39..." --data-urlencode "From=$TWILIO_PHONE_NUMBER" \
  -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN
```
Per l'outbound il cookbook fa parlare l'agente per primo con un `response.create` subito dopo `session.updated`.

### 6. Varianti utili
- **Personaggi diversi per numero/chiamata**: TwiML `<Stream url="..."><Parameter name="character" value="leonardo"/></Stream>` → arriva in `start.customParameters`; scegliere `voice`/`instructions` di conseguenza (⚠️ non incluso nell'esempio: aggiungere la lettura di `customParameters` prima del `session.update`).
- **Riattaccare** dal bot: serve la REST API Twilio (update della call con TwiML `<Hangup/>`) usando `callSid` dallo `start`. ⚠️ non incluso.
- **DTMF** su Media Streams: Twilio invia eventi `dtmf` (solo bidirezionale); il bridge può trasformarli in testo per il modello. Su SIP diretto è nativo.
- Sicurezza: validare la firma `X-Twilio-Signature` sul webhook (non fatto nell'esempio).

---

## B) SIP diretto verso xAI

1. **Registrare il numero** (proprio, su un trunk vostro):
   ```bash
   curl -X POST https://api.x.ai/v2/phone-numbers -H "Authorization: Bearer $XAI_API_KEY" \
     -H "Content-Type: application/json" -d '{
       "origin": "byo_trunk", "name": "Cane robot", "phone_number": "+1XXXXXXXXXX",
       "sip_auth": {"allowed_addresses": ["<CIDR del carrier>"]},
       "webhook": {"url": "https://<PUBLIC_HOST>/xai-webhook"}}'
   ```
   Risposta: `phone_number.sip_host` (`sip.voice.x.ai`), `webhook.dispatch_signing_secret` (**mostrato una sola volta**). Il provisioning di numeri xAI via API non è supportato.
2. **Instradare il trunk** verso `sip:{number}@sip.voice.x.ai;transport=tls` (TLS 5061; TCP/UDP 5060).
   - **Twilio**: Voice → Elastic SIP Trunking → crea trunk → *Origination* URI `sip:{number}@sip.voice.x.ai;transport=tls` → assegna il numero; abilita call transfer se serve.
   - Telnyx / Bandwidth / Plivo / PBX: istruzioni nella doc.
3. **Webhook** `realtime.call.incoming` (firmato Standard Webhooks: header `webhook-id`, `webhook-timestamp`, `webhook-signature`) con `data.call_id` e `sip_headers` (From/To).
4. **Agganciarsi alla chiamata**: `wss://api.x.ai/v1/realtime?call_id={call_id}` con **API key** (no ephemeral), poi `session.update` + `response.create`.
5. Controllo chiamata: `POST /v1/realtime/calls/{call_id}/refer` `{"target_uri": "tel:+39..."}` (sincrono: 200 = risposto, 502 rifiutato, 504 timeout), `POST /v1/realtime/calls/{call_id}/hangup`.
6. DTMF: cifre bufferizzate e passate al modello come testo su `#`, 2.5 s di idle o quando l'utente parla; evento `input_audio_buffer.dtmf_event_received`. Tool `{"type":"function","name":"send_dtmf"}` per far premere tasti all'agente.
7. Rimuovere: `DELETE /v2/phone-numbers/{phone_number_id}` (204).

⚠️ Strada B non testata end-to-end; richiede un numero su un trunk SIP già configurato.

## Telefono d'epoca SENZA telefonia
Per un telefono a disco del museo non serve Twilio: cornetta collegata a una **scheda audio USB** (capsula microfonica + auricolare) su laptop/Raspberry, gancio come interruttore (GPIO o tasto USB) → `examples/voice_agent_local.py` con `--rate 16000`/`48000` a seconda della scheda. Cornetta = microfono e auricolare separati e vicini all'orecchio → poco eco, si può tentare `--full-duplex`. Alzata della cornetta = apri sessione + `force_message`/saluto; riaggancio = chiudi sessione (si paga la durata con server_vad).

## Fonti
- https://docs.x.ai/cookbook/examples/voice-agent-phone.md
- https://github.com/xai-org/xai-cookbook/tree/main/examples/voice-agent-phone/xai (src/index.ts, src/twilio.ts)
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech/sip.md
- https://docs.x.ai/developers/rest-api-reference/inference/voice.md (`/v2/phone-numbers`, `/v1/realtime/calls/*`)
- https://www.twilio.com/docs/voice/media-streams/websocket-messages
- https://www.twilio.com/docs/voice/media-streams
- https://www.twilio.com/en-us/guidelines/regulatory (Italia: numeri regolamentati)
