# @sauti/hub-voice: the hub's voice agent (Lane 10, Domain)

The tourist calls the farm's number. One computer speaker at the tourism office answers in Swahili or English, checks availability, takes a visit **request**, and files it for Noor, who confirms it herself. While the caller is still on the line, a live browser view prepares the change on the listing with the banner **WAITING FOR NOOR'S APPROVAL · A**. Nothing is saved until her approval arrives.

Max's plan (room #47625) in order: phone and text booking first, GetYourGuide later. Carter's rules (room #47595, #47624): all AI local on the hub PC; Twilio and LiveKit only carry audio and SMS; a spoken or texted "yes" is never approval; no keys in git, the room or logs; the repo is public.

```
 caller ──SIP──▶ LiveKit (self-hosted) ──▶ livekit-agents worker "sauti-hub"  (ONE speaker)
                                               │  STT faster-whisper · LLM Gemma 4 E4B (llama.cpp/Ollama) · TTS Chatterbox as "tts-1"
                                               │  all via OpenAI-compatible base_url on 127.0.0.1
                        every caller turn ─────┼──▶ sidecars (parallel, time budget, fail-open, READ-ONLY)
                                               │     language · safety/tone · booking facts (+ hub availability)
                                               │     translation aid · escalator · preparer (live view)
                                               │          └──▶ append-only, redacted BLACKBOARD ◀── speaker reads via ONE tool call
                        speaker tools ─────────┼──▶ farm_facts · check_availability (read)
                                               └──▶ file_booking_request  (the ONE write: a REQUEST for Noor)
                                                         │
                                               apps/hub (@sauti/core): proposal + read-back SMS to Noor's enrolled phone
                                               Noor: "NDIYO A 4821" (one-time code) or Sauti PIN in the app
                                                         │
                                               preparer process: PreparerGate ok? ──▶ click Save. Otherwise never.
```

## What is enforced, and where

| Rule | Where |
|---|---|
| The agent never confirms; it files a request Noor approves | `policy.py` (speaker rules), `hubclient.HubActions.file_booking_request` returns `pending_owner` only; the hub creates the proposal through `@sauti/core` |
| Sidecars cannot speak, send, call, commit or file | `sidecars/base.SidecarContext` has only `settings`, `hub` (read-only client with exactly `availability` and `farm_facts`), `board`, `now_ms`, `call_id`; `tests/test_sidecars.py` |
| Sidecars are bounded and fail-open | `run_sidecars`: one budget, timeouts and errors recorded, the call carries on |
| The blackboard is append-only and holds no phone number or code | `blackboard.py` + `redact.py`; defence in depth raises `RedactionError` rather than record; `tests/test_blackboard.py` |
| Numbers the speaker says come from approved facts | `farm_facts` tool reads the hub's current farm sheet; the booking sidecar's facts carry exact quotes; the translation aid has a number guard and is "never counted" |
| The live view prepares during the call but never saves without a matching approval | `sidecars/preparer.py`: `PreparerDisplay` has only `prepare`; `PreparerGate.may_commit` requires a contract-valid approval record, `approved`, same digest as the envelope (recomputed) and the prepared change, same action, before `valid_until`, never twice; `tests/test_preparer_gate.py`, `tests/test_live_view.py` |
| Caller ID is not identity | not recorded, not used; `policy.py` rule 3 |
| Who speaks, from which language | `sidecars/language.py`: deterministic stopwords, Bantu look-alikes are `und`, unsupported language or persistent `und` = a person calls back |

## Run

Offline, nothing installed but Python (this is what the tests and the demo screen use):

```
cd apps/hub-voice
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt      # or .venv/bin/pip
python -m pytest tests -q
python -m hub_voice.simulate fixtures/calls/booking_sw.jsonl               # transcript in, blackboard out (runtime/, gitignored)
```

Live, on the hub PC:

```
pip install "livekit-agents[openai,silero,turn-detector]==1.8.4" "livekit-api>=1.2.1" python-dotenv
cp .env.example .env    # LiveKit self-hosted URL + key/secret, local model server URLs, hub URL + token
python -m hub_voice.agent download-files   # silero + turn detector ONNX, once
python -m hub_voice.agent console          # local microphone test, no LiveKit server
python -m hub_voice.agent dev              # connect to LiveKit; SIP dispatch rule names agent "sauti-hub"
```

Model servers (all local): faster-whisper with an OpenAI-compatible `/v1/audio/transcriptions`; llama.cpp or Ollama serving Gemma 4 E4B at `/v1/chat/completions`; a Chatterbox wrapper at `/v1/audio/speech` that accepts model `tts-1` and returns wav or pcm at 24 kHz (the plugin sends `tts-1`; the voice name is yours). With no model URLs configured the worker refuses to speak and says so; use `simulate`.

Telephony, after Carter's Twilio and LiveKit setup: inbound via SIP trunk + dispatch rule → `sauti-hub`; outbound calls to Noor (alert clips, read-back) via the LiveKit outbound trunk from the hub; SMS through the hub's Twilio adapter. The hub's F1/F2 (no reply to unknown senders, daily caps) land before the real number is wired.

## Interfaces this app expects from apps/hub

`GET /v1/availability?date=YYYY-MM-DD` → `{date, capacity, confirmed, remaining, open}` (the core's `checkCapacity`); `GET /v1/farm` → the approved farm sheet; `POST /v1/proposals` with `{tenant_id, source:{channel:"voice", call_id}, booking:{date, party_size, visitor_name, language}, note}` → `{ref, action_id, status:"pending_owner"}`. Bearer token from `HUB_TOKEN`. Until they exist the client answers from `fixtures/` and appends to `runtime/proposals.jsonl`.

The preparer process (codex-mobile, `apps/hub-voice/preparer/**`) implements `PreparerDisplay.prepare(ref, change, banner)` with a headed Playwright browser against a local mock extranet, and calls `PreparerGate.commit(...)` only when the hub reports an approval; the gate is the only path to Save.

## Files

| File | Owns |
|---|---|
| `hub_voice/agent.py` | the livekit-agents worker: session wiring, four speaker tools, event logging; livekit imported lazily |
| `hub_voice/policy.py` | disclosure, handover lines, the speaker's hard rules |
| `hub_voice/blackboard.py`, `redact.py` | append-only per-call record, redaction, the speaker view |
| `hub_voice/sidecars/base.py` | `Turn`, `Advice`, `SidecarContext` (read-only), `run_sidecars` (budget, phases, fail-open) |
| `hub_voice/sidecars/{language,safety,booking,translation,escalator,preparer}.py` | the six sidecars; `preparer.py` also holds `PreparerGate` and the `PreparerDisplay` port |
| `hub_voice/hubclient.py` | `HubReadOnly` (queries) and `HubActions` (file a request), simulated twins |
| `hub_voice/simulate.py` | offline transcript driver |
| `fixtures/` | synthetic farm facts, calendar and a sample call; `tests/` | the rules above as tests |

Generated Swahili in fixtures is unreviewed and says so. No real phone number appears anywhere in this app.
