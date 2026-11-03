# Custom Voices (voice cloning)

> Verificato il: **2026-11-03** su docs.x.ai (Custom Voices guide + API reference) e blog x.ai/news/grok-custom-voices (30 apr 2026). ⚠️ = non verificato.

## TL;DR (leggere prima di progettare il "telefono con personaggi")

1. **Disponibilità geografica**: "Custom Voices is currently only available in the **United States**, with the exception of **Illinois**." → ⚠️ dall'Italia probabilmente **non** disponibile, salvo che il team SpaceXAI all'evento abiliti l'account/team. **Chiedetelo subito al desk.**
2. **Consenso obbligatorio (console)**: il blog descrive una verifica in due fasi: *passphrase check* (lo speaker legge una frase di verifica trascritta in tempo reale) + *speaker similarity* (embedding della verifica vs registrazione). Citazione: "You can't clone a voice from a pre-existing recording, and you can't clone someone else's voice."
   → **Niente cloni di personaggi storici/celebrità da registrazioni esistenti.** Si può clonare solo la propria voce, registrata dal vivo.
3. **API di creazione** (`POST /v1/custom-voices`) **riservata ai team Enterprise** (403 altrimenti). Da console: fino a **30 voci gratis** per team.
4. Una volta creata, la voce (`voice_id` di 8 caratteri) funziona in `POST /v1/tts`, `wss://api.x.ai/v1/tts` e **`wss://api.x.ai/v1/realtime`** (Voice Agent) esattamente come una built-in. Nessun costo extra d'uso.

### Workaround per i personaggi
- **Built-in voices + persona nel prompt**: scegliere la voce built-in più adatta per ogni personaggio (provarle nella playground TTS della console) e descrivere il personaggio in `## Role & Persona`; stile del parlato in `## Voice & Communication Style` (parole, ritmo delle frasi, intercalari d'epoca). Il prompt controlla *cosa* dice, non il timbro.
- **Un membro del team "recita" il personaggio**: il modello clona timbro **e** "delivery patterns" della registrazione. Se la console è disponibile per il vostro account, un membro del team può registrare 90–120 s interpretando il personaggio (accento, ritmo) e superare la verifica con la propria voce. ⚠️ Possibile solo se la feature è abilitata per il vostro team/regione.
- Pronunce di nomi propri: `replace` (anche IPA su TTS).

## Creare una voce

### Dalla console
`https://console.x.ai/team/default/voice/voice-library` → Clone Voice → registrazione + verifica. Per copiare l'id: menu a tre puntini sulla card → **Copy Voice ID**. Il blog dice che il processo, verifica inclusa, richiede "under two minutes" e consiglia "about a minute of natural speech".

### Via API (solo Enterprise)
```bash
curl -X POST https://api.x.ai/v1/custom-voices \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -F "name=Operatore 1950" -F "language=it" -F "gender=male" -F "age=old" \
  -F "tone=warm" -F "use_case=characters" \
  -F "file=@reference.wav;type=audio/wav"
# 201 -> {"voice_id": "nlbqfwie", "name": "...", ..., "created_at": "..."}
```
| Campo | Valori |
|---|---|
| `file` (req) | max **120 s**, nessun minimo; WAV/MP3/FLAC/OGG/Opus/M4A/AAC/MKV/MP4 |
| `name`, `description`, `accent` | testo libero |
| `gender` | `male`, `female`, `neutral` |
| `age` | `young`, `middle-aged`, `old` |
| `language` | ISO 639 (`it`) o BCP-47 con regione maiuscola (`it-IT`) |
| `use_case` | `conversational`, `narration`, `characters`, `educational`, `advertisement`, `social_media`, `entertainment` |
| `tone` | `warm`, `casual`, `professional`, `friendly`, `authoritative`, `expressive`, `calm` |

⚠️ La API reference non menziona la verifica con passphrase per l'endpoint API (solo il blog la descrive per la console).

### Gestione
- `GET /v1/custom-voices?limit=..&pagination_token=..` (le custom **non** appaiono in `GET /v1/tts/voices`)
- `GET /v1/custom-voices/{voice_id}` (404 se di un altro team)
- `PATCH /v1/custom-voices/{voice_id}` solo metadati (`null` cancella, `""` → 400)
- `GET /v1/custom-voices/{voice_id}/audio` scarica il riferimento
- `DELETE /v1/custom-voices/{voice_id}` → `{"deleted": true}`
- Limite: 30 voci per team (400 al superamento).

## Requisiti audio del riferimento
| Aspetto | Raccomandazione |
|---|---|
| Durata | **90–120 s** (sotto 30 s "may lack detail") |
| Codec | WAV PCM non compresso (i lossy introducono artefatti clonati) |
| Sample rate | **24 kHz** (più alto viene ricampionato, più basso perde fedeltà) |
| Bit depth | 16-bit (24 ok) |
| Canali | mono |
| Ambiente | stanza piccola e "morbida", niente HVAC/ventole/notifiche: **il rumore viene clonato** |
| Microfono | condenser/USB di qualità; pop filter consigliato |
| Contenuto | un solo speaker, niente musica; parlare in modo naturale ed espressivo, **nello stile del caso d'uso** (il modello copia anche la "delivery") |

In un museo durante l'hackathon: registrare in un angolo tranquillo, con microfono vicino; evitare la sala con le macchine d'epoca accese.

## Usare la voce
```python
# Voice Agent realtime
await ws.send(json.dumps({"type": "session.update", "session": {"voice": "nlbqfwie", "instructions": "..."}}))
# TTS REST
requests.post("https://api.x.ai/v1/tts", headers=H, json={"text": "...", "voice_id": "nlbqfwie", "language": "it"})
# TTS streaming
"wss://api.x.ai/v1/tts?language=it&voice=nlbqfwie&codec=pcm&sample_rate=24000"
```
Dopo un DELETE, l'uso del `voice_id` fallisce con unknown-voice (TTS: 404).

## Fonti
- https://docs.x.ai/developers/model-capabilities/audio/custom-voices.md
- https://docs.x.ai/developers/rest-api-reference/inference/voice.md (sezioni `/v1/custom-voices`)
- https://docs.x.ai/developers/model-capabilities/audio/voice.md (Quick Start Custom Voices)
- https://x.ai/news/grok-custom-voices
- https://docs.x.ai/developers/release-notes.md (Custom Voices, maggio 2026)
