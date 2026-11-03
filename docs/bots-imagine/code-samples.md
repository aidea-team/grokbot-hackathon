# Code samples (Python / JS)

> Preparati e verificati il **2026-11-03**. Livello di verifica (onesto):
> - ✅ **sintassi** (`py_compile` / `node --check`)
> - ✅ **firme SDK** controllate per introspezione su `xai-sdk==1.21.0`, `xdk==0.10.6`, `openai` (ultima), `ai@7.0.162`, `@ai-sdk/xai@5.0.38`, `@xdevplatform/xdk@0.6.6`
> - ✅ **dry-run con chiave non valida**: le chiamate arrivano all'API e falliscono solo per auth (`Incorrect API key provided` / `401` / `403 unsupported-authentication`), quindi endpoint e payload sono accettati dallo schema
> - ⚠️ **Nessuna esecuzione end-to-end con chiavi reali** (non disponibili): output, tempi e costi reali da confermare all'evento.
>
> Variabili d'ambiente: `XAI_API_KEY` (console.x.ai); per X: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` (app X con permessi Read+Write, package Pay-per-use, ambiente Production).

```bash
python -m venv .venv && . .venv/bin/activate
pip install "xai-sdk==1.21.0" "xdk==0.10.6" openai requests
# JS
npm i ai@7.0.162 @ai-sdk/xai@5.0.38
```

Indice:
1. Immagine con xAI SDK
2. Image edit via REST (foto dalla camera)
3. Video con xAI SDK (polling automatico)
4. Video via REST con polling esplicito
5. Leggere X con Grok (`x_search`)
6. X API: post con immagine generata
7. X API: polling menzioni
8. Grok Bot: trigger webhook da hardware
9. Grok Build headless da Python
10. JS: immagine + video con Vercel AI SDK
11. curl di riferimento

## 1. Immagine con xAI SDK

`image_format="base64"` → `resp.image` sono i byte. Senza, `resp.url` è un URL temporaneo.

```python
# pip install xai-sdk   (verificato su xai-sdk 1.21.0)
import os
import xai_sdk

client = xai_sdk.Client(api_key=os.environ["XAI_API_KEY"])

resp = client.image.sample(
    prompt="Un cane robot che esplora un museo di computer retrò, stile poster anni '80",
    model="grok-imagine-image-2.0",
    aspect_ratio="16:9",
    resolution="1k",          # "1k" | "2k"
    quality="low",            # "low" | "medium" (omesso = auto)
    image_format="base64",    # ritorna i byte invece di un URL temporaneo
)
with open("poster.jpg", "wb") as f:
    f.write(resp.image)
print("model:", resp.model, "moderation ok:", resp.respect_moderation)
```

## 2. Image edit via REST (foto dalla camera)

Non usare `client.images.edit()` dell'SDK OpenAI: l'endpoint vuole JSON, non multipart. Con `grok-imagine-image-2.0` si possono passare fino a 5 immagini con `"images": [...]`.

```python
# pip install requests
import base64, os, requests

API = "https://api.x.ai/v1"
H = {"Authorization": f"Bearer {os.environ['XAI_API_KEY']}", "Content-Type": "application/json"}

with open("webcam.jpg", "rb") as f:          # es. frame catturato dalla camera del robot
    data_uri = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

r = requests.post(f"{API}/images/edits", headers=H, json={
    "model": "grok-imagine-image-2.0",
    "prompt": "Trasforma la scena in un dipinto a olio, mantieni le persone riconoscibili",
    "image": {"url": data_uri, "type": "image_url"},
    "response_format": "b64_json",
}, timeout=120)
r.raise_for_status()
out = r.json()["data"][0]
with open("edited.jpg", "wb") as f:
    f.write(base64.b64decode(out["b64_json"]))
print("cost ticks:", r.json().get("usage", {}).get("cost_in_usd_ticks"))
```

## 3. Video con xAI SDK (polling automatico)

