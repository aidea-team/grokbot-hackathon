# SpaceXAI (oggi "SpaceXSI"): cos'è e cosa vuole vedere

> **Verificato il 2026-11-03.** Fonte primaria per i prodotti: release notes ufficiali delle API (docs.x.ai/release-notes). Per la storia societaria: Wikipedia e stampa. x.ai/news risponde 403 alle letture automatiche, quindi gli annunci sono citati di seconda mano dove indicato. ⚠️ = non verificato o fonti in conflitto.
> I dettagli tecnici di API, Voice, Bot e Imagine sono negli altri documenti: [../grok-api/](../grok-api/), [../voice/](../voice/), [../bots-imagine/](../bots-imagine/).

## Linea del tempo societaria

| Data | Evento |
|---|---|
| 2/2/2026 | **SpaceX acquisisce xAI** con un'operazione interamente in azioni; xAI diventa controllata al 100%. Valutazioni: SpaceX circa $1T, xAI circa $250B (⚠️ una fonte dice $125B) |
| feb–mar 2026 | Riorganizzazione in 4 team e licenziamenti. A fine marzo nessuno dei co-fondatori originali, tranne Musk, è ancora in azienda |
| 10/4/2026 | Michael Nicolls (VP Starlink) diventa presidente di xAI |
| 21/4/2026 | SpaceX ottiene un'opzione per acquisire **Cursor** (Anysphere) per $60B |
| mag 2026 | Musk: xAI smette di esistere come società separata; Grok e X diventano la divisione AI di SpaceX |
| 12/6/2026 | IPO di SpaceX (valutazione circa $1,77T) |
| 16/6/2026 | SpaceX esercita l'opzione su Cursor ($60B in azioni); **closing il 14/8/2026**. SpaceXAI e Cursor si fondono |
| lug 2026 | Rebrand **xAI → SpaceXAI** (nuovo logo riportato il 6/7) |
| 4/10/2026 | Musk annuncia il rinomino in **SpaceXSI** ("SpaceX Super Intelligence"); depositato il marchio SPACEXSI |
| 10/10/2026 | L'account X ufficiale diventa **@SpaceXSI** |
| 13/10/2026 | Sito e termini legali passano a SpaceXSI; bundle unico di abbonamento **X + Grok + Cursor** |

Per noi: l'evento usa ancora il nome **"SpaceXAI"** (sito, speaker "SpaceXAI team"), mentre Luma ed email ora dicono "SpaceXSI for Milan, Italy" e le docs API dicono "SpaceXSI". Sono la stessa cosa. **Cursor ora è della stessa azienda**: il sito lo elenca tra i tool, con Grok 4.7 tra i suoi modelli.

## Prodotti rilevanti per l'hackathon (stato al 3/11/2026)

Dalle release notes ufficiali dell'API, salvo dove indicato.

| Prodotto | Stato | Note utili |
|---|---|---|
| **Grok 4.7** (`grok-4.7`) | Settembre 2026, modello di punta "for coding, agentic tasks, and knowledge work" | Contesto 500k; input testo e immagini; nessun limite di output; reasoning effort low, medium, high (default) e xhigh. Prezzi $2 / $0,50 (cache) / $6 per 1M token sotto i 200k (doppi sopra). **Grok 4.7 Fast** solo in Cursor e Grok Build. Il sito dell'hackathon lo cita esplicitamente |
| Grok 4.6 / 4.5 | Agosto e luglio 2026 | Stessa fascia di prezzo |
| Grok 4.20 + Multi-agent | Marzo 2026 | |
| **Grok Voice** (speech-to-speech, realtime) | **`grok-voice-3.0`** (ottobre 2026) = `grok-voice-latest`; Voice 2.0 deprecata; Voice 1.0 da aprile 2026 | API Realtime via WebSocket compatibile OpenAI (`wss://api.x.ai/v1/realtime`, secondo LiteLLM). Più **TTS** (marzo), **STT** (aprile; `grok-voice-transcribe-2.0` a settembre; Smart Turn; soglia VAD regolabile, "utile per telefonia narrowband"), **Custom Voices** (clonazione da una breve clip, maggio) |
| **Grok Bot** | Disponibile da agosto 2026 (beta lanciata l'**11/8/2026** con Cursor) | "Durable AI teammates that work on a persistent cloud computer, with messaging, approvals, connectors, and routines". Agenti su un computer remoto (browser, filesystem, terminale) che lavorano 24/7, usano le app come una persona e si coordinano tra loro. Accesso iniziale per SuperGrok Heavy, Cursor Ultra e Cursor Teams Premium. Esistono **template condivisibili** (link x.ai/bot/…, usati nell'hackathon di Tokyo) |
| **Grok Imagine** | Immagini `grok-imagine-image-2.0` (qualità auto, fino a 5 immagini di riferimento, 21:9 e 5:2); video `grok-imagine-video-1.5` (testo→video, immagine→video, riferimento→video, 1080p nativo) | `grok-imagine-image-quality` **ritirato il 2/11/2026**. Integrazione con la Files API e URL pubblici |
| **Grok Build** | Beta da maggio 2026 (`curl -fsSL https://x.ai/cli/install.sh \| bash`) | Agente di coding da terminale: TUI, headless per script e CI, Agent Client Protocol. Modello dedicato `grok-build-0.1`. ⚠️ Open source (Apache 2.0, `xai-org/grok-build`) secondo fonti secondarie |
| Tool server-side | GA | Web search (anche immagini), X search, code execution, collections e search sui documenti; Responses API anche via WebSocket; Context Compaction; Priority processing; Batch API |
| Moderazione personalizzata | Ottobre 2026 | Array `guidelines` (nsfw, violence, profanity) |

