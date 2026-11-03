# Function calling e structured outputs

> **Verificato il:** 2026-11-03 su docs.x.ai, OpenAPI spec e codice di `xai-sdk==1.21.0` (firme ispezionate in locale).
> ⚠️ Snippet tratti dai docs ufficiali e **non eseguiti** contro l'API (non avevo una key).

## Function calling: il formato

Il formato **cambia tra Responses API e Chat Completions**, e Claude Code tende a confonderli.

**Responses API (raccomandata): tool "piatto"**
```json
{
  "type": "function",
  "name": "move_robot",
  "description": "Move the robot dog",
  "parameters": {
    "type": "object",
    "properties": {
      "direction": {"type": "string", "enum": ["forward", "back", "left", "right"]},
      "meters": {"type": "number", "minimum": 0, "maximum": 2}
    },
    "required": ["direction", "meters"]
  }
}
```
Nell'output la chiamata è un item `{"type": "function_call", "name", "arguments" (stringa JSON), "call_id"}`. Il risultato si rimanda così: `{"type": "function_call_output", "call_id": ..., "output": "<stringa>"}`.

**Chat Completions (legacy): tool annidato**
```json
{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
```
La chiamata arriva in `message.tool_calls[]` con `tc.function.name`, `tc.function.arguments` e `tc.id`. Il risultato si rimanda con `{"role": "tool", "tool_call_id": tc.id, "content": "..."}`.

### Regole sullo schema dei parametri
- La radice di `parameters` **deve** essere `"type": "object"`, oppure un `anyOf`/`oneOf` in cui ogni ramo è un object. Altrimenti si riceve un **400** che nomina il tool.
- Gli argomenti generati rispettano **sempre** lo schema: `strict` è implicitamente `true`. Valgono le stesse regole JSON Schema degli structured outputs (vedi sotto).
- `description` è opzionale, ma serve molto al modello per scegliere il tool giusto.
- ⚠️ Il limite sul numero di tool non è coerente: la guida Function Calling dice "max 350 tools per request", la reference API dice "max 1000". Conviene restare sotto i 350.