`generate()` blocca finché il video è pronto (default timeout 10 min). Per non bloccare: `start()` + `get()`.

```python
# pip install xai-sdk   (il metodo generate() fa start + polling da solo)
import os
from datetime import timedelta
import xai_sdk

client = xai_sdk.Client(api_key=os.environ["XAI_API_KEY"])

video = client.video.generate(
    prompt="La camera avanza lentamente tra le vetrine, luci al neon che si accendono",
    model="grok-imagine-video-1.5",
    image_url="https://docs.x.ai/assets/api-examples/video/waterfall-still.png",  # opzionale: image-to-video
    duration=6,                 # 1-15 s
    resolution="480p",          # 480p è il default e il più veloce
    generate_audio=False,
    timeout=timedelta(minutes=10),
    interval=timedelta(seconds=5),
)
print(video.url, video.duration)   # URL temporaneo: scaricalo subito
```

## 4. Video via REST con polling esplicito

Pattern adatto a una demo: lancia la richiesta, mostra `progress`, scarica l'MP4 a `done`.

```python
# pip install requests  — flusso asincrono esplicito (start + polling)
import os, time, requests

API = "https://api.x.ai/v1"
H = {"Authorization": f"Bearer {os.environ['XAI_API_KEY']}", "Content-Type": "application/json"}

start = requests.post(f"{API}/videos/generations", headers=H, json={
    "model": "grok-imagine-video-1.5-lite",   # il più economico: $0.02/s
    "prompt": "Un drone giocattolo decolla da un tavolo e fa un giro della stanza",
    "duration": 5,
    "aspect_ratio": "9:16",
    "resolution": "480p",
}, timeout=60)
start.raise_for_status()
rid = start.json()["request_id"]

while True:
    r = requests.get(f"{API}/videos/{rid}", headers=H, timeout=60).json()
    if r["status"] == "done":
        url = r["video"]["url"]
        open("clip.mp4", "wb").write(requests.get(url, timeout=120).content)
        print("ok", url)
        break
    if r["status"] in ("failed", "expired"):
        raise SystemExit(f"video {r['status']}: {r.get('error')}")
    print("pending", r.get("progress"), "%")
    time.sleep(5)
```

## 5. Leggere X con Grok (x_search)

Nessun account X necessario. Costo: $5/1k post fetchati + token. Con l'xAI SDK Python: `from xai_sdk.tools import x_search` (date come `datetime`).

```python
# pip install openai  — Grok legge X lato server (nessun account X API necessario)
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")

resp = client.responses.create(
    model="grok-4.7",
    input="Riassumi in 3 punti cosa si dice oggi su X dell'hackathon Grok a Pavia, con link ai post.",
    tools=[{
        "type": "x_search",
        "from_date": "2026-11-04",          # YYYY-MM-DD, to_date escluso
        "to_date": "2026-11-06",
        # "allowed_x_handles": ["xai"],     # max 20, senza @
    }],
    extra_body={"max_turns": 2},            # limita i giri di ricerca (= costo)
)
print(resp.output_text)
print(resp.usage.model_dump().get("server_side_tool_usage_details"))
```

## 6. X API: post con immagine generata

Verificato che `CreateRequest(...)` e `UploadRequest(...)` serializzano a `{'text':..., 'media': {'media_ids': [...]}, 'made_with_ai': True}` e `{'media': <b64>, 'media_category': 'tweet_image'}`. Costo: $0.015/post, **$0.20 se il testo contiene un URL**. Per i video usare l'upload chunked (`initialize_upload`/`append_upload`/`finalize_upload`) o `xurl media upload clip.mp4`.