### Altri segnali recenti

- **Grokathon 2026** (ufficiale, 12 ore): ha vinto **Nova** (decompilatore di binari verso C, provato su una ROM Game Boy e su una centralina d'auto del 1995). Tra i finalisti **ThinkVoice** (Grok Voice + sensori cerebrali). SpaceXAI ama progetti tecnicamente audaci, "retro + AI" e Voice su hardware. Vedi [hackathon.md](hackathon.md#eventi-simili-precedenti-contesto).
- ⚠️ Concorso Grok Bot con chiusura iscrizioni il 29/9/2026: i finalisti visitano la fabbrica SpaceX di Hawthorne (fonte Digg, non verificata).
- ⚠️ **Grok in Tesla Optimus**: Musk avrebbe confermato che Optimus "already" conversa tramite Grok Voice (solo fonti secondarie). Fa da aggancio narrativo per "Grok che dà voce e cervello a un robot".
- Campagna globale di **Grok Bot Meetup, Build Day e Hackathon** (decine di città a ottobre e novembre 2026) gestita dalla "SpaceXSI Community", ex community degli ambassador Cursor. Il prodotto che spingono adesso è **Grok Bot**.

## Cosa la giuria e SpaceXAI vorranno vedere valorizzato (nostra lettura)

1. **Grok Bot**: è il prodotto del momento. È citato nel talk ("Grok Bots"), nel brief ("bot framework") e nei criteri di altri hackathon ("How much Grok Bot and Cursor architected it"). Usarlo in modo **visibile**: per esempio un Grok Bot "operatore" con approvazioni umane, routine e connettori che orchestra il robot, oppure usato per costruire (mostrare la sessione).
2. **Grok Voice 3.0 in realtime** su hardware fisico: lo speaker ne parla, ha vinto un premio al Grokathon ed è l'interfaccia naturale per cane, drone e simulatori.
3. **Grok 4.7 per codice e agenti**: generazione di codice in tempo reale (es. Code-as-Policies con Grok), function calling e structured output, reasoning effort regolabile. Mostrare la latenza.
4. **Imagine** come ciliegina (video del volo, poster), non come centro.
5. **Cursor e Grok Build** come strumenti con cui abbiamo costruito, da citare nel pitch.
6. Coerenza con i "principi condivisi": evidenze misurabili, replay e log, human in the loop, sicurezza (vedi [hackathon.md](hackathon.md#criteri-di-giudizio)).

## Fonti

- Release notes API: https://docs.x.ai/release-notes.md (lette il 2026-11-03)
- Wikipedia SpaceXAI: https://en.wikipedia.org/wiki/SpaceXAI
- Bloomberg (trattative, gen 2026): https://www.bloomberg.com/news/articles/2026-01-29/spacex-in-merger-talks-with-xai-ahead-of-ipo-reuters-reports
- Grok 4.7: https://www.inside.com.tw/article/42456-grok-47-xai-launch-api-github-copilot-sept-2026 (secondaria)
- Grok Bot: https://thenextweb.com/news/spacexai-grok-bot-ai-agents-cursor , https://www.constellationr.com/insights/news/spacexai-launches-grok-bot-work-assistant , https://x.ai/news/introducing-grok-bot (⚠️ 403)
- Grok Voice (LiteLLM): https://docs.litellm.ai/docs/providers/xai_realtime
- Grok Build: https://docs.x.ai/build/overview , https://gittrend.io/repo/xai-org/grok-build (secondaria)
- Grokathon: https://runtimewire.com/article/spacexai-grokathon-nova-binary-decompiler
- Optimus + Grok (⚠️ secondaria): https://www.notateslaapp.com/news/2874/tesla-to-integrate-xais-grok-into-optimus-helping-bring-the-robot-to-life
- Calendario globale SpaceXSI Community (Luma): https://luma.com/spacexsi-community
