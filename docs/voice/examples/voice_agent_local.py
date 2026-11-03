#!/usr/bin/env python3
"""
Grok Voice Agent (Speech to Speech) - client locale microfono/casse con un function tool.

Requisiti:
    pip install "websockets>=14" sounddevice numpy
    (Linux: sudo apt install libportaudio2 ; macOS: brew install portaudio)
    export XAI_API_KEY=xai-...

Uso:
    python voice_agent_local.py                 # half-duplex (default, sicuro con casse aperte)
    python voice_agent_local.py --full-duplex   # barge-in vero: usare CUFFIE o un device con AEC
    python voice_agent_local.py --rate 48000    # se il device non supporta 24 kHz
    python voice_agent_local.py --text          # niente audio: scrivi da tastiera (debug)

Protocollo: wss://api.x.ai/v1/realtime (compatibile OpenAI Realtime), vedi events-reference.md.
"""
import argparse
import asyncio
import base64
import json
import os
import threading
import time

from websockets.asyncio.client import connect  # websockets >= 13 (API "nuova")

URL = os.getenv("XAI_REALTIME_URL", "wss://api.x.ai/v1/realtime")
MODEL = os.getenv("XAI_VOICE_MODEL", "grok-voice-latest")  # in produzione: "grok-voice-3.0"
VOICE = os.getenv("XAI_VOICE", "eve")  # built-in (eve, ara, rex, sal, leo, ...) o custom voice_id

INSTRUCTIONS = """## Role & Persona
You are Fido, a playful robot dog at the Ctrl+Alt Museum in Pavia. You speak Italian.

## Objective
Understand what the visitor wants the robot dog to do and do it with the move_robot tool.

## Conversation Flow
When the visitor asks for a movement or a trick, say one short line like "Ok, ci penso io!" and call move_robot immediately.
After the tool result, confirm in one short sentence what you did.

## Guardrails & Escalation
Only use the actions listed in the move_robot tool. If asked for something else, say you can't do it yet.

## Voice & Communication Style
- Respond only in Italian.
- Spoken words only: no markdown, no lists, no emojis.
- 1-2 short sentences per turn.
"""

TOOLS = [
    {
        # Formato "piatto" (come OpenAI Realtime e come il cookbook ufficiale xAI)
        "type": "function",
        "name": "move_robot",
        "description": "Make the robot dog perform a movement or trick.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["sit", "stand", "walk_forward", "walk_backward", "turn_left", "turn_right", "wave", "dance"],
                    "description": "Movement to perform",
                },
                "duration_s": {"type": "number", "description": "Duration in seconds (0.5-10)"},
            },
            "required": ["action"],
        },
    }
]


def run_tool(name: str, args: dict) -> dict:
    """Esegue il tool (bloccante va bene: viene chiamato in un thread). Sostituire con l'SDK del robot."""
    if name == "move_robot":
        action = args.get("action")
        duration = float(args.get("duration_s", 2))
        print(f"\n[ROBOT] -> {action} per {duration}s")
        # TODO: qui chiamare l'SDK/HTTP/ROS del cane robot
        return {"ok": True, "action": action, "duration_s": duration}
    return {"ok": False, "error": f"unknown tool {name}"}


class Player:
    """Buffer PCM16 mono riprodotto da un RawOutputStream di sounddevice."""

    def __init__(self, rate: int):
        import sounddevice as sd  # import lazy: --text funziona senza PortAudio

        self._buf = bytearray()
        self._lock = threading.Lock()
        self.last_audio_at = 0.0
        self._stream = sd.RawOutputStream(samplerate=rate, channels=1, dtype="int16", callback=self._cb)
        self._stream.start()

    def _cb(self, outdata, frames, time_info, status):
        n = frames * 2
        with self._lock:
            chunk = bytes(self._buf[:n])
            del self._buf[:n]
        if chunk:
            self.last_audio_at = time.monotonic()
        outdata[: len(chunk)] = chunk
        outdata[len(chunk):] = b"\x00" * (n - len(chunk))

    def feed(self, pcm: bytes):
        with self._lock:
            self._buf.extend(pcm)

    def clear(self):
        with self._lock:
            self._buf.clear()

    def busy(self, tail_s: float = 0.0) -> bool:
        with self._lock:
            pending = len(self._buf) > 0
        return pending or (time.monotonic() - self.last_audio_at) < tail_s


class NullPlayer:
    last_audio_at = 0.0

    def __init__(self):
        self.bytes_received = 0

    def feed(self, pcm: bytes):
        self.bytes_received += len(pcm)

    def clear(self):
        pass

    def busy(self, tail_s: float = 0.0) -> bool:
        return False


async def mic_task(ws, rate: int, player, half_duplex: bool, ready: asyncio.Event):
    import sounddevice as sd

    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue()
    frames = rate // 10  # 100 ms per chunk (consigliato dalla doc)

    def cb(indata, frames_, time_info, status):
        loop.call_soon_threadsafe(q.put_nowait, bytes(indata))

    with sd.RawInputStream(samplerate=rate, channels=1, dtype="int16", blocksize=frames, callback=cb):
        while True:
            chunk = await q.get()
            if not ready.is_set():
                continue  # non mandare audio prima di session.updated (formato non ancora applicato)
            if half_duplex and player.busy(tail_s=0.3):
                continue  # niente eco: il modello non sente se stesso dalle casse
            await ws.send(json.dumps({"type": "input_audio_buffer.append",
                                      "audio": base64.b64encode(chunk).decode()}))