```python
# pip install xdk   (X API v2 official Python SDK, verificato su xdk 0.10.6)
# Pubblicare richiede user context: OAuth 1.0a (4 chiavi dell'app, permessi Read+Write) o OAuth 2.0 PKCE.
import base64, os
from xdk import Client
from xdk.oauth1_auth import OAuth1
from xdk.media.models import UploadRequest
from xdk.posts.models import CreateRequest
from xdk.schemas import CreatePostsMedia, CreatePostsReply

oauth1 = OAuth1(
    api_key=os.environ["X_API_KEY"],
    api_secret=os.environ["X_API_SECRET"],
    callback="http://localhost:8080/callback",
    access_token=os.environ["X_ACCESS_TOKEN"],
    access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
)
x = Client(auth=oauth1)

with open("poster.jpg", "rb") as f:
    up = x.media.upload(UploadRequest(
        media=base64.b64encode(f.read()).decode(),
        media_category="tweet_image",
    ))
media_id = up.data.id

post = x.posts.create(CreateRequest(
    text="Generato dal vivo con Grok Imagine al Ctrl+Alt Museum #GrokHackathon",
    media=CreatePostsMedia(media_ids=[media_id]),
    made_with_ai=True,
    # reply=CreatePostsReply(in_reply_to_tweet_id="1234567890"),   # per rispondere a una menzione
))
print(post)
```

## 7. X API: polling menzioni

⚠️ Le docs X mostrano `client.posts.get_user_mentions`, che non esiste in `xdk` 0.10.6: il metodo reale è `client.users.get_mentions`. ⚠️ La forma degli oggetti restituiti (attributi vs dict) non è stata provata con dati reali: lo snippet gestisce entrambi.

```python
# pip install xdk  — polling delle menzioni (alternativa economica ai webhook)
import os, time
from xdk import Client
from xdk.oauth1_auth import OAuth1

x = Client(auth=OAuth1(
    api_key=os.environ["X_API_KEY"], api_secret=os.environ["X_API_SECRET"],
    callback="http://localhost:8080/callback",
    access_token=os.environ["X_ACCESS_TOKEN"], access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
))
me = x.users.get_me().data
my_id = me.id if hasattr(me, "id") else me["id"]
since_id = None

while True:
    kwargs = {"max_results": 10}
    if since_id:
        kwargs["since_id"] = since_id
    for page in x.users.get_mentions(my_id, **kwargs):   # NB: è users.get_mentions, non posts.get_user_mentions
        for p in page.data or []:
            pid = p.id if hasattr(p, "id") else p["id"]
            text = p.text if hasattr(p, "text") else p["text"]
            print("menzione:", pid, text)
            since_id = max(since_id or pid, pid, key=int)
        break   # solo la prima pagina
    time.sleep(30)   # ogni post letto costa: le menzioni del proprio account sono "Owned Reads" ($0.001)
```

## 8. Grok Bot: trigger webhook da hardware

URL e key si copiano dalla routine (desktop app → dettagli Bot → Routines → sezione **Webhook**). La risposta HTTP non contiene il risultato: arriva nella chat del Bot.

```python
# Trigger di una routine Grok Bot da hardware/laptop (URL e key si copiano dalla sezione "Webhook" della routine)
import os, requests

r = requests.post(
    os.environ["GROKBOT_WEBHOOK_URL"],                         # campo "POST to"
    headers={"Authorization": f"Bearer {os.environ['GROKBOT_WEBHOOK_KEY']}"},  # campo "key"
    json={"event": "robot_dog_fell", "sensor": {"tilt_deg": 78}, "ts": "2026-11-04T23:10:00+01:00"},
    timeout=30,
)
print(r.status_code)   # 200 = run avviato (non concluso). Il risultato arriva nella chat del Bot.
```

## 9. Grok Build headless da Python

Richiede `grok` installato e loggato (o `XAI_API_KEY`). ⚠️ Sintassi `--allow` da confermare con `grok --help`; in alternativa definire le regole in `~/.grok/config.toml` (`[permission] rules = [...]`).

