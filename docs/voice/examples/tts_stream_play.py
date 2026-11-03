#!/usr/bin/env python3
"""
Streaming TTS (wss://api.x.ai/v1/tts) -> casse, a bassa latenza. Utile per telecronache:
un LLM testuale (o il vostro codice) genera frasi, questo le pronuncia appena arrivano.

    pip install "websockets>=14" sounddevice
    export XAI_API_KEY=xai-...
    python tts_stream_play.py "E parte il cane robot! [laugh] Che velocità, signori!"
"""
import asyncio
import base64
import json
import os
import sys

from websockets.asyncio.client import connect

URL = os.getenv("XAI_TTS_URL", "wss://api.x.ai/v1/tts")
RATE = 24000


async def speak(sentences, voice="rex", language="it"):
    import sounddevice as sd

    qs = (f"?language={language}&voice={voice}&codec=pcm&sample_rate={RATE}"
          f"&optimize_streaming_latency=1")  # 1 = primo chunk piu' piccolo (meno TTFA)
    out = sd.RawOutputStream(samplerate=RATE, channels=1, dtype="int16")
    out.start()
    async with connect(URL + qs, additional_headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"},
                       max_size=None) as ws:
        for s in sentences:  # multi-utterance sulla stessa connessione
            await ws.send(json.dumps({"type": "text.delta", "delta": s}))
            await ws.send(json.dumps({"type": "text.done"}))
            async for raw in ws:
                ev = json.loads(raw)
                if ev["type"] == "audio.delta":
                    await asyncio.to_thread(out.write, base64.b64decode(ev["delta"]))
                elif ev["type"] == "audio.done":
                    break
                elif ev["type"] == "error":
                    raise RuntimeError(ev.get("message"))
        # per interrompere (barge-in): await ws.send(json.dumps({"type": "text.clear"})) -> server risponde audio.clear
    out.stop()


if __name__ == "__main__":
    asyncio.run(speak(sys.argv[1:] or ["Benvenuti al Ctrl+Alt Museum di Pavia!"]))
