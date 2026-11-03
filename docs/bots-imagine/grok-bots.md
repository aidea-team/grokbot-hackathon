# Grok Bot (il "bot framework")

> Verificato il **2026-11-03** su docs.x.ai/grok-bot/* (versione `.md` delle pagine), x.ai/news/introducing-grok-bot e docs.x.ai/x-subscription/*.
> ⚠️ = non verificato / da confermare all'evento.

## TL;DR

- **Grok Bot non è un SDK né un'API**: è un **prodotto/app** (desktop macOS/Windows/Linux + iOS/Android) in cui crei "Bot" = teammate AI con nome, ruolo e memoria, che lavorano su un **computer cloud persistente** (browser, filesystem, terminale). Lo configuri **scrivendogli in chat**, non con un workflow builder.
- Lanciato il **11 agosto 2026** (beta). Gira nel cloud di **Cursor**; si accede con un **account Cursor** (Grok Bot e Cursor sono nello stesso ecosistema).
- **Integrazione programmatica possibile** (quella utile all'hackathon), anche senza API "di bot":
  1. **Routine con trigger webhook**: un tuo script/hardware fa `POST` a un URL con `Authorization: Bearer <key>` e il Bot parte.
  2. **MCP server** aggiunto per URL o comando: il Bot può chiamare i *tuoi* tool (es. "muovi il braccio robotico") esposti come MCP.
  3. **Esecuzione di comandi sul tuo laptop** (con approvazione): il Bot può lanciare script sulla macchina collegata all'hardware.
  4. Trigger da **email** (indirizzo `@mail.grokbot.com`), **Slack**, GitHub, Linear, Sentry, PagerDuty, **schedule**.
- **X**: lettura pubblica di X inclusa (search, post, menzioni di account, trend) senza collegare un account. **Tag @bot su X NON disponibile per account con paese UE** → in Italia di fatto non usabile.
- **Accesso**: piani **Premium ($30/mese), Super, Ultra** di "The X Subscription", oppure piani Cursor a pagamento legacy, o SuperGrok/X Premium+ collegati. A volte c'è un **trial** a credito (7 giorni). ⚠️ Non risulta che i "API credits" dell'hackathon includano Grok Bot.
- Il Bot sa anche **generare immagini e video** (Grok Imagine) e fare **voice chat**.

## Cos'è, in pratica

| Aspetto | Dettaglio (da docs) |
|---|---|
| Unità | "Bot": un teammate con nome, foto, un lavoro principale, memoria propria |
| Computer | **Uno per account**, condiviso da tutti i tuoi Bot (file, cookie, login, credenziali CLI condivisi). Ogni Bot ha il proprio "schermo"; un Bot fa un computer-use task alla volta. Isolamento forte tra utenti (hardware-isolated) |
| Workspace | `/workspace` per file durevoli. `node_modules`/venv **non** vengono salvati: reinstallare dopo update/recover/reset |
| Dove gira | Cloud di Cursor; continua a lavorare a laptop chiuso |
| Interfacce | App desktop, app mobile (iOS 18+, Android 9+), **X Chat** (rollout graduale), Slack (Bot condivisi), tag **@bot** su X |
| Modello | "Grok Bot manages model selection, so there is no model picker" |
| Memoria | Preferenze stabili, ruolo, sommari del lavoro precedente; separata per Bot (salvo nome/fuso orario dell'utente) |
| Coordinamento | Bot in parallelo, si scrivono tra loro, group chat, handoff di task |
| Apprendimento | "Teach a task": registri fino a **10 minuti** di interazione col browser → bozza di skill |
| Sicurezza | Approvals + Auto Review prima di azioni esterne; credenziali in **Vault** / 1Password / Secure Form (il Bot non vede le password) |

## Come si crea un Bot (passi dalla guida ufficiale)

1. Installa l'app da https://x.ai/bot o dal Cursor dashboard (https://cursor.com/dashboard/bot).
2. **Sign in** con account Cursor (o "Sign in with Grok" per seat Grok Business). Se l'accesso viene da SuperGrok/X Premium+: **Link Grok Account**. Account in "Privacy Mode (Legacy)" devono passare a Privacy Mode.
3. Il primo Bot si chiama **"Grok Bot"**; per aggiungerne: **+ → Create a Bot** → nome → Create.
4. Primo messaggio: **un lavoro principale** + "remember this". Esempio ufficiale: *"Your job is product performance... Never change production settings. Remember this for future work."*
5. Dai un task; quando serve login, il Bot usa Vault/password manager o chiede via Secure Form; per SSO/CAPTCHA/passkey ti passa il computer ("Open computer").
6. Quando il processo è stabile → salvalo come **skill**, poi automatizzalo con una **routine**.

Alcune cose restano **solo desktop**: teach-by-demonstration, test delle routine, update del computer.

## Skill e routine (= trigger, schedule, tool custom)

### Skill
- Istruzioni riutilizzabili (passi, regole, output atteso, cosa richiede approvazione). Libreria privata condivisa da tutti i tuoi Bot. Si richiamano per nome; `@` per Bot, gruppi, routine e app.
- Si possono pubblicare al team (serve descrizione).

### Routine
- Dice **a un Bot** quando eseguire un workflow: **schedule** ("every weekday at 8:00 AM", "every 2 hours") o **evento**: messaggio Slack, evento GitHub/Linear/Sentry/PagerDuty, **email** all'indirizzo del Bot, **webhook**.
- Si crea chiedendolo in chat al Bot proprietario. Una nuova routine **non parte alla creazione**: aspetta il prossimo orario; usa **Test** per lanciarla subito (il test fa lavoro reale).
- Fuso orario: Settings → Bot → Timezone.

### Webhook (punto di aggancio per l'hardware)
Chiedi al Bot di aggiungere un trigger webhook alla routine; poi su desktop la routine mostra la sezione **Webhook** con:
- **POST to** → URL
- **key** → segreto, da inviare come `Authorization: Bearer <key>`
- **header** → header completo pronto da copiare

Invii `POST` con body JSON opzionale; il Bot riceve il body insieme all'istruzione della routine. **`200` = run accettato e avviato, non concluso**; il risultato compare nella chat del Bot. Qualsiasi altro codice = run non partito (routine in pausa o key vecchia). Snippet in [code-samples.md](code-samples.md#8-grok-bot-trigger-webhook-da-hardware).

### Limiti routine (docs)
| Limite | Valore |
|---|---|
| Routine per Bot | max **50** |
| Run history conservata | ultimi **20** run per routine |
| Distanza minima tra schedule | **5 minuti** |
| Run/ora, tutte le routine | **300** |
| Run/ora, singola routine | **200** (oltre: `Automation run rate limit exceeded`, nessun retry automatico) |
| Known issue | limite condiviso tra tutti gli utenti Grok Bot può far fallire run anche sotto soglia |

Ogni run consuma usage: un trigger troppo largo (es. "ogni messaggio") può bruciare una settimana di usage in un giorno.

## Connettori e "tool custom"

- **Connected apps** (OAuth tenuto sul backend Cursor, il Bot non vede i token): Gmail, Google Calendar/Drive/Sheets/Docs/Slides, Slack (posta *come l'utente*), Notion, Linear, GitHub, 1Password, Outlook, SharePoint, Zoom (bug noto errore 4700), Stripe Link, Tailscale, QuickBooks, Workday, WhatsApp Business, Zoho, ecc. Elenco completo: catalogo **Connect apps** nell'app.
- **MCP server custom**: *"A Bot can also add an MCP server that isn't in the catalog, by URL or by a command that runs on its computer"*. Un server avviato da comando è disponibile anche agli altri tuoi Bot. Server su rete privata o con CA privata richiedono approvazione. → **Questo è il modo per dare al Bot "tool custom"**, es. un MCP server sul laptop collegato al robot esposto via tunnel (ngrok/Cloudflare Tunnel). ⚠️ Pattern non testato: le docs dicono che le connessioni MCP partono dal cloud Cursor, quindi l'endpoint deve essere raggiungibile da internet.
- **Esecuzione sul computer locale**: Settings → Computer → Your computer → **Execution on this computer** = *Ask every time* (default) / *Always allow* / *Never allow*. Il primo comando mostra "Allow Grok Bot and all Bots to run commands on your local computer?". → Il Bot può lanciare script sul laptop collegato all'hardware.
- **Route traffic through this computer**: il traffico web del computer cloud esce dal tuo desktop (IP tuo). Indirizzi privati/VPN restano bloccati salvo allowlist org.
- **Email propria**: un indirizzo per account `nome@mail.grokbot.com` (permanente, non rinominabile), alias `nome+tag@...`. Le email in arrivo **non** svegliano il Bot da sole: serve una routine con filtro mittente. Le email inviate da una routine restano **bozza** finché non premi Send (niente invio unattended).

## Integrazione X (dentro Grok Bot)

- **Lettura pubblica senza account**: *"Bots can search and read what's public on X without you connecting an X account"* — cercare post, aprire un post da link, leggere post e **menzioni di un account**, chi ha quotato/repostato, contare post recenti, trend e news. Read-only, non agisce come te.
- **X for Grok Bot plugin** (opzionale, da Connect apps): DM, bookmark, home timeline, like; *"the X plugin needs X API credits on your X developer account"* → costi X API pay-per-use (vedi [x-integration.md](x-integration.md)). ⚠️ Le docs non dicono esplicitamente se il plugin permette di **pubblicare** post.
- **Tag @bot su X**: rispondi/posta "@bot fai X" → il tuo Bot principale riceve il post (+ post a cui rispondi + quotati, foto incluse), @bot risponde pubblicamente con una conferma; il lavoro resta nella chat del Bot.
  - Requisiti: account Grok con X collegato (grok.com → Settings → Account → Connect 𝕏), accesso Grok Bot sullo stesso account, almeno un Bot proprio.
  - **Non disponibile** per account X con paese registrato in **UE**, UK, Australia, Islanda, Liechtenstein, Norvegia (conta il paese su X, non VPN/posizione).
  - @bot tace se: il post tagga anche @grok, contiene video/GIF, non passa moderazione, usage esaurito, ecc.
- **X Chat**: puoi chattare con i tuoi Bot dentro X Chat (rollout graduale, solo account personali).

## Immagini, video e voce nel Bot

- Immagini: 1:1, 4:3, 3:4, 16:9, 9:16; non per grafici (per quelli chiedere una "page").
- Video: da testo, da 1 immagine (primo frame), da 2 immagini (inizio/fine; uguali = loop), fino a 14 reference image, fino a 4 immagini a momenti fissi. **1–15 s (default 6)**, **480p** salvo richiesta **720p**, MP4, input JPEG/PNG/WebP fino a ~35 MB totali. "Creating a video can take a few minutes."
- **Voice chat** live con un Bot (desktop e mobile), voce/velocità/lingua configurabili, transcript a fine chiamata. ⚠️ Le docs non dicono quale modello voce usi (presumibilmente Grok Voice).

## Accesso, prezzi, crediti

| Via di accesso | Grok Bot incluso? |
|---|---|
| The X Subscription **Free** / **Plus** ($8/mese) | **No** |
| The X Subscription **Premium** ($30/mese, $300/anno) | Sì (pool settimanale condiviso con Grok e Cursor, "4x") |
| **Super** ($100/mese) / **Ultra** ($200/mese) | Sì, pool più grandi (15x / 50x) |
| Legacy Cursor Pro / Pro+ / Ultra / Teams | Sì |
| Link SuperGrok / SuperGrok Plus / Heavy / X Premium+ | Sì (non SuperGrok Lite né Grok Enterprise) |
| Seat Grok Business self-serve | Sì ("Sign in with Grok") |
| **Trial** | "Start Trial" quando offerto: credito d'uso + finestra 7 giorni; un task grosso può esaurirlo |

- Usage misurato su **agent steps e token**, reset settimanale; oltre il pool: on-demand / Additional Usage credits.
- Al lancio (11/08/2026) era "in beta" con usage separato; ora sotto The X Subscription usa il pool condiviso.
- ⚠️ **Crediti hackathon**: il sito dice solo "API credits provided". Altre "Grok Bot Build Night" SpaceXAI (es. UC Davis, 3/09/2026) davano **"One month of Cursor Pro, with Grok Bot included"**. Per Pavia non confermato: **chiedere al kick-off** se c'è un codice Cursor Pro/Grok Bot.

## Limiti e gotcha rilevanti per la demo

- **Non c'è un'API per creare/pilotare Bot da codice** (esiste solo un *Admin API* / *Organization API* Cursor per team ed enterprise, per gestione computer/membri). L'ingresso programmatico è via webhook/email/Slack/MCP.
- Il risultato di un webhook arriva **in chat**, non come risposta HTTP: per chiudere il loop verso l'hardware serve che il Bot chiami un tuo MCP server, esegua un comando locale, o scriva su un servizio che il tuo codice legge (Sheets, Slack, email, file).
- Siti possono bloccare traffico da cloud → "Route traffic through this computer".
- Operazioni distruttive/esterne passano da approvazione (Auto Review): prevedere che durante la demo compaia una card di approvazione.
- Per demo dal vivo affidabili: routine strette, input sicuri, `Test` prima.
- 1 voice chat alla volta; voice chat non nei group chat.

## Idee concrete per l'hackathon (derivate dalle capability documentate)

- **"Custode del museo"**: sensore/robot → webhook → routine Bot che analizza l'evento, genera un'immagine/video Imagine e prepara un post (bozza) o un'email.
- **Robot con "ufficio"**: il Bot gestisce calendario/email/Slack del team e, via MCP server esposto dal laptop, invia comandi al braccio robotico.
- Se serve qualcosa di **completamente programmabile e in tempo reale**, meglio usare direttamente la **Grok API** (function calling + tool `x_search` + Imagine) e mostrare Grok Bot come "orchestratore" asincrono.

## Fonti

- https://docs.x.ai/grok-bot/overview
- https://docs.x.ai/grok-bot/get-started
- https://docs.x.ai/grok-bot/skills-routines-and-automations
- https://docs.x.ai/grok-bot/computer-and-apps
- https://docs.x.ai/grok-bot/tag-on-x
- https://docs.x.ai/grok-bot/chat-and-collaboration
- https://docs.x.ai/grok-bot/files-and-results
- https://docs.x.ai/grok-bot/approvals-security-and-privacy
- https://docs.x.ai/grok-bot/settings-and-notifications
- https://docs.x.ai/grok-bot/faq
- https://docs.x.ai/grok-bot/teams-and-enterprises
- https://docs.x.ai/x-subscription/grok-bot
- https://docs.x.ai/x-subscription/pricing
- https://docs.x.ai/developers/release-notes (voce "Grok Bot", agosto 2026)
- https://x.ai/news/introducing-grok-bot (11 agosto 2026)
- https://luma.com/bqjdbblj (esempio Build Night UC Davis: "One month of Cursor Pro, with Grok Bot included")
- https://help.x.com/en/using-x/about-bot (citato dalle docs, non letto direttamente ⚠️)