```python
# Usa Grok Build (CLI `grok`) come "programmatore" pilotato da script
import json, subprocess

res = subprocess.run(
    ["grok", "--no-auto-update", "-p",
     "Scrivi robot/patrol.py che fa camminare il cane robot in un quadrato usando robot_sdk.py; poi esegui i test",
     "--output-format", "json", "--max-turns", "20",
     "--allow", "Bash(pytest*)"],          # ⚠️ sintassi regole permessi da verificare con `grok --help`
    capture_output=True, text=True, timeout=900, cwd=".",
)
out = json.loads(res.stdout)
print(out["text"], out.get("stopReason"), out.get("usage"))
```

## 10. JS: immagine + video con Vercel AI SDK

Verificato: `generateImage`, `experimental_generateVideo`, `xai.image`, `xai.video`, `xai.responses`, `xai.tools.xSearch` esistono nelle versioni indicate; il dry-run arriva all'API (`AI_APICallError: Incorrect API key provided`).

```javascript
// npm i ai @ai-sdk/xai   (verificato con ai@7.0.162, @ai-sdk/xai@5.0.38)
import { xai } from "@ai-sdk/xai";
import { generateImage, experimental_generateVideo as generateVideo } from "ai";
import fs from "node:fs";

// 1) Immagine
const { image } = await generateImage({
  model: xai.image("grok-imagine-image-2.0"),
  prompt: "Un braccio robotico che dipinge un quadro, luce da studio",
  aspectRatio: "1:1",
});
fs.writeFileSync("arm.jpg", Buffer.from(image.base64, "base64"));

// 2) Video (l'SDK fa polling da solo)
const result = await generateVideo({
  model: xai.video("grok-imagine-video-1.5"),
  prompt: "Il braccio robotico finisce il quadro e si inchina",
  duration: 6,
  aspectRatio: "16:9",
  providerOptions: { xai: { resolution: "480p", pollTimeoutMs: 10 * 60 * 1000 } },
});
console.log(result.providerMetadata?.xai?.videoUrl);
```

## 11. curl di riferimento

```bash
# Immagine (sincrona)
curl -s https://api.x.ai/v1/images/generations \
  -H "Authorization: Bearer $XAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"grok-imagine-image-2.0","prompt":"robot dog in a retro museum","aspect_ratio":"16:9"}' \
  | jq -r '.data[0].url'

# Video (asincrono): start + poll
RID=$(curl -s https://api.x.ai/v1/videos/generations \
  -H "Authorization: Bearer $XAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"grok-imagine-video-1.5-lite","prompt":"a drone takes off from a desk","duration":5,"resolution":"480p"}' \
  | jq -r .request_id)
until [ "$(curl -s https://api.x.ai/v1/videos/$RID -H "Authorization: Bearer $XAI_API_KEY" | tee /tmp/v.json | jq -r .status)" != "pending" ]; do sleep 5; done
jq -r '.video.url // .error' /tmp/v.json

# X: ricerca recente (bearer app-only)
curl -s "https://api.x.com/2/tweets/search/recent?query=%23GrokHackathon%20-is%3Aretweet&max_results=10" \
  -H "Authorization: Bearer $X_BEARER_TOKEN"

# X: post (user context) con xurl
xurl -X POST /2/tweets -d '{"text":"Hello from Ctrl+Alt Museum"}'
```

## Fonti
- https://docs.x.ai/developers/model-capabilities/images/generation
- https://docs.x.ai/developers/model-capabilities/images/editing
- https://docs.x.ai/developers/model-capabilities/video/generation
- https://docs.x.ai/developers/rest-api-reference/inference/videos
- https://docs.x.ai/developers/tools/x-search
- https://docs.x.ai/grok-bot/skills-routines-and-automations (Webhooks)
- https://docs.x.ai/build/cli/headless-scripting
- https://docs.x.com/xdks/python/authentication
- https://docs.x.com/x-api/posts/create-post , https://docs.x.com/x-api/media/upload-media
- https://docs.x.com/x-api/posts/timelines/quickstart/user-mention-quickstart
- https://pypi.org/project/xai-sdk/ , https://pypi.org/project/xdk/ , https://www.npmjs.com/package/@ai-sdk/xai
