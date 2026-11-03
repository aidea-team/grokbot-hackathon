# Macchine d'epoca + Grok: C64, Programma 101, telefoni a disco, MS-DOS

> Verificato il: **2026-11-03**. ✅ = verificato (doc ufficiale o **provato in locale**) · ⚠️ = non verificato.
> Contesto museo (Ultimate 64 Elite MK2, Videotel con ESP32, chattralino): vedi `../event/museum.md` e `museum-inventory-sims.md`.

## TL;DR

- **C64 in VICE ↔ Grok: provato end-to-end in locale** (VICE 3.7.1 su Linux/WSLg; per l'LLM si è usata una funzione finta). Funziona così: un programma BASIC V2 scrive la domanda in una **mailbox in RAM**, Python la legge via **VICE binary monitor** (TCP 6502), chiama Grok e riscrive la risposta in RAM; il BASIC la stampa. Codice completo in §2.4. ✅ 8 run su 8 riusciti dopo l'aggiunta del marker "ready".
- Lo **stesso protocollo a mailbox funziona sul C64 "vero" del museo**, se l'Ultimate 64 è in rete: la REST API ha `readmem`/`writemem`/`run_prg` (§2.6). ⚠️ Non provato su hardware.
- `petcat -w2 -o prog.prg -- prog.bas` tokenizza BASIC V2 ✅ (provato). I keyword vanno scritti **in minuscolo**, i codici di controllo come `{clr}`.
- Il **text monitor remoto** di VICE (TCP 6510) accetta `keybuf print 2+2\x0d` e `m 0400 0567` ✅ (provato): è il modo più rapido per "digitare" nel C64 e leggere lo schermo.
- Per il pitch il precedente "chattare col C64" esiste già (vedi `../ideas/prior-art.md`). Ci distingue **Grok che agisce**: scrive ed esegue BASIC, legge lo schermo, corregge.

---

## 1. Commodore 64: vincoli di BASIC V2 (per i prompt di Grok che deve scrivere codice)

- Righe numerate **0-63999**; una riga logica può avere **al massimo 80 caratteri a schermo** (2 righe da 40). ✅ (C64-wiki) Abbreviando i keyword (es. `?` per PRINT) si ottengono righe più lunghe, ma **petcat accetta righe lunghe senza problemi**, che poi però non sono editabili sul C64. ⚠️
- **38911 byte** liberi per il BASIC. ✅
- **Nessun costrutto strutturato**: niente `WHILE`, `ELSE`, `DO/LOOP` (arrivano da BASIC 3.5 in poi). Solo `IF … THEN`, `GOTO`, `GOSUB`, `FOR/NEXT`. ✅
- **Nessun comando per grafica, suono o colori**: si usano `POKE` e `PEEK`, per esempio `POKE 53280,0` per il bordo nero. ✅
- Variabili: solo **i primi 2 caratteri sono significativi** (`SCORE` e `SCARF` sono la stessa variabile), tipi `A` float, `A%` int, `A$` stringa (max 255 caratteri). ⚠️ Fatto noto, non verificato sulla pagina C64-wiki letta.
- `INPUT` **spezza sulle virgole**: "ciao, come stai" diventa `CIAO` con `?EXTRA IGNORED`. ✅ (provato). Anche i due punti danno problemi. Soluzioni: dire all'utente di non usare la virgola, oppure leggere con `GET` carattere per carattere.
- `INPUT` aggiunge sempre `? ` dopo il prompt. ✅ (provato)
- Il programma è **tokenizzato**: i keyword diventano byte singoli da $80 in su. Un `.prg` ha come header l'indirizzo di caricamento `01 08` ($0801). ✅ (provato con xxd)
- Charset: in modalità maiuscole/grafica (default) si scrive in **MAIUSCOLO ASCII 32-93**. Le minuscole ASCII nel keybuf di VICE vengono digitate come maiuscole ✅. Le lettere accentate vanno traslitterate (à → A).

**Prompt suggerito a Grok per generare BASIC:** "Scrivi un programma Commodore 64 BASIC V2. Righe numerate a passi di 10, keyword in minuscolo, nessun costrutto non presente in V2 (niente ELSE/WHILE), massimo 80 caratteri per riga, usa POKE per colori e suono, codici di controllo nel formato petcat `{clr}` `{wht}`. Rispondi solo con il codice."
Il loop di correzione: petcat → run in VICE → lettura dello schermo (per esempio `?SYNTAX ERROR IN 40`) → di nuovo a Grok.

## 2. VICE: emulatore, monitor, automazione da Python

### 2.1 Installazione
- **Windows**: build GTK3 ufficiale da https://vice-emu.sourceforge.io. Eseguibile `x64sc.exe` in `bin/`. ⚠️ Non provato su Windows.
- **Ubuntu/WSL**: `sudo apt install vice` installa la 3.7.1, **ma senza ROM** (pacchetto `+dfsg`). All'avvio si ottiene `Couldn't load kernal ROM 'kernal-901227-03.bin'`. ✅ (provato) Le ROM si prendono dal tarball sorgente ufficiale `vice-3.7.1.tar.gz` (cartelle `data/C64`, `data/DRIVES`) e si copiano in `/usr/share/vice/C64` e `/usr/share/vice/DRIVES`. In alternativa si passa `-directory <dir>`, dove `<dir>` deve contenere le sottocartelle `C64/`, `DRIVES/` ecc. ✅ (provato: con `-directory .../vice/C64` NON funziona, con `-directory .../vice` sì).
- Opzioni utili (verificate con `x64sc -help`, 3.7.1) ✅:
  - `-binarymonitor -binarymonitoraddress ip4://127.0.0.1:6502`
  - `-remotemonitor -remotemonitoraddress ip4://127.0.0.1:6510`
  - `-autostart file.prg`, oppure il file come ultimo argomento
  - `-autostartprgmode 1` (inject in RAM)
  - `-keybuf "<stringa>"` (escape esadecimali tipo `\x0d`)
  - `-warp`, `-sounddev dummy`, `-limitcycles`, `-exitscreenshot`, `-moncommands file`
  - ⚠️ La porta di default **non è documentata**. Le porte 6502 e 6510 sono quelle degli esempi e delle convenzioni: passarle sempre esplicite.

### 2.2 petcat (BASIC testo ↔ .prg) ✅ provato
```bash
petcat -w2 -o grok64.prg -- grok64.bas     # tokenizza (BASIC V2)
petcat -2 -- grok64.prg                    # detokenizza / list
```

### 2.3 Remote monitor testuale (porta 6510) ✅ provato
```python
import socket, time
s = socket.create_connection(("127.0.0.1", 6510))
s.sendall(rb"keybuf print 2+2\x0d" + b"\n")  # digita nel C64 (\x0d = RETURN)
s.sendall(b"x\n")                         # esce dal monitor: l'emulazione riparte
time.sleep(1)
s.sendall(b"m 0400 07e7\n")               # dump della screen RAM (screen code, non ASCII)
time.sleep(0.5); print(s.recv(65536).decode("latin-1"))
s.sendall(b"x\n")
```
Altri comandi: `autostart "file.prg"`, `reset`, `load`, `bload`. ✅ (manuale VICE, cap. 12)

### 2.4 Binary monitor: bridge C64 ↔ Grok (codice provato) ✅

**Protocollo binary monitor** (manuale VICE cap. 13), little endian:
- **Richiesta**: `02` (STX) · `02` (API v2) · `len` u32 · `request_id` u32 · `cmd` u8 · body
- **Risposta**: `02` · `02` · `len` u32 · `type` u8 · `error` u8 · `request_id` u32 · body. Gli eventi asincroni hanno id `0xffffffff`.
- Comandi usati: `0x01` memory get, `0x02` memory set, `0x72` keyboard feed (PETSCII), `0xAA` exit, `0xCC` reset, `0xDD` autostart.
- ⚠️ **Ogni comando ferma l'emulazione**: dopo ogni operazione serve `0xAA` (exit), altrimenti il C64 resta congelato. ✅ (provato)
- Il keyboard feed accetta stringhe **più lunghe dei 10 caratteri** del buffer del C64: VICE le accoda da solo. ✅ (provato con 36 caratteri)
- ⚠️ **Non digitare durante l'autostart**: il testo si perde. ✅ (osservato) Bisogna aspettare un marker "ready" scritto dal programma BASIC (`POKE 829,42`).

**Mailbox in RAM**:
- `$033C`/828: flag (0 idle, 1 domanda pronta, 2 risposta pronta)
- `$033D`/829: ready = 42
- `$C000`/49152: lunghezza della domanda, poi il testo
- `$C100`/49408: lunghezza della risposta (lo/hi), poi il testo da `$C102`

`grok64.bas`:
```basic
10 rem grok64: chat c64 <-> grok (mailbox in ram)
15 poke 828,0:poke 829,42:poke 53280,0:poke 53281,0
20 print "{clr}{wht}grok64 - scrivi e premi return"
30 a$="":input "> ";a$
40 l=len(a$):if l=0 then 30
50 for i=1 to l:poke 49152+i,asc(mid$(a$,i,1)):next
60 poke 49152,l:poke 828,1
70 print "{yel}...";
80 if peek(828)<>2 then 80
90 n=peek(49408)+256*peek(49409)
100 print:for i=1 to n:print chr$(peek(49409+i));:next:print "{wht}"
110 poke 828,0:goto 30
```

`vice_bm.py` (client binary monitor):
```python
import socket, struct, itertools, unicodedata

STX, API = 0x02, 0x02
CMD_MEM_GET, CMD_MEM_SET, CMD_KEYBUF, CMD_EXIT, CMD_RESET, CMD_AUTOSTART = 0x01, 0x02, 0x72, 0xAA, 0xCC, 0xDD

class ViceBM:
    def __init__(self, host="127.0.0.1", port=6502, timeout=5.0):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.ids = itertools.count(1)

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("VICE closed the connection")
            buf += chunk
        return buf

    def _cmd(self, cmd, body=b""):
        rid = next(self.ids)
        self.s.sendall(struct.pack("<BBIIB", STX, API, len(body), rid, cmd) + body)
        while True:  # skip async events (stopped/resumed/registers, req_id 0xffffffff)
            _, _, blen, _, err, resp_id = struct.unpack("<BBIBBI", self._recv_exact(12))
            payload = self._recv_exact(blen)
            if resp_id == rid:
                if err:
                    raise RuntimeError(f"VICE error 0x{err:02x} for cmd 0x{cmd:02x}")
                return payload

    def resume(self):                      # every command stops the emulation
        self._cmd(CMD_EXIT)

    def mem_get(self, start, end, resume=True):
        p = self._cmd(CMD_MEM_GET, struct.pack("<BHHBH", 0, start, end, 0, 0))
        (n,) = struct.unpack("<H", p[:2])
        if resume: self.resume()
        return p[2:2 + n]

    def mem_set(self, start, data: bytes, resume=True):
        self._cmd(CMD_MEM_SET, struct.pack("<BHHBH", 0, start, start + len(data) - 1, 0, 0) + data)
        if resume: self.resume()

    def type_text(self, petscii: bytes, resume=True):
        for i in range(0, len(petscii), 255):
            chunk = petscii[i:i + 255]
            self._cmd(CMD_KEYBUF, bytes([len(chunk)]) + chunk)
        if resume: self.resume()

    def autostart(self, filename: str, run=True):
        fn = filename.encode()
        self._cmd(CMD_AUTOSTART, struct.pack("<BHB", 1 if run else 0, 0, len(fn)) + fn)
        self.resume()

def to_petscii(text: str, maxlen=None) -> bytes:
    """ASCII -> PETSCII, default uppercase/graphics mode."""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))   # accents removed
    out = bytearray()
    for c in t.upper():
        o = ord(c)
        if c == "\n": out.append(13)
        elif 32 <= o <= 93 and c != '"': out.append(o)
        else: out.append(32 if c.isspace() else ord("?"))
        if maxlen and len(out) >= maxlen: break
    return bytes(out)

def screen_text(vm: ViceBM) -> str:
    """Read screen RAM ($0400, 40x25) -> approximate ASCII (useful to show Grok the screen)."""
    raw = vm.mem_get(0x0400, 0x0400 + 999)
    rows = []
    for r in range(25):
        row = ""
        for b in raw[r * 40:(r + 1) * 40]:
            b &= 0x7F
            row += "@" if b == 0 else chr(b + 64) if b <= 26 else chr(b) if 32 <= b <= 63 else "."
        rows.append(row.rstrip())
    return "\n".join(rows)
```

`grok64_bridge.py` (loop; con `FAKE_LLM=1` funziona senza API key):
```python
import os, time
from vice_bm import ViceBM, to_petscii

FLAG, READY, Q, R = 828, 829, 49152, 49408

def ask_llm(question: str) -> str:
    if os.environ.get("FAKE_LLM"):
        return f"(finto) hai chiesto: {question}"
    from openai import OpenAI          # see docs/grok-api/responses-and-chat.md
    client = OpenAI(base_url="https://api.x.ai/v1", api_key=os.environ["XAI_API_KEY"])
    r = client.responses.create(
        model="grok-4.3", reasoning={"effort": "none"},      # low latency (docs/grok-api/models.md)
        instructions=("Sei un Commodore 64 del 1982 al Ctrl+Alt Museum di Pavia. Rispondi in italiano, "
                      "massimo 300 caratteri, solo ASCII, niente emoji, niente virgolette."),
        input=question)
    return r.output_text

def main():
    vm = ViceBM()
    while vm.mem_get(READY, READY)[0] != 42:   # wait for the BASIC program
        time.sleep(0.25)
    while True:
        if vm.mem_get(FLAG, FLAG)[0] == 1:
            n = vm.mem_get(Q, Q)[0]
            q = vm.mem_get(Q + 1, Q + n).decode("latin-1") if n else ""
            t0 = time.time()
            try:
                a = ask_llm(q)
            except Exception as e:             # never leave the C64 hanging
                a = f"ERRORE: {type(e).__name__}"
            data = to_petscii(a, maxlen=600)
            vm.mem_set(R, bytes([len(data) & 0xFF, len(data) >> 8]) + data, resume=False)
            vm.mem_set(FLAG, b"\x02")
            print({"q": q, "a": a, "latency_s": round(time.time() - t0, 2)})   # -> JSONL for the jury
        time.sleep(0.25)

if __name__ == "__main__":
    main()
```

Avvio:
```bash
petcat -w2 -o grok64.prg -- grok64.bas
x64sc -binarymonitor -binarymonitoraddress ip4://127.0.0.1:6502 -autostartprgmode 1 grok64.prg &
FAKE_LLM=1 python grok64_bridge.py        # poi senza FAKE_LLM, con XAI_API_KEY nel .env
```
Output reale del test (schermo C64 letto con `screen_text`):
```
GROK64 - SCRIVI E PREMI RETURN
> ? CHI HA PROGETTATO LA PROGRAMMA 101?
...
(FINTO) HAI CHIESTO: CHI HA PROGETTATO L
A PROGRAMMA 101?
> ?
```
- **Una sola connessione** al binary monitor per volta: se serve anche "digitare" da un altro script, conviene passare tutto dallo stesso processo. ⚠️ Nel test due connessioni **in sequenza** hanno funzionato. Ogni `mem_get` ferma e riavvia l'emulazione: polling a 4 Hz va bene.
- **Varianti "Grok agisce"**:
  1. Grok genera un `.bas`, lo si tokenizza con petcat e lo si lancia con autostart (`0xDD`) o con `autostart` sul text monitor.
  2. Si legge lo schermo con `screen_text`; su `?SYNTAX ERROR` si rimanda a Grok.
  3. In alternativa, per Grok Vision, uno screenshot con `-exitscreenshot` o con il comando `screenshot` del monitor ⚠️ (non provato).

### 2.5 Caricare programmi su un C64 reale
| Metodo | Come | Stato |
|---|---|---|
| **Ultimate 64 / 1541 Ultimate** (il museo ha un **Ultimate 64 Elite MK2**, vedi `../event/museum.md`) | REST API in rete: `POST /v1/runners:run_prg` | §2.6 ⚠️ |
| **Kung Fu Flash** (cartuccia, SD) | carica CRT, D64, D71, D81, PRG, P00 da SD; la **porta USB** (protocollo EasyFlash 3 USB) permette di inviare PRG da PC mentre gira il launcher; la KFF2 si presenta come porta seriale; serve il tool EF3 USB modificato del repo. Il progetto originale è archiviato su GitHub (dic 2025) e spostato su Codeberg | ✅ (recensione valoroso, theoasisbbs, repo) ⚠️ procedura PC non provata |
| **SD2IEC** | emula un drive IEC (device 8) da SD: si copia il `.prg` sulla SD e sul C64 si fa `LOAD"NOME",8` poi `RUN` | ⚠️ fatto noto, non riverificato |
| **XUM1541 / OpenCBM** | cavo USB verso il 1541 reale, per scrivere floppy veri da PC | ✅ citato su valoroso.it |
| **Keyrah V2/V3** (Individual Computers) | **tastiera C64 → USB**: usare la tastiera originale di un C64 come tastiera per VICE su PC/RPi. Va montata al posto della scheda madre; il produttore sconsiglia di sventrare C64 funzionanti | ✅ (wiki icomp) |
| Iniettare tasti in un C64 reale da PC | crosspoint switch analogico sulla matrice tastiera (es. MT8808) pilotato da Arduino | ⚠️ tecnica nota, nessuna fonte verificata. **Non** farlo su pezzi del museo |
| WiC64 (WiFi ESP32 su userport) | HTTP/HTTPS gestiti dall'ESP32, servizi dedicati; non è un modem AT generico | ⚠️ fonti in disaccordo sulla porta |

### 2.6 Ultimate 64: stessa mailbox, via REST (non provato) ⚠️
REST API dal firmware **3.11**. Password opzionale nell'header `X-Password` (dal firmware 3.12). Endpoint ✅ (doc 1541u):
- `PUT /v1/machine:writemem?address=C100&data=0504`: hex, massimo 128 byte. Per blocchi più lunghi `POST` con allegato binario.
- `GET /v1/machine:readmem?address=033C&length=1`: restituisce dati binari.
- `POST /v1/runners:run_prg` con il PRG allegato (fa reset, carica via DMA ed esegue).
- `PUT /v1/machine:reset`, `PUT /v1/machine:pause` / `PUT /v1/machine:resume`.
- `POST /v1/machine:input`: eventi tastiera e joystick in JSON (**solo U64**; formato da leggere nella doc ⚠️).
```python
import requests
U64 = "http://192.168.1.64"            # IP dell'Ultimate (chiedere allo staff)
H = {}                                 # {"X-Password": "..."} se impostata

class U64Mem:                          # drop-in per mem_get / mem_set del bridge
    def mem_get(self, start, end, resume=True):
        r = requests.get(f"{U64}/v1/machine:readmem", params={"address": f"{start:04X}", "length": end - start + 1}, headers=H, timeout=3)
        r.raise_for_status(); return r.content
    def mem_set(self, start, data: bytes, resume=True):
        for i in range(0, len(data), 128):     # PUT: max 128 byte per chiamata
            chunk = data[i:i + 128]
            requests.put(f"{U64}/v1/machine:writemem", params={"address": f"{start + i:04X}", "data": chunk.hex()}, headers=H, timeout=3).raise_for_status()

def run_prg(path):
    with open(path, "rb") as f:        # ⚠️ formato dell'allegato (raw body o multipart) da verificare
        requests.post(f"{U64}/v1/runners:run_prg", data=f.read(), headers=H, timeout=10).raise_for_status()
```
- Esiste un **MCP server** per Ultimate 64 (`martijn-devrev/ultimate64mcp`): Grok potrebbe usarlo come tool remoto MCP ⚠️ (vedi `../grok-api/agentic-server-tools.md`).
- Per "digitare" senza `machine:input` c'è il trucco classico: scrivere fino a 10 caratteri PETSCII nel buffer di tastiera `$0277` e il loro numero in `$C6` (198). ⚠️ Non provato su U64.

## 3. Olivetti Programma 101 (materiale per prompt e storytelling)
- Progetto guidato da **Pier Giorgio Perotto** (Olivetti, Ivrea), con Giovanni De Sandre, Gastone Garziera, Giancarlo Toppi e Giuliano Gaiti. Design di **Mario Bellini** (Compasso d'Oro). ✅
- **Presentata a New York nell'ottobre 1965** alla fiera BEMA (it.wikipedia); vendita 1966-1971. La en.wikipedia scrive invece "launched at the 1964 New York World's Fair, volume production 1965": **le fonti non concordano** ⚠️. La scheda del museo la data 1966.
- Circa **44.000 unità** (it.wiki) o **40.000** (en.wiki), il 90% in Nord America; prezzo **3.200 $**. ✅ (con discrepanza)
- Memoria a **linee di ritardo magnetostrittive**: 10 registri, circa 240 byte in tutto (1.920 bit); ciclo di 2,2 ms. ✅
- Programmi su **cartolina magnetica** di circa 5×20 cm: due tracce, **120 istruzioni per cartolina**. Linguaggio "di tipo Assembler": 4 operazioni, radice quadrata, valore assoluto, salti condizionati e incondizionati, stampa. ✅
- Stampante integrata da **30 colonne su carta da 9 cm**. ✅
- **NASA** ne usò una decina per i calcoli dell'**Apollo 11**. ✅ (it/en wiki)
- **HP 9100A**: Olivetti contestò la violazione del brevetto e **HP pagò circa 900.000 $ di royalty** (it.wiki). ✅
- Idea: Grok "interpreta" la P101, cioè spiega con la voce di un ingegnere Olivetti del '65, oppure genera un programma P101 "di tipo assembler" stampato in stile 30 colonne. ⚠️ Toccare la P101 reale è improbabile: è un pezzo da museo.

## 4. Telefoni a disco (rotary) + Grok Voice

### Il museo l'ha già fatto: il "chattralino"
*"Integrazione tra un centralino analogico, telefoni a ghiera e ChatGPT, con un'interfaccia completamente conversazionale."* ✅ (comPVter). **Prima domanda allo staff**: come è costruito, e possiamo sostituire ChatGPT con **Grok Voice** (`wss://api.x.ai/v1/realtime`, PCMU 8 kHz per la telefonia, vedi `../voice/telephony-twilio.md`)? Sarebbe il percorso più veloce.

### Da zero: tre architetture
1. **Raspberry Pi nel telefono** (es. "Retro Calling" di Pollux Labs, MIT: Raspberry Pi 4, GPIO per il disco, speech-to-text Whisper e ChatGPT). ✅ Da adattare a Grok Voice.
   - Disco: il contatto impulsi va su un GPIO con pull-up; si contano gli impulsi e una pausa di circa 300 ms chiude la cifra. **"0" = 10 impulsi**, circa 10 impulsi al secondo ⚠️.
   - Gancio: un secondo GPIO.
   - Audio: **scheda audio USB** collegata a capsula e auricolare. ⚠️ I microfoni a carbone dei telefoni antichi vogliono polarizzazione in DC: meglio sostituire la capsula con una dinamica o electret.
2. **ATA/SIP** (es. Grandstream HT801 → Asterisk o SIP → bridge verso Grok Voice), come nel progetto di Zoltan T. (Tom's Hardware). ✅ ⚠️ Verificare che l'ATA decodifichi la selezione a impulsi.
3. **Centralino del museo** (chattralino), se riusabile.

```python
# Raspberry Pi: rotary dial -> digit (gpiozero). Wiring: pulse contact between GPIO17 and GND.
from gpiozero import Button
from threading import Timer
pulse = Button(17, pull_up=True, bounce_time=0.005)
hook  = Button(27, pull_up=True)             # handset lifted = pressed / released depending on wiring ⚠️
count, timer, digits = 0, None, []

def end_digit():
    global count
    digits.append(0 if count == 10 else count); count = 0
    print("number:", "".join(map(str, digits)))   # e.g. "1" -> P101 historian, "64" -> C64 persona

def on_pulse():
    global count, timer
    count += 1
    if timer: timer.cancel()
    timer = Timer(0.3, end_digit); timer.start()

pulse.when_released = on_pulse     # ⚠️ pressed or released depending on NC/NO contact: test with a print
hook.when_pressed = lambda: digits.clear()
input("dial...\n")
```
Idea demo: **ogni numero fa rispondere un personaggio diverso**, cioè un `instructions` diverso nella sessione Grok Voice. Per esempio "101" risponde Perotto, "64" risponde il C64, "1988" il pilota del Flight Simulator.

## 5. MS-DOS / DOSBox (e Olivetti M24 reale)
- DOSBox non ha un'API di controllo. Si interagisce in tre modi: (a) una **cartella montata** (`mount c ~/dos`), in cui Python scrive file `.BAT`/`.BAS` che si lanciano da `autoexec`; (b) la **seriale emulata su TCP**; (c) l'iniezione di tasti a livello di OS (xdotool / pyautogui) ⚠️.
- **Seriale nullmodem** (la via più pulita per un "terminale DOS che parla con Grok"): in `dosbox.conf`, sezione `[serial]`, si mette `serial1=nullmodem port:5000`. Senza `server:` DOSBox fa da **server** e Python si collega in TCP a `127.0.0.1:5000`; `telnet:1` attiva l'interpretazione telnet. ✅ (manuale DOSBox Staging, VOGONS) ⚠️ Nomi delle sezioni e opzioni variano tra DOSBox, DOSBox-X e Staging.
- Lato DOS: un programma terminale, oppure QBasic (`OPEN "COM1:9600,N,8,1" FOR RANDOM AS #1`) ⚠️ (non provato). QBasic non è incluso in DOSBox.
- **Olivetti M24 reale** (nel catalogo del museo): stesso bridge, con un cavo null-modem e un adattatore USB-seriale (`pyserial`) al posto del TCP. ⚠️ Chiedere se la macchina è funzionante e ha una COM libera.
```python
import socket, os
from openai import OpenAI
client = OpenAI(base_url="https://api.x.ai/v1", api_key=os.environ["XAI_API_KEY"])
s = socket.create_connection(("127.0.0.1", 5000))     # DOSBox serial1=nullmodem port:5000
f = s.makefile("rwb")
for line in f:                                         # one question per line from COM1
    q = line.decode("cp437", "replace").strip()
    a = client.responses.create(model="grok-4.3", reasoning={"effort": "none"},
                                instructions="Sei un PC MS-DOS del 1984. Rispondi in max 5 righe, solo ASCII.",
                                input=q).output_text
    f.write(a.encode("cp437", "replace").replace(b"\n", b"\r\n") + b"\r\n\x04"); f.flush()   # \x04 = end of reply
```

## Fonti
- VICE manual, binary monitor (cap. 13): https://vice-emu.sourceforge.io/vice_13.html
- VICE manual, monitor (`keybuf`, `autostart`): https://vice-emu.sourceforge.io/vice_12.html
- VICE manual, opzioni da riga di comando: https://vice-emu.sourceforge.io/vice_2.html · https://vice-emu.sourceforge.io/vice_6.html
- VICE download e sorgenti (ROM): https://vice-emu.sourceforge.io · https://sourceforge.net/projects/vice-emu/files/releases/
- petcat: https://vice-emu.sourceforge.io/vice_16.html · https://www.techtinkering.com/articles/tokenize-detokenize-commodore-basic-programs-using-petcat/
- C64 BASIC V2: https://www.c64-wiki.com/wiki/BASIC
- Ultimate 64 REST API: https://1541u-documentation.readthedocs.io/en/master/_sources/api/api_calls.rst.txt · MCP: https://github.com/martijn-devrev/ultimate64mcp
- Kung Fu Flash: https://github.com/KimJorgensen/KungFuFlash · https://www.valoroso.it/en/kung-fu-flash-for-commodore-64-review/ · https://theoasisbbs.com/kung-fu-flash-2-a-smarter-faster-upgrade-for-c64-users/
- Keyrah: https://wiki.icomp.de/wiki/Keyrah_V2 · https://wiki.icomp.de/wiki/Keyrah_V3
- WiC64 / WLAN C64: https://www.c64-wiki.com/wiki/WLAN · https://misterfpga.org/viewtopic.php?p=87886
- OpenAI forum, client C64 Ultimate: https://community.openai.com/t/proposal-developer-integration-openai-api-client-for-the-commodore-64-ultimate/1366869
- Programma 101: https://it.wikipedia.org/wiki/Programma_101 · https://en.wikipedia.org/wiki/Programma_101 · https://ctrlalt.museum/prodotto/olivetti-programma-101-first-personal-computer/
- Chattralino: https://ctrlalt.museum/compvter-associazione-di-promozione-sociale/
- Telefoni a disco + LLM: https://hackster.io/pollux-labs/retro-calling-chatgpt-on-your-rotary-phone-731b91 · https://www.3dtested.com/raspberry-pi/raspberry-pi-and-chatgpt-bring-ai-conversations-to-your-retro-rotary-phone · https://thingswemake.com/the-rotary-club/
- DOSBox seriale: https://www.dosbox-staging.org/0.83/manual/networking/serial-ports/ · https://www.vogons.org/viewtopic.php?p=138955