### `tool_choice`
| Valore | Effetto |
|---|---|
| `"auto"` (default) | il modello decide |
| `"required"` | almeno un tool deve essere chiamato |
| `"none"` | nessun tool |
| Responses: `{"type": "function", "name": "move_robot"}` | forza un tool specifico (schema `ModelToolChoice` dell'OpenAPI) |
| Chat Completions: `{"type": "function", "function": {"name": "move_robot"}}` | forza un tool specifico |
| xai-sdk: `tool_choice=required_tool("move_robot")` (`from xai_sdk.chat import required_tool`) | forza un tool specifico |

⚠️ La tabella nella guida Function Calling mostra solo la forma annidata (Chat Completions). Per la Responses API l'OpenAPI indica invece la forma piatta `{type, name}`.

### Parallel tool calls
Sono attive di default: il modello può chiedere più chiamate nella stessa risposta, e vanno eseguite **tutte** prima di continuare. Per disattivarle: `parallel_tool_calls: false`. Su un robot fisico può essere utile avere una sola azione per turno.

### Streaming
Con `stream: true` la function call arriva **completa in un unico chunk**.

## Snippet: tool loop con la Responses API (Python, OpenAI SDK)
```python
import os, json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")

tools = [{
    "type": "function",
    "name": "get_temperature",
    "description": "Get current temperature for a location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "fahrenheit"},
        },
        "required": ["location"],
    },
}]

response = client.responses.create(
    model="grok-4.7",
    input=[{"role": "user", "content": "What is the temperature in San Francisco?"}],
    tools=tools,
)

for item in response.output:
    if item.type == "function_call":
        args = json.loads(item.arguments)
        result = {"location": args["location"], "temperature": 59, "unit": args.get("unit", "fahrenheit")}
        response = client.responses.create(
            model="grok-4.7",
            input=[{"type": "function_call_output", "call_id": item.call_id, "output": json.dumps(result)}],
            tools=tools,
            previous_response_id=response.id,
        )

print(response.output_text)
```
⚠️ L'esempio ufficiale gestisce bene una sola function call. Se ce ne sono più di una in parallelo, bisogna raccogliere **tutti** i `function_call_output` e inviarli in **una sola** richiesta successiva. In alternativa si può impostare `parallel_tool_calls=False`.

Variante **stateless**, cioè senza `previous_response_id` e con `store=False`, consigliata dalla best practice: si accumula `input += response.output + [function_call_output...]` e si rimanda tutto l'input. Così il reasoning cifrato resta nella history.

## Snippet: xai-sdk (Python)
```python
import os, json
from xai_sdk import Client
from xai_sdk.chat import user, tool, tool_result

client = Client(api_key=os.getenv("XAI_API_KEY"))
tools = [tool(
    name="get_temperature",
    description="Get current temperature for a location",
    parameters={
        "type": "object",
        "properties": {"location": {"type": "string"}},
        "required": ["location"],
    },
)]

chat = client.chat.create(model="grok-4.7", tools=tools)
chat.append(user("What is the temperature in San Francisco?"))
response = chat.sample()

while response.tool_calls:
    chat.append(response)
    for tc in response.tool_calls:
        args = json.loads(tc.function.arguments)
        chat.append(tool_result(json.dumps({"temperature": 15, "unit": "celsius"})))
    response = chat.sample()

print(response.content)
```
Firme verificate su `xai-sdk 1.21.0`: `tool(name, description, parameters)`, `tool_result(result: str, tool_call_id: str | None = None)`. Con chiamate parallele conviene passare `tool_call_id=tc.id`.

Con Pydantic: `parameters=MyArgs.model_json_schema()` funziona sia con l'SDK OpenAI sia con xai-sdk.

## Snippet: TypeScript (Vercel AI SDK, il loop lo gestisce l'SDK)
```javascript
import { xai } from '@ai-sdk/xai';
import { generateText, tool, stepCountIs } from 'ai';
import { z } from 'zod';

const { text } = await generateText({
  model: xai.responses('grok-4.7'),
  tools: {
    getTemperature: tool({
      description: 'Get current temperature for a location',
      inputSchema: z.object({ location: z.string() }),
      execute: async ({ location }) => ({ location, temperature: 15, unit: 'celsius' }),
    }),
  },
  stopWhen: stepCountIs(5),
  prompt: 'What is the temperature in San Francisco?',
});
console.log(text);
```

## Structured outputs

Ci sono due strade:
1. **`response_format` / `text.format` con `json_schema`**: l'output viene garantito conforme allo schema, se lo schema usa feature supportate. Esistono anche `json_object` (JSON qualsiasi purché valido) e `text`.
2. **Tool calling**: gli argomenti sono sempre strict.

Tutti i modelli 4.x attuali supportano gli structured outputs, anche insieme ai tool (function o server-side).

### Supporto JSON Schema (sottoinsieme)
- **Supportati:** `string`, `number`, `integer`, `boolean`, `null`, `enum`, `const`, `array`, `object`, `anyOf`, `oneOf` (si comporta come `anyOf`), `allOf` (una sola sotto-schema), `$ref`/`$defs` (non circolari). Draft 2020-12 è preferito, Draft-07 è accettato.
- **`additionalProperties` è `false` di default.** Per permettere chiavi extra va messo `true` esplicitamente.
- Per un campo nullable: `{"type": ["string", "null"]}`. I campi non presenti in `required` sono opzionali.
- **`format` imposto:** `date`, `time`, `date-time`, `email`, `uuid`, `ipv4`, `ipv6`, `uri`.
- **Vincoli garantiti fino a:** min/maxLength 2048, min/maxItems 256, min/maxProperties 64, min/max numerici senza limite.
- **Best effort, non garantiti:** `not`, `if/then/else`, `allOf` con più sotto-schemi, altri `format`.
- **Errore 400:** `enum`/`anyOf` vuoti, proprietà con schema `true`/`false`, `minContains`/`maxContains`, `items` come array (va usato `prefixItems`).
- **Regex `pattern`:** sottoinsieme ECMAScript, ancorato implicitamente a tutta la stringa. Non supporta backreference, `\b`, lookahead/lookbehind, `\p{}` né flag inline.

### Python, OpenAI SDK, Responses (`responses.parse`)
```python
from pydantic import BaseModel, Field
from openai import OpenAI
import os

class RobotCommand(BaseModel):
    action: str = Field(description="one of: walk, sit, stand, turn")
    speed: float = Field(ge=0, le=1)
    say: str

client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
resp = client.responses.parse(
    model="grok-4.7",
    input="The visitor says hi and asks you to come closer.",
    text_format=RobotCommand,
)
cmd = resp.output_parsed
```
(Il pattern `responses.parse(..., text_format=Model)` e `output_parsed` è quello dei docs xAI, nell'esempio "Agentic Tools with Structured Output". Il modello RobotCommand è un mio adattamento.)

### Python, OpenAI SDK, Chat Completions (legacy)
```python
completion = client.beta.chat.completions.parse(
    model="grok-4.7",
    messages=[{"role": "user", "content": "..."}],
    response_format=RobotCommand,
)
cmd = completion.choices[0].message.parsed
```

### Python, xai-sdk
```python
from xai_sdk import Client
from xai_sdk.chat import user

chat = Client().chat.create(model="grok-4.7")
chat.append(user("The visitor says hi and asks you to come closer."))
response, cmd = chat.parse(RobotCommand)   # (Response, istanza Pydantic)

# In alternativa, compatibile con lo streaming:
chat = Client().chat.create(model="grok-4.7", response_format=RobotCommand)
# ... chat.stream() / chat.sample(), poi RobotCommand.model_validate_json(response.content)
```

### JS, OpenAI SDK, Responses (JSON schema esplicito)
```javascript
const response = await client.responses.create({
  model: "grok-4.7",
  input: "Give me a robot command.",
  text: {
    format: {
      type: "json_schema",
      name: "robot_command",
      schema: {
        type: "object",
        properties: { action: { type: "string" }, speed: { type: "number" } },
        required: ["action", "speed"],
        additionalProperties: false,
      },
      strict: true,
    },
  },
});
const cmd = JSON.parse(response.output_text);
```

### Vercel AI SDK
```javascript
import { generateText, Output } from 'ai';
const result = await generateText({
  model: xai.responses('grok-4.7'),
  output: Output.object({ schema: RobotCommandZod }),
  prompt: '...',
});
```
⚠️ L'esempio ufficiale legge `result._output`, che è una proprietà "privata". Nelle versioni recenti di `ai` il campo pubblico dovrebbe essere `result.output`, ma non l'ho verificato.

## Fonti
- https://docs.x.ai/developers/tools/function-calling.md
- https://docs.x.ai/developers/model-capabilities/text/structured-outputs.md
- https://docs.x.ai/developers/tools/advanced-usage.md
- https://docs.x.ai/developers/rest-api-reference/inference/responses.md
- https://docs.x.ai/openapi.json (schemi `ModelToolChoice` / `ToolChoice`)
- https://github.com/xai-org/xai-sdk-python (v1.21.0, 2026-10-23), `xai_sdk/chat.py` (`required_tool`, `tool`, `tool_result`)
- https://github.com/xai-org/xai-sdk-ts (README, sezione Tools)
