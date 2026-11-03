#!/usr/bin/env python3
"""
Bridge Twilio Media Streams <-> Grok Voice Agent (μ-law 8 kHz passthrough, nessuna conversione).
Porting Python del cookbook ufficiale xai-org/xai-cookbook/examples/voice-agent-phone/xai (Node/TS).

Requisiti:
    pip install fastapi "uvicorn[standard]" "websockets>=14"
    export XAI_API_KEY=xai-...
    export PUBLIC_HOST=abcd-1234.ngrok-free.app     # host pubblico, senza https://

Avvio:
    uvicorn twilio_bridge:app --host 0.0.0.0 --port 3000
    ngrok http 3000
    Twilio Console > Phone Numbers > (numero) > Voice "A call comes in": Webhook POST https://<PUBLIC_HOST>/twiml
"""
import asyncio
import base64
import json
import os

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from websockets.asyncio.client import connect

XAI_URL = os.getenv("XAI_REALTIME_URL", "wss://api.x.ai/v1/realtime")
MODEL = os.getenv("XAI_VOICE_MODEL", "grok-voice-latest")
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "localhost:3000")

INSTRUCTIONS = """## Role & Persona
You are the operator of the robot dog at the Ctrl+Alt Museum. You answer phone calls in Italian.

## Objective
Take spoken orders for the robot dog and execute them with the move_robot tool.

## Conversation Flow
Before calling move_robot, say one short line such as "Subito!". After the result, confirm briefly.

## Guardrails & Escalation
Only use the actions in the move_robot tool. Otherwise say you can't do it.

## Voice & Communication Style
- Respond only in Italian. Spoken words only. 1-2 short sentences per turn.
"""

TOOLS = [{
    "type": "function",
    "name": "move_robot",
    "description": "Make the robot dog perform a movement or trick.",
    "parameters": {
        "type": "object",
        "properties": {"action": {"type": "string",
                                  "enum": ["sit", "stand", "walk_forward", "turn_left", "turn_right", "wave", "dance"]}},
        "required": ["action"],
    },
}]


def run_tool(name: str, args: dict) -> dict:
    if name == "move_robot":
        print(f"[ROBOT] -> {args.get('action')}")  # TODO: SDK/HTTP del robot
        return {"ok": True, "action": args.get("action")}
    return {"ok": False, "error": f"unknown tool {name}"}


app = FastAPI()


@app.post("/twiml")
async def twiml(request: Request):
    # <Connect><Stream> = stream BIDIREZIONALE (necessario per rimandare audio al chiamante)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://{PUBLIC_HOST}/media-stream" />
  </Connect>
</Response>"""
    return Response(content=xml, media_type="text/xml")


@app.websocket("/media-stream")
async def media_stream(tw: WebSocket):
    await tw.accept()
    st = {"stream_sid": None, "ready": False, "calls": [], "marks": set()}
    marks_drained = asyncio.Event()
    marks_drained.set()

    async with connect(f"{XAI_URL}?model={MODEL}",
                       additional_headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"},
                       open_timeout=10, max_size=None) as xai:

        async def send_tw(msg: dict):
            if st["stream_sid"]:
                await tw.send_text(json.dumps(msg))

        async def twilio_to_xai():
            try:
                while True:
                    msg = json.loads(await tw.receive_text())
                    ev = msg.get("event")
                    if ev == "start":
                        st["stream_sid"] = msg["start"]["streamSid"]
                        print(f"[twilio] start callSid={msg['start'].get('callSid')}")
                    elif ev == "media" and msg["media"].get("track", "inbound") == "inbound":
                        if st["ready"]:  # niente audio prima di session.updated
                            await xai.send(json.dumps({"type": "input_audio_buffer.append",
                                                       "audio": msg["media"]["payload"]}))
                    elif ev == "mark":  # Twilio rimanda il mark quando l'audio precedente e' stato riprodotto
                        st["marks"].discard(msg["mark"]["name"])
                        if not st["marks"]:
                            marks_drained.set()
                    elif ev == "stop":
                        break
            except WebSocketDisconnect:
                pass
            finally:
                await xai.close()

        async def xai_to_twilio():
            async for raw in xai:
                ev = json.loads(raw)
                t = ev["type"]
                if t == "conversation.created":
                    await xai.send(json.dumps({"type": "session.update", "session": {
                        "voice": os.getenv("XAI_VOICE", "ara"),
                        "instructions": INSTRUCTIONS,
                        "turn_detection": {"type": "server_vad"},
                        "audio": {"input": {"format": {"type": "audio/pcmu"},
                                            "transcription": {"language_hint": "it"}},
                                  "output": {"format": {"type": "audio/pcmu"}}},
                        "tools": TOOLS,
                    }}))
                elif t == "session.updated" and not st["ready"]:
                    st["ready"] = True
                    await xai.send(json.dumps({"type": "response.create", "response": {
                        "instructions": "Answer the phone: greet the caller in Italian in one short sentence."}}))
                elif t == "response.output_audio.delta":
                    await send_tw({"event": "media", "streamSid": st["stream_sid"],
                                   "media": {"payload": ev["delta"]}})  # già μ-law base64
                elif t == "input_audio_buffer.speech_started":
                    await send_tw({"event": "clear", "streamSid": st["stream_sid"]})  # barge-in
                    st["marks"].clear()
                    marks_drained.set()
                elif t == "conversation.item.input_audio_transcription.completed":
                    print(f"[caller] {ev.get('transcript')}")
                elif t == "response.output_audio_transcript.done":
                    print(f"[agent] {ev.get('transcript')}")
                elif t == "response.function_call_arguments.done":
                    st["calls"].append(ev)
                elif t == "response.done":
                    rid = ev.get("response", {}).get("id", "r")
                    if st["stream_sid"]:
                        st["marks"].add(rid)
                        marks_drained.clear()
                        await send_tw({"event": "mark", "streamSid": st["stream_sid"], "mark": {"name": rid}})
                    calls, st["calls"] = st["calls"], []
                    if calls:
                        for c in calls:
                            try:
                                a = json.loads(c.get("arguments") or "{}")
                            except json.JSONDecodeError:
                                a = {}
                            res = await asyncio.to_thread(run_tool, c["name"], a)
                            await xai.send(json.dumps({"type": "conversation.item.create", "item": {
                                "type": "function_call_output", "call_id": c["call_id"], "output": json.dumps(res)}}))
                        try:  # aspetta che il chiamante abbia sentito la frase prima del tool
                            await asyncio.wait_for(marks_drained.wait(), timeout=10)
                        except asyncio.TimeoutError:
                            pass
                        await xai.send(json.dumps({"type": "response.create"}))
                elif t == "error":
                    print(f"[xai error] {ev.get('error')}")

        await asyncio.gather(twilio_to_xai(), xai_to_twilio(), return_exceptions=True)
