# Vision (image understanding)

> **Verificato il:** 2026-11-03 su docs.x.ai e negli esempi di xai-sdk-python e xai-sdk-ts.
> ⚠️ Snippet non eseguiti contro l'API.

## Cosa supporta
- **Tutti** i modelli di testo attuali accettano immagini in input: `grok-4.7`, `4.6`, `4.5`, `4.3`, `4.20-*`, `grok-build-0.1` (modalità "text, image → text"). L'output è solo testo.
- **Formati:** `jpg/jpeg` e `png`. ⚠️ Il README dell'SDK TS dice che rileva anche WebP dai byte, ma i docs API elencano solo jpg e png. Per sicurezza conviene usare JPEG.
- **Dimensione massima:** 20 MiB per immagine. **Numero di immagini:** nessun limite. Testo e immagini possono stare in qualsiasi ordine.
- **Sorgente:** URL pubblico oppure data URL base64 (`data:image/jpeg;base64,...`).
- **`detail`:** `"auto"` (default), `"low"` (più veloce e meno token) o `"high"` (più dettaglio, più lento e più caro).
- ⚠️ **Il costo in token per immagine** (risoluzione, tiling) **non è documentato**. Si legge a posteriori in `usage` (`prompt_image_tokens` con xai-sdk, `image_tokens` con Chat Completions).
- ⚠️ La pagina Image Understanding avverte: *"When sending images, it is advised to not store request/response history on the server. Otherwise the request may fail."* → con le immagini usare **`store: false`**.

## Formati del messaggio

**Responses API**
```json
{"role": "user", "content": [
  {"type": "input_image", "image_url": "data:image/jpeg;base64,<...>", "detail": "low"},
  {"type": "input_text", "text": "What is in front of the robot?"}
]}
```

**Chat Completions (legacy)**
```json
{"role": "user", "content": [
  {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,<...>", "detail": "high"}},
  {"type": "text", "text": "What is in this image?"}
]}
```

## Python, OpenAI SDK, frame della webcam in base64
```python
import base64, os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")

with open("frame.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

response = client.responses.create(
    model="grok-4.3",                 # per la latenza; grok-4.7 per la qualità
    reasoning={"effort": "none"},     # solo grok-4.3 accetta "none"
    store=False,
    input=[{
        "role": "user",
        "content": [
            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}", "detail": "low"},
            {"type": "input_text", "text": "Describe obstacles in front of the robot in one sentence."},
        ],
    }],
)
print(response.output_text)
```
(La struttura `input_image`/`input_text` e il data URL vengono dai docs. La combinazione `grok-4.3` + `effort: "none"` + `detail: "low"` è un mio adattamento per ridurre la latenza.)

## Python, xai-sdk
```python
import base64
from xai_sdk import Client
from xai_sdk.chat import user, image

client = Client()
b64 = base64.b64encode(open("frame.jpg", "rb").read()).decode("utf-8")

chat = client.chat.create(model="grok-4.7", store_messages=False)
chat.append(user(
    "What kind of object is this?",
    image(f"data:image/jpeg;base64,{b64}", detail="low"),
))
response = chat.sample()
print(response.content, response.usage.prompt_image_tokens)
```
Firma verificata: `image(image_url: str, *, detail: Literal['auto','low','high'] = 'auto')`.

## JS/TS, OpenAI SDK
```javascript
import fs from "node:fs";
import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.XAI_API_KEY, baseURL: "https://api.x.ai/v1" });
const b64 = fs.readFileSync("frame.jpg").toString("base64");

const response = await client.responses.create({
  model: "grok-4.7",
  store: false,
  input: [{
    role: "user",
    content: [
      { type: "input_image", image_url: `data:image/jpeg;base64,${b64}`, detail: "low" },
      { type: "input_text", text: "What's in this image?" },
    ],
  }],
});
console.log(response.output_text);
```

## TS, `@xai-official/sdk` (sperimentale): passa direttamente un Blob
```ts
import { readFile } from "node:fs/promises";
import { SpaceXSI } from "@xai-official/sdk";

const client = new SpaceXSI();
const bytes = new Uint8Array(await readFile("./frame.png"));
const response = await client.responses.create({
  model: "grok-4.7",
  input: [{ role: "user", content: [
    { type: "input_text", text: "What is in this image?" },
    { type: "input_image", image: new Blob([bytes], { type: "image/png" }) },
  ]}],
});
console.log(response.toText());
```

## Consigli per camera/robot
- Ridimensionare il frame prima di inviarlo, per esempio a 640–1024 px sul lato lungo, in JPEG con qualità 70–85, e usare `detail: "low"` quando non servono dettagli fini. ⚠️ È un'euristica mia: la risoluzione interna usata dal modello non è documentata.
- Mandare un frame solo quando serve (evento o richiesta dell'utente), non in streaming continuo. Le immagini aggiungono token e latenza.
- Per i video da X o le immagini trovate sul web esistono i tool server-side `view_image` e `view_x_video`, ma riguardano **solo** media trovati dalle ricerche (vedi [agentic-server-tools.md](agentic-server-tools.md)).

## Fonti
- https://docs.x.ai/developers/model-capabilities/images/understanding.md
- https://docs.x.ai/developers/model-capabilities/legacy/chat-completions.md (sezione Image understanding / detail levels)
- https://docs.x.ai/developers/models.md (limiti delle immagini in input)
- https://github.com/xai-org/xai-sdk-python/blob/main/examples/sync/image_understanding.py
- https://github.com/xai-org/xai-sdk-ts (README, "Image input")
