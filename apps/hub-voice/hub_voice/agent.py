"""The livekit-agents worker "sauti-hub": the only voice on the call.

STT, LLM and TTS are OpenAI-compatible servers on the hub PC (faster-whisper,
llama.cpp or Ollama serving Gemma 4 E4B, a Chatterbox wrapper that answers as
model "tts-1"); LiveKit and Twilio carry only audio. Silero VAD + the multilingual
turn detector; interruptions allowed with no minimum word count. The speaker has
four tools: consult_sidecars (read), farm_facts (read), check_availability (read)
and file_booking_request (the ONE write: a request Noor approves). Sidecars have
none.

Run:  python -m hub_voice.agent download-files   (once)
      python -m hub_voice.agent console           (local mic, no LiveKit server)
      python -m hub_voice.agent dev | start       (LIVEKIT_URL/API_KEY/API_SECRET in env)
Dispatch: a SIP dispatch rule with agent_name "sauti-hub" (explicit dispatch).

livekit imports are inside main() so the sidecar and gate modules can be tested
without the agent stack installed. API checked against livekit-agents 1.8.4.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from .blackboard import Blackboard
from .config import Settings, load_settings
from .hubclient import BookingRequest, HubActions, HubError, HubReadOnly
from .policy import DISCLOSURE_EN, DISCLOSURE_SW, speaker_instructions
from .redact import redact_text
from .sidecars import PreparerDisplay, PreparerSidecar, SidecarContext, Turn, default_sidecars, run_sidecars

log = logging.getLogger("sauti-hub")


class CallState:
    """Per-call wiring: blackboard, sidecars, hub clients, turn counter."""

    def __init__(self, settings: Settings, call_id: str, display: PreparerDisplay | None = None) -> None:
        self.settings = settings
        self.call_id = call_id
        self.board = Blackboard(call_id=call_id, sink_path=settings.runtime_dir / "blackboards" / f"{call_id}.jsonl")
        self.hub_ro = HubReadOnly(settings.hub_base_url, settings.hub_token(), settings.fixtures_dir)
        self.hub_actions = HubActions(settings.hub_base_url, settings.hub_token(), settings.runtime_dir, settings.tenant_id)
        self.sidecars = default_sidecars(display)
        self.preparer: PreparerSidecar = next(s for s in self.sidecars if isinstance(s, PreparerSidecar))
        self.turns = 0
        self.language_hint: str | None = None

    def ctx(self) -> SidecarContext:
        return SidecarContext(settings=self.settings, hub=self.hub_ro, board=self.board, now_ms=int(time.time() * 1000), call_id=self.call_id)

    async def on_caller_turn(self, text: str, is_final: bool = True) -> str:
        """Run the sidecars on a caller turn; returns the speaker view. Never raises."""
        self.turns += 1
        self.board.append("caller", "turn", {"turn": self.turns, "text": text, "final": is_final})
        turn = Turn(index=self.turns, text=text, language_hint=self.language_hint, is_final=is_final)
        report = await run_sidecars(self.sidecars, turn, self.ctx(), self.board)
        lang = next((a for a in report.advices if a.source == "language"), None)
        if lang and lang.data.get("action") == "ok":
            self.language_hint = str(lang.data.get("lang"))
        return self.board.view_for_speaker()


def build_agent_classes(state: CallState):  # noqa: ANN201 - returns livekit classes built lazily
    from livekit.agents import Agent, RunContext, ToolError, function_tool

    class SautiSpeaker(Agent):
        def __init__(self) -> None:
            super().__init__(instructions=speaker_instructions(state.settings.languages))

        @function_tool()
        async def consult_sidecars(self, context: RunContext) -> str:
            """Read the sidecars' advice for the caller's latest words: language, availability facts, safety and tone cues, handover recommendation. Call this first every turn."""
            return state.board.view_for_speaker()

        @function_tool()
        async def farm_facts(self, context: RunContext) -> dict[str, Any]:
            """The owner-approved facts about the farm: price per person, open days and hours, directions, what is included. The only source for any number you say."""
            try:
                facts = await state.hub_ro.farm_facts()
            except HubError as exc:
                raise ToolError(f"facts unavailable: {exc}") from exc
            state.board.append("speaker", "tool", {"tool": "farm_facts"})
            return facts

        @function_tool()
        async def check_availability(self, context: RunContext, date: str) -> dict[str, Any]:
            """Seats left on a date (YYYY-MM-DD). This is information only; it does not reserve anything."""
            try:
                av = await state.hub_ro.availability(date)
            except HubError as exc:
                raise ToolError(str(exc)) from exc
            state.board.append("speaker", "tool", {"tool": "check_availability", **av.as_dict()})
            return av.as_dict()

        @function_tool()
        async def file_booking_request(self, context: RunContext, date: str, party_size: int, visitor_name: str, note: str = "") -> dict[str, Any]:
            """File a visit REQUEST for Noor to approve. Use only after reading the date, party size and name back to the caller. Returns a reference letter. This does not confirm anything."""
            try:
                filed = await state.hub_actions.file_booking_request(
                    BookingRequest(date=date, party_size=int(party_size), visitor_name=visitor_name, language=state.language_hint or "sw", note=note), state.call_id
                )
            except HubError as exc:
                raise ToolError(f"could not file the request: {exc}") from exc
            state.board.append("speaker", "tool", {"tool": "file_booking_request", "ref": filed.ref, "status": filed.status, "party_size": int(party_size), "date": date})
            # "Getting that done for you right now": the live view prepares the change with the banner while the caller is still on the line. No save.
            try:
                await state.preparer.show(filed.ref, {"date": date, "party_size": int(party_size)})
            except Exception as exc:  # noqa: BLE001 - the screen is not the record; a display failure never fails the call
                state.board.append("preparer", "error", {"message": f"display: {type(exc).__name__}"})
            return {"ref": filed.ref, "status": filed.status, "say": f"Ombi {filed.ref} limepokelewa; Noor atathibitisha. / Request {filed.ref} received; Noor will confirm."}

    return SautiSpeaker


def _turn_detector():  # noqa: ANN202
    """The local ONNX turn detector (livekit-plugins-turn-detector). It is marked deprecated in 1.8 in favour of
    livekit.agents.inference, which is a hosted service: not acceptable here (all AI stays on the hub PC). If the plugin
    is gone, fall back to VAD-only endpointing."""
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from livekit.plugins.turn_detector.multilingual import MultilingualModel
        return MultilingualModel()
    except Exception:  # noqa: BLE001
        log.warning("local turn detector unavailable; using VAD endpointing only")
        return None


async def entrypoint(ctx) -> None:  # noqa: ANN001 - livekit JobContext
    from livekit.agents import AgentSession, room_io
    from livekit.plugins import openai, silero

    settings = load_settings()
    call_id = f"call-{uuid.uuid4().hex[:12]}"
    state = CallState(settings, call_id)
    state.board.append("system", "note", {"event": "call_start", "room": redact_text(getattr(ctx.room, "name", "") or ""), "simulated_models": settings.simulated_models, "simulated_hub": settings.simulated_hub})

    await ctx.connect()
    participant = await ctx.wait_for_participant()
    # Caller ID is never proof of identity; it is not even recorded (redaction would blank it anyway).
    state.board.append("system", "note", {"event": "participant_joined", "kind": str(getattr(participant, "kind", "")), "has_sip_attributes": bool(getattr(participant, "attributes", {}).get("sip.callID"))})

    if settings.simulated_models:
        log.warning("model servers not configured (SAUTI_STT_BASE_URL / SAUTI_LLM_BASE_URL / SAUTI_TTS_BASE_URL): the worker cannot speak; use `simulate` for an offline run")
        return

    stt = openai.STT(base_url=settings.stt_base_url, api_key="local", model=settings.stt_model, language="sw")
    llm = openai.LLM(base_url=settings.llm_base_url, api_key="local", model=settings.llm_model, temperature=0.2)
    tts = openai.TTS(base_url=settings.tts_base_url, api_key="local", model="tts-1", voice=settings.tts_voice, response_format="wav")
    turn_handling: dict[str, Any] = {"interruption": {"enabled": True, "min_words": 0}}
    detector = _turn_detector()
    if detector is not None:
        turn_handling["turn_detection"] = detector
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=silero.VAD.load(),
        turn_handling=turn_handling,
        max_tool_steps=3,
        user_away_timeout=20.0,
    )

    def on_transcribed(ev) -> None:  # noqa: ANN001
        if getattr(ev, "is_final", False) and getattr(ev, "transcript", ""):
            asyncio.create_task(state.on_caller_turn(ev.transcript, True))

    def on_item(ev) -> None:  # noqa: ANN001
        item = getattr(ev, "item", None)
        if item is not None and getattr(item, "role", "") == "assistant":
            state.board.append("speaker", "turn", {"text": str(getattr(item, "text_content", "") or "")})

    session.on("user_input_transcribed", on_transcribed)
    session.on("conversation_item_added", on_item)

    Speaker = build_agent_classes(state)
    await session.start(agent=Speaker(), room=ctx.room, room_options=room_io.RoomOptions())
    await session.say(f"{DISCLOSURE_SW} {DISCLOSURE_EN}", allow_interruptions=True)
    state.board.append("speaker", "turn", {"text": "[disclosure]"})


def main() -> None:
    from livekit.agents import WorkerOptions, cli

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    settings = load_settings()
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name=settings.agent_name))


if __name__ == "__main__":
    main()
