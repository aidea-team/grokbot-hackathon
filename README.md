# grokbot-hackathon

**Grok-driven control of legged robots, with a physics simulator, live visual perception and a safety layer that is independent of the model.**

Built by team **aidea** (Federico Romeo, Federico Rios, Francesco Puddu) for the *Grok Hackathon at the Museum* (Ctrl+Alt Museum, Pavia, 4–5 November 2026, organised with the Grok team at SpaceXSI).

> Brief: take a piece of hardware from the museum, connect it to Grok (API, Voice or Bot), and by Thursday afternoon show something that did not work when you started.

A natural-language instruction such as *"go to the laptop and stop in front of it"* is turned by Grok into a sequence of whitelisted robot primitives. The model never talks to hardware directly: every action goes through a deterministic execution layer that can be stopped locally, regardless of what the model says. The same command path drives a MuJoCo simulator and the real robot, so behaviour can be rehearsed, measured and logged before any hardware moves.

---

## Contents

1. [What is implemented](#1-what-is-implemented)
2. [Architecture](#2-architecture)
3. [Components](#3-components)
4. [Safety model](#4-safety-model)
5. [Perception](#5-perception)
6. [Getting started](#6-getting-started)
7. [Running the applications](#7-running-the-applications)
8. [Configuration](#8-configuration)
9. [Testing and measured results](#9-testing-and-measured-results)
10. [Observability](#10-observability)
11. [Known limitations and unverified items](#11-known-limitations-and-unverified-items)
12. [Repository layout](#12-repository-layout)
13. [Engineering workflow](#13-engineering-workflow)

---

## 1. What is implemented

| Area | Status | Where |
|---|---|---|
| Grok agent loop for the **Unitree Go1** quadruped (perceive → reason → one atomic action → observe) | Implemented; tested in simulator and against a fake UDP dog; **not yet run on the real robot** in this form | `src/chat/`, `src/dog/` |
| **Unitree Go2** support (WebRTC) with a kinematic mock | Implemented; mock only, **never run on a real Go2** | `src/dog/go2_*.py`, `src/chat/go2_bodies.py` |
| Grok agent loop for the **Unitree G1 U2** humanoid (head camera, distance/angle based motion, gestures) | Implemented; simulator and real high-level path, partly unverified on the robot | `src/g1/` |
| **MuJoCo physics simulator** that receives the *same commands as the real robot* | Implemented | `src/sim/`, `src/g1/g1_world.py` |
| **Live perception**: open-vocabulary segmentation plus per-object distance and height | Implemented; validated in simulation and on a simulated stereo head; **not calibrated on the real head** | `src/vision/` |
| Safety envelope: arming, kill switch, watchdog, `HALTED` latch, one action at a time, mock-first | Implemented | `src/chat/real_body.py`, `src/g1/g1_real.py` |
| Structured JSONL logging of every proposal, verdict, execution and latency | Implemented | `logs/` |
| Research notes on the Grok API, Voice, Bot, Imagine and the museum hardware | Written (2026-11-03) | `docs/` |

LLM backend: **Grok only**, through the xAI Responses API (`https://api.x.ai/v1`). No other model provider is used anywhere in the repository.

---

## 2. Architecture

```
                         ┌──────────────────────────────────────────────┐
   operator (browser)    │  Web UI (FastAPI + static HTML)              │
   chat, WASD, STOP ───▶ │  src/chat/app.py (dog)  src/g1/g1_app.py (G1)│
                         └───────────────┬──────────────────────────────┘
                                         │ goal text
                         ┌───────────────▼──────────────┐      frames + odometry
                         │  Agent loop (one per robot)  │◀──────────────────────────┐
                         │  dog_agent.py / g1_agent.py  │                           │
                         └───────┬──────────────▲───────┘                           │
              Responses API call │              │ function_call (tool + args)       │
          (images, state, history)│             │                                   │
                         ┌───────▼──────────────┴───────┐                           │
                         │  Grok  (grok-4.5, low effort)│                           │
                         └──────────────────────────────┘                           │
                                                                                    │
   whitelisted tool call ──▶ ┌──────────────────────────────────────────┐          │
                             │  Execution layer ("body")                │          │
                             │  type checks · one action at a time      │          │
                             │  arming · HALTED latch · watchdog        │          │
                             └───────┬───────────────────────┬──────────┘          │
                                     │ same commands         │                     │
                        ┌────────────▼─────────┐   ┌─────────▼──────────┐          │
                        │ Simulator (MuJoCo)   │   │ Real robot driver  │          │
                        │ SimDriver + world    │   │ Go1 UDP · Go2 RTC  │──────────┘
                        │ physics, cameras     │   │ G1 DDS (high level)│   cameras
                        └──────────────────────┘   └────────────────────┘
   Kill switch (STOP button, Esc, Enter in the terminal) acts on the body directly, bypassing the model.
```

Design principles:

- **Grok plans, hardware executes.** The model only emits calls to a fixed tool whitelist. It never sees raw velocities, joint commands or low-level interfaces.
- **One command language for simulator and robot.** The simulator does not have its own command vocabulary: it consumes exactly what the real driver would send. Results measured in simulation therefore exercise the same code path as the robot.
- **Mock-first.** Every robot starts on the simulator or mock. The real robot is reachable only when a process is started with `--real` *and* the operator arms it explicitly in the UI.
- **The stop path does not depend on the model.** Kill switch, watchdog and the `HALTED` state are implemented in the execution layer.
- **Measure everything.** Latency per phase, tool calls and outcomes are written to JSONL from the first prototype onward.

---

## 3. Components

### 3.1 Agent loop (`src/chat/dog_agent.py`, `src/g1/g1_agent.py`)

A user message starts a *mission*. Each step:

1. wait until the body is idle;
2. capture camera frames (the front camera is mandatory; others are optional);
3. build a prompt with the goal, odometry, the log of previous steps and any new user messages;
4. call Grok with `tool_choice: "required"` and `parallel_tool_calls: false`, so exactly one tool call comes back;
5. execute it, observe physical feedback (blocked, stuck, crash, fall), append to the step log;
6. repeat until the model calls `finish`, a step limit is reached, or the operator stops the mission.

Messages sent while a mission is running are handed to it at the next step. If the model answers in plain text it is treated as the final message. Mission state is epoch-tagged: a stale mission thread exits silently after an abort or reset.

Step limits: Go1 40 steps in simulation and 20 on the real dog (`DOG_MAX_STEPS`, `DOG_MAX_STEPS_REAL`); G1 20 steps, capped to 12 on the real robot (`G1_MAX_STEPS`).

### 3.2 Go1 / Go2 command set (`src/dog/`)

`src/dog/commands.py` is the single definition of tools, validation and execution for the Go1, used by both the real body and the simulator body. Tools: `walk`, `turn`, `stand`, `stand_up`, `lie_down`, `recovery`, `backflip`, `jump_yaw`, `straight_hand`, `dance`, `damping`, `finish`. `src/dog/go2_commands.py` defines the Go2 set (with `strafe`, without `Damp` or flips). The agent picks prompt and tools per robot.

Drivers translate tool calls into the robot protocol:

- `Go1Driver` — Go1 high-level UDP protocol through `free-dog-sdk` (a pure-Python reimplementation of Unitree's `unitree_legged_sdk`, pinned to a tested commit).
- `Go2Driver` / `Go2Link` — WebRTC through `unitree_webrtc_connect` (optional dependency).
- `SimDriver` / `Go2MockDriver` — simulator and kinematic mock behind the same interface.

### 3.3 Execution layer (`src/chat/real_body.py`, `src/chat/hub.py`, `src/chat/both_body.py`)

`RobotHub` owns the active robot and mode and exposes a uniform `body`:

| Mode | Behaviour |
|---|---|
| `mock` (default) | MuJoCo simulator driven with the robot's own commands. |
| `real` | The physical robot. Requires `--real` at process start, an operator-typed `go` in the terminal, a checklist in the UI and an explicit "arm and connect". |
| `both` | The same command goes to the real robot and to the simulator. The real robot decides: a command reaches the simulator only if the real body accepts it. The simulator is a real-time mirror whose pose is shown next to the robot's estimated odometry. |

### 3.4 Simulator (`src/sim/`, `src/g1/`)

**Go1 (`src/sim/dog_world.py`, `scene.py`).** MuJoCo with the `mujoco_menagerie` Go1 model. Legs are PD servos driven by a trot with inverse kinematics; forward speed and yaw are regulated by step amplitude, and heading hold by a yaw controller. Velocity commands run open loop (speed × time, no course correction), and built-in modes (stand-up, backflip, jump-yaw, dance, damping) are triggered on the rising edge and finished by the controller, as the firmware does. A residual stabiliser on the trunk (`INVISIBLE_ASSIST`: 4 N force, 10 Nm attitude torque, 6 Nm yaw torque, against a ~125 N robot weight) remains and is disabled if the robot tips over. Servo damping is deliberately zero (`SERVO_KD`), because with non-zero damping the stairs cannot be climbed.

World: 2 m of empty floor, an 8-step staircase (5 cm risers) leading to a railed platform at 0.4 m, coloured side platforms, five barriers of rising height (0.10–0.60 m), a life-size standing person (1.75 m) and a light rolling ball.

**G1 (`src/g1/g1_world.py`, `g1_policy_lab.py`).** MuJoCo simulation of the Unitree G1 with Unitree's own locomotion policies executed with `onnxruntime` (no PyTorch): `gym12` (12 leg joints, `unitree_rl_gym`) and `lab29` (29 joints, `unitree_rl_lab`, default). The robot is commanded only in high-level velocities (vx, vy, yaw rate) with a ramp and a 0.4 s watchdog; fall detection resets the pelvis below 0.45 m. Velocity limits: vx ±0.8 m/s, vy ±0.4 m/s, ω ±1.0 rad/s. The `desk` scene (`--scene desk`) places a desk with a laptop and mouse and a chair in front of the robot, with position hold when no command is received (measured within 1 cm and 3° over 30 s).

### 3.5 G1 agent (`src/g1/g1_agent.py`)

Tools: `move`, `gesture`, `look`, `finish`. The model never selects a speed. It requests a **distance in metres or an angle in degrees**, and the code walks at a cruise speed above the controller's minimum stepping floor (the real G1 does not step below ~0.2 m/s):

| Action | Cruise | Allowed range |
|---|---|---|
| `walk_forward` | 0.4 m/s | 0.2–3.0 m |
| `walk_backward` | 0.3 m/s | 0.2–2.0 m |
| `strafe_left/right` | 0.25 m/s | 0.2–3.0 m |
| `turn_left/right` | 0.6 rad/s | 10–180° |

A `move` call carries a plan of 1–4 chained steps. Guards: at most 3 consecutive walking moves before the model must look or finish (pure turns do not count), cumulative displacement is reported back to the model, a lost target triggers a bounded search (30° right, 60° left, then stand still), and heading is held with the asked-vs-measured result reported.

### 3.6 Real G1 interface (`src/g1/g1_real.py`)

High-level services only: `LocoClient.Move/StopMove`, FSM transitions limited to a whitelist (3, 500, 501, 706), stand/balance modes, and the arm-action service (23 built-in plus 14 taught gestures, read from the robot with `GetActionList`). It **never** enables developer mode, switches the control service, or publishes low-level commands (`rt/lowcmd`, `rt/arm_sdk`), and never sends `Damp` or `Lie2StandUp`. This is enforced by tests (`tests/test_g1_real_safety.py`). The head camera is the custom stereo head, received as H.264 over UDP (discovery on port 5601), independent of the robot link and usable while the robot is disarmed.

The Mac needs **CycloneDDS 0.10.x** (the robot's series). With 11.x, DDS discovery sees no service and every RPC times out (measured). Build instructions are in [`src/g1/README.md`](src/g1/README.md).

---

## 4. Safety model

| Layer | Mechanism | Independent of the model |
|---|---|---|
| Tool whitelist | Only declared tools can be called; unknown tools and malformed arguments are rejected | yes |
| Type validation | Arguments must be finite numbers of the right type | yes |
| Serialisation | One action at a time; `parallel_tool_calls: false` | yes |
| Arming | Real mode requires `--real`, a terminal `go`, a UI checklist and explicit arming | yes |
| Kill switch | STOP button, Esc in the browser, Enter in the terminal. After a stop the robot stays `HALTED` until a human re-arms it | yes |
| Watchdog | Browser silent for 3 s while the Go1 moves, or 0.4 s for the G1: the robot stops | yes |
| Mission limits | Maximum steps per mission, lower on real hardware | yes |
| Mock-first | Every robot starts in simulation | yes |
| Forbidden commands | G1: no `Damp`, `Lie2StandUp`, developer mode, low-level control. Go2: no `Damp`, no flips | yes |

**Deliberately absent right now.** The numeric guardrails (range limits on distances, speeds and angles for the Go1, geofence, minimum battery) were intentionally removed on 4 November and are being rewritten by the team. Until then the Go1 driver exposes all high-level primitives with type checks only. The first run of any new primitive on the real dog must be done with a person holding the physical remote. `backflip`, `jump_yaw`, `dance` and `damping` have never been run on the real dog, and `damping` switches the motors off.

---

## 5. Perception

Implemented in `src/vision/`, surfaced in the G1 web app under the head camera as three tabs: **camera | objects | depth**.

- **Segmentation.** YOLOE (open vocabulary from text, ~3 fps, CPU via `onnxruntime`), YOLO26 (80 COCO classes, ~10 fps) or SAM 3 in the cloud, sampled every N seconds (1–4 s per frame). Weights are downloaded on first use to `vendor/models/` and checked against SHA-256.
- **Depth.** In simulation: exact, from the MuJoCo depth buffer. On the real robot: OpenCV StereoSGBM on the head's stereo pair (30–55 ms), with the floor plane estimated by RANSAC on the 3D points.
- **Per-object measurement.** The mask is eroded, then the median distance is taken. Height (97th percentile above the floor) and width use only points near the object's depth, so a mask spilling onto the background does not inflate them.

Measured results are in [§9](#9-testing-and-measured-results). Full method, model comparison, calibration procedure and limits: [`docs/vision/live-perception.md`](docs/vision/live-perception.md).

---

## 6. Getting started

Requirements: Python **3.12**, internet access for the first setup. Run the setup **before** joining the dog's Wi-Fi, which has no internet.

```bash
git pull
./scripts/setup.sh
source .venv/bin/activate
```

`scripts/setup.sh`:

1. creates `.venv/` with Python 3.12 and installs `requirements.txt`;
2. clones `free-dog-sdk` into `vendor/free-dog-sdk` at a pinned commit and makes `import ucl` available in the venv;
3. clones `mujoco_menagerie` into `vendor/mujoco_menagerie` at a pinned commit (Go1 and UR5e models);
4. creates `.env` from `.env.example` if missing;
5. runs a smoke test: library imports, one second of simulated physics for Go1 and UR5e, and a mock dog walk.

Then put your key in `.env`: `XAI_API_KEY=...`.

Third-party code lives under `vendor/` (git-ignored) so it is never committed and every machine gets the same revision.

Troubleshooting:

- `python3.12` not found: `brew install python@3.12` (macOS) or `apt install python3.12 python3.12-venv`; or `PYTHON=/path/to/python3.12 ./scripts/setup.sh`.
- `sounddevice` fails (voice scripts): install PortAudio (`brew install portaudio` / `apt install libportaudio2`).
- MuJoCo viewer does not open on macOS: use `mjpython`, not `python`.
- Windows: use WSL.

---

## 7. Running the applications

**Dog chat (Go1 / Go2) and G1 in one app**

```bash
mjpython src/chat/app.py            # macOS (python on Linux/Windows) → http://127.0.0.1:8765
mjpython src/chat/app.py --real     # allows the real robot; a person must type `go` in the terminal
```

The top bar switches robot (Go1 | Go2 | G1 at `/g1/`) and mode (mock · MuJoCo | real | both).

**G1 standalone, with live perception**

```bash
python src/g1/g1_app.py --port 8766 --scene desk          # simulator
python src/g1/g1_app.py --port 8766 --real --iface en0    # real G1, high level only
```

Open `http://127.0.0.1:8766/?head=annotated` for the segmented head camera. Keys: `W/S` forward/back, `A/D` turn, `Q/E` strafe, `Shift` faster, `Space`/`Esc` stop, `R` stand up / reset.

**Hello world: Go1 walks one metre**

```bash
python src/dog/walk1m.py            # mock
python src/dog/walk1m.py --real     # real dog: type `go` to arm; Enter or Ctrl+C stops
```

For the real dog: stand it up, join the `Unitree_Go…` Wi-Fi (password `00000000`), check `ping 192.168.12.1`, keep the physical remote in someone's hand. Details in [`src/dog/README.md`](src/dog/README.md).

**Simulator viewers**

```bash
mjpython src/sim/view.py go1        # or ur5e; plain python on Linux/Windows
python src/sim/check_mujoco.py      # headless check
```

**Why `free-dog-sdk` and not the official SDK.** It is a pure-Python reimplementation of the same high-level Go1 UDP protocol, installs without compiling and is pinned to commit `0ececb5`. It exposes every high-level mode (`MotorModeHigh`: `VEL_WALK`, `STAND_UP`, `RECOVERY`, `BACKFLIP`, `DANCE1/2`, `DAMPING`, …) but, unlike the official SDK, **has none of its safety features**. What limits the commands is our own driver. If it misbehaves on the real Go1, plan B is the compiled `unitree_legged_sdk` bindings.

---

## 8. Configuration

All secrets live in `.env` (git-ignored). Never commit keys, Twilio tokens or the Go2 AES key.

| Variable | Purpose | Default |
|---|---|---|
| `XAI_API_KEY` | xAI API key | required |
| `GROK_MODEL` | Model id for the agents | `grok-4.5` |
| `GROK_REASONING_EFFORT` | `none`/`low`/`medium`/`high` | `low` |
| `DOG_MAX_STEPS`, `DOG_MAX_STEPS_REAL` | Go1 step limit per mission | 40, 20 |
| `G1_MAX_STEPS` | G1 step limit per mission | 20 (12 real) |
| `GO2_ADDR`, `GO2_AES_KEY` | Go2 address and owner AES key (firmware ≥ 1.1.15) | empty |
| `G1_CAMERA_PORT` | UDP port for the G1 head stream | 5601 |

The default model was chosen on 2026-11-05 from a three-call benchmark with one image and a forced tool call (`parallel_tool_calls=false`); all candidates returned a valid tool call: `grok-4.3` effort `none` ~2 s, `grok-4.20-0309-non-reasoning` ~2 s, **`grok-4.5` low ~3 s**, `grok-4.7` low ~5 s, `grok-4.6` low ~6 s, `grok-4.3` low ~10 s. The `openai` Python package is used purely as an HTTP client with `base_url` pointed at `https://api.x.ai/v1`. Settings such as camera set, resolution, JPEG quality and reasoning effort are adjustable live from the dog UI and apply at the next step.

---

## 9. Testing and measured results

Tests are standalone scripts and never touch real hardware (they use mock drivers or a fake UDP dog):

```bash
python tests/test_real_safety.py       # Go1: unknown tools, malformed args, all primitives, kill switch, watchdog, arming
python tests/test_chat_modes.py        # mock/real/both switching, confirmation, stop = HALTED until re-arm
python tests/test_sim.py               # simulator receives the real dog's commands; world, stairs, primitives
python tests/test_go2.py               # Go2 tools, mock driver, mode switching, real link failure handling
python tests/test_g1.py                # G1 simulator
python tests/test_g1_agent.py          # G1 agent: move guards, gestures, lost-target search, heading hold
python tests/test_g1_real_safety.py    # G1 real: only whitelisted high-level calls, no Damp / low level
python tests/test_vision_sim.py        # per-object geometry vs ground truth
python tests/test_vision_stereo.py     # stereo vs ground truth
python tests/test_g1_stereo_stream.py  # head discovery → RTP H.264 → stereo, with a fake head
```

Known flake: `test_sim.py`'s stairs test fails intermittently (about 2 runs in 8, also on `main`).

**Perception accuracy** (simulation, `desk` scene, exact masks):

| Object | Measured height | True height | Distance in `desk` start pose |
|---|---|---|---|
| Laptop (screen edge) | 0.95 m | 0.96 m | 2.06 m |
| Chair (backrest) | 0.84 m | 0.86 m | 1.71 m |
| Desk | 0.75 m | 0.75 m | 1.91 m |

**Stereo against ground truth** (rendered pairs, 60 mm baseline, 75° FOV): median frame error 1.6–1.8 %; per object within 3.1 % in three views (laptop 2.09 m vs 2.09 m, desk 1.97 m vs 1.95 m, chair 0.98 m vs 0.97 m). Dark, uniform surfaces are the worst case (+8 % on the first scene's black office chair).

**Real-robot path with a fake head** (same protocol, no robot): depth on 59 % of pixels, 38 ms matching, camera height 1.261 m against 1.25 m true, tilt 14.0° against 14.0° true.

**Throughput** (i7-1360P, WSL2, no GPU): YOLOE 220–350 ms per frame, YOLO 70–145 ms, StereoSGBM 30–55 ms; SAM 3 1–4 s per frame (cloud), hence sampled. Neural stereo models were measured at 0.4–2.6 s per frame on the same CPU and rejected for live use.

**G1 locomotion** (simulator): commanded 0.5 m/s gives ~0.44 m/s, 0.8 gives ~0.73 m/s, 0.8 rad/s gives ~41°/s.

---

## 10. Observability

Every mission is logged as JSON Lines under `logs/`:

- `chat-YYYYMMDD.jsonl` — mission start (goal, mode, robot, model, effort, settings), each step (action, thought, latency, outcome), per-step timing (wait / capture / API / execution), mission end (steps, average and total time per phase), LLM errors;
- `dog-*.jsonl` — driver-level commands, verdicts and kill events.

This is the basis for the quantitative results required by the hackathon rules (baseline comparison, success and failure counts, latency).

---

## 11. Known limitations and unverified items

Everything below is explicit because none of it has been confirmed on hardware.

- **No snippet has been verified end to end against the live xAI API** until a key is available; on first use, check the model ids and formats against [`docs/grok-api/`](docs/grok-api/) and correct the docs if they differ.
- **Go1 numeric guardrails are removed on purpose** (see [§4](#4-safety-model)); the validator is being rewritten. Odometry is open loop.
- **Go1 primitive durations** in `src/dog/driver.py` are estimates; `backflip`, `jump_yaw`, `dance`, `damping` never ran on the real dog.
- **Go2** has never been connected to a real robot; the `VERIFY` points are listed in [`src/dog/README.md`](src/dog/README.md).
- **G1 on the real robot:** new and taught gestures, distance-based `Move` from chat (start-up time `STARTUP_S` needs calibration) and whole-body stored motions (FSM 550x, not implemented) are unverified. FSM 802/501 and mode `ai` were read from the robot.
- **G1 stereo head is uncalibrated.** Without `src/g1/stereo_calib.json` the app assumes a 75° FOV and a 60 mm baseline and labels the result "stereo (not calibrated)". Calibrate on site with `scripts/g1_stereo_calibrate.py` and a tape measure. Stereo error grows with the square of distance (about 2 cm at 1 m, 6–8 cm at 2 m, 25–35 cm at 4 m, theoretical). Featureless surfaces (lit screens, white walls, matt black plastic) degrade it.
- **Perception limits:** occluded objects are measured only where visible; SAM 3 results refer to the analysed frame and age while the robot moves; with `gym12` the simulated G1 drifts even when idle (use `lab29`).
- **Licences:** YOLO/YOLOE weights are AGPL-3.0 (Ultralytics).
- **Out of scope for this build:** Grok Voice, telephony and the robot arm (UR e-Series via `ur_rtde`) are researched in `docs/` but not implemented here. The `@bot` tag on X does not work from the EU.

---

## 12. Repository layout

```
src/
  llm_provider.py     Grok client configuration (single provider)
  chat/               Dog web app, agent loop, execution layer, hub, both-mode body, settings
  dog/                Go1/Go2 commands and drivers, camera relay, hello world, README
  sim/                MuJoCo Go1 world, scene, cameras, SimDriver/SimBody, viewers
  g1/                 G1 simulator, locomotion policies, agent, real interface, web app, README
  vision/             Segmentation backends, depth (simulated and stereo), live pipeline
scripts/              setup, G1 FSM/walk tools, stereo calibration, fake G1 head, YOLOE tools
tests/                Standalone test scripts (no hardware)
docs/                 Research: Grok API, voice, bots/Imagine, hardware, event rules, ideas, perception
vendor/               Third-party code and model weights (git-ignored)
logs/                 JSONL run logs (git-ignored)
```

Documentation map: start from [`docs/README.md`](docs/README.md). Most relevant: [`docs/hardware/llm-robot-architecture.md`](docs/hardware/llm-robot-architecture.md) (LLM → robot architecture), [`docs/vision/live-perception.md`](docs/vision/live-perception.md), [`docs/grok-api/`](docs/grok-api/), [`docs/event/tracks.md`](docs/event/tracks.md). Context for Claude Code and Grok Build is in [`CLAUDE.md`](CLAUDE.md).

---

## 13. Engineering workflow

- `main` must always work. Use short-lived branches, `git pull --rebase origin main` before pushing, and merge often.
- One directory per component to avoid conflicts.
- Never commit `.env`, keys or tokens, and never commit anything from `vendor/`. Commit logs only when they are evidence for the jury.
- Docs are in Italian, code, identifiers and technical comments in English. If something in `docs/` proves wrong on site (hardware model, endpoint, behaviour), fix the file.

**Event rules that shape the deliverable:** Grok must be essential; a minimal demo on a new jury case by Thursday 16:00; the repository must contain a README, data or fixtures, at least one result against a baseline, and the limits. Principles: reproducibility, evidence first, human in the loop, security by design, realistic scope.