async def stdin_task(ws, ready: asyncio.Event):
    await ready.wait()
    while True:
        line = await asyncio.to_thread(input, "\nTu> ")
        if not line.strip():
            continue
        await ws.send(json.dumps({"type": "conversation.item.create", "item": {
            "type": "message", "role": "user", "content": [{"type": "input_text", "text": line}]}}))
        await ws.send(json.dumps({"type": "response.create"}))


async def wait_playback(player, timeout_s: float = 15.0):
    t0 = time.monotonic()
    while player.busy(tail_s=0.1) and time.monotonic() - t0 < timeout_s:
        await asyncio.sleep(0.05)


async def session(args, conversation_id=None):
    url = f"{URL}?model={MODEL}"
    if conversation_id:
        url += f"&conversation_id={conversation_id}"
    headers = {"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"}
    player = NullPlayer() if args.text else Player(args.rate)
    ready = asyncio.Event()
    state = {"conversation_id": conversation_id, "pending_calls": []}

    async with connect(url, additional_headers=headers, open_timeout=10, max_size=None) as ws:
        # 1) aspetta session.created (doc cookbook: ~1 connessione su 10 non parte -> timeout e retry)
        while True:
            first = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            if first["type"] == "conversation.created":
                state["conversation_id"] = first["conversation"]["id"]
            if first["type"] in ("session.created", "conversation.created"):
                break

        # 2) configura la sessione
        audio_fmt = {"type": "audio/pcm", "rate": args.rate}
        await ws.send(json.dumps({"type": "session.update", "session": {
            "voice": VOICE,
            "instructions": INSTRUCTIONS,
            "turn_detection": {"type": "server_vad"},  # esplicito: non fidarti del default
            "audio": {
                "input": {"format": audio_fmt, "transcription": {"language_hint": "it"}},
                "output": {"format": audio_fmt},
            },
            "tools": TOOLS,
            "resumption": {"enabled": True},  # estensione xAI: replay history su reconnect
            # "reasoning": {"effort": "none"},  # meno latenza su compiti semplici
        }}))

        side = asyncio.create_task(stdin_task(ws, ready) if args.text
                                   else mic_task(ws, args.rate, player, not args.full_duplex, ready))
        try:
            async for raw in ws:
                if isinstance(raw, bytes):  # solo se audio.output.transport == "binary"
                    player.feed(raw)
                    continue
                ev = json.loads(raw)
                t = ev["type"]
                if t == "conversation.created":
                    state["conversation_id"] = ev["conversation"]["id"]
                elif t == "session.updated" and not ready.is_set():
                    ready.set()
                    print("[sessione pronta] parla pure (Ctrl+C per uscire)")
                    if not conversation_id:  # saluto iniziale: l'agente parla per primo
                        await ws.send(json.dumps({"type": "response.create", "response": {
                            "instructions": "Greet the visitor in Italian in one short sentence."}}))
                elif t == "response.output_audio.delta":
                    player.feed(base64.b64decode(ev["delta"]))
                elif t == "response.output_audio_transcript.delta":
                    print(ev["delta"], end="", flush=True)
                elif t == "input_audio_buffer.speech_started":
                    player.clear()  # barge-in: ferma subito la riproduzione locale
                    print("\n[utente parla...]")
                elif t == "conversation.item.input_audio_transcription.completed":
                    print(f"\n[utente] {ev.get('transcript', '')}")
                elif t == "response.function_call_arguments.done":
                    state["pending_calls"].append(ev)  # possono arrivarne piu' d'uno (parallel calls)
                elif t == "response.done":
                    print()
                    calls, state["pending_calls"] = state["pending_calls"], []
                    if calls:
                        for c in calls:
                            try:
                                fargs = json.loads(c.get("arguments") or "{}")
                            except json.JSONDecodeError:
                                fargs = {}
                            result = await asyncio.to_thread(run_tool, c["name"], fargs)
                            await ws.send(json.dumps({"type": "conversation.item.create", "item": {
                                "type": "function_call_output", "call_id": c["call_id"],
                                "output": json.dumps(result)}}))
                        await wait_playback(player)  # evita audio sovrapposto (best practice doc)
                        await ws.send(json.dumps({"type": "response.create"}))  # UNA sola volta
                elif t == "error":
                    print(f"\n[ERRORE] {ev.get('error')}")
        finally:
            side.cancel()
    return state["conversation_id"]


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rate", type=int, default=24000, help="8000/16000/22050/24000/32000/44100/48000")
    p.add_argument("--full-duplex", action="store_true", help="barge-in reale (usa cuffie/AEC)")
    p.add_argument("--text", action="store_true", help="modalita' testo, senza audio")
    args = p.parse_args()

    conv_id, backoff = None, 1
    while True:
        try:
            conv_id = await session(args, conv_id) or conv_id
            backoff = 1
        except (asyncio.TimeoutError, OSError) as e:
            print(f"[reconnect] {type(e).__name__}: {e}")
        except Exception as e:  # ConnectionClosed ecc.
            print(f"[reconnect] {type(e).__name__}: {e}")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
