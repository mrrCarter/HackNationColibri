"""The hub (apps/hub) as seen from the voice agent.

Two deliberately separate objects:

- HubReadOnly: availability and approved farm facts. Sidecars get this one.
- HubActions: files a booking REQUEST (a proposal that reaches Noor as a read-back
  SMS through the hub and @sauti/core). Only the speaker's tool holds this one.

Neither confirms a booking: confirmation is Noor's exact approval, by Sauti PIN in
the app or by "NDIYO <ref> <code>" from her enrolled phone. With no hub URL
configured both answer from local fixtures and write to a local JSONL outbox under
runtime/ (gitignored), so the whole flow runs offline for the demo.

Endpoints expected from apps/hub (asked in the room, 2026-10-04):
  GET  /v1/availability?date=YYYY-MM-DD  -> {date, capacity, confirmed, remaining, open}
  GET  /v1/farm                          -> approved farm facts (the current farm sheet revision)
  POST /v1/proposals                     -> {ref, action_id, status: "pending_owner"}
Owner mode (Noor calls the farm number herself):
  GET  /v1/owner/match?sha256=<hex>      -> {match: true|false}   (sha256 of the normalised caller id; the number never travels)
  GET  /v1/proposals?status=pending_owner -> {pending: [{ref, date, party_size, source, filed_at}]}  (no names, no numbers)
  GET  /v1/feedback/summary              -> {period, themes: [{theme, verdict, unique_comments, summary_sw}], ask_a_person}
  POST /v1/owner-proposals               -> {ref, action_id, status: "pending_owner"}  (the hub sends the read-back SMS + code)
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .redact import redact_text

try:  # httpx is only needed against a real hub
    import httpx
except Exception:  # pragma: no cover - optional at import time
    httpx = None  # type: ignore[assignment]

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class HubError(RuntimeError):
    pass


@dataclass(frozen=True)
class Availability:
    date: str
    capacity: int
    confirmed: int
    open: bool

    @property
    def remaining(self) -> int:
        return max(0, self.capacity - self.confirmed) if self.open else 0

    def as_dict(self) -> dict[str, Any]:
        return {"date": self.date, "capacity": self.capacity, "confirmed": self.confirmed, "remaining": self.remaining, "open": self.open}


def _check_date(date: str) -> None:
    if not DATE.match(date):
        raise HubError("date must be YYYY-MM-DD")


class HubReadOnly:
    """Queries only. No method here changes anything anywhere."""

    def __init__(self, base_url: str, token: str, fixtures_dir: Path, timeout_s: float = 1.0) -> None:
        self._base = base_url.rstrip("/")
        self._token = token
        self._fixtures = fixtures_dir
        self._timeout = timeout_s

    @property
    def simulated(self) -> bool:
        return not self._base

    async def availability(self, date: str) -> Availability:
        _check_date(date)
        if self.simulated:
            cal = json.loads((self._fixtures / "availability.json").read_text(encoding="utf-8"))
            day = cal.get("days", {}).get(date)
            if day is None:
                weekday = time.strftime("%a", time.strptime(date, "%Y-%m-%d")).lower()[:3]
                open_days = {d[:3].lower() for d in cal.get("open_weekdays", [])}
                return Availability(date=date, capacity=int(cal.get("capacity_per_tour", 0)), confirmed=0, open=weekday in open_days)
            return Availability(date=date, capacity=int(day.get("capacity", cal.get("capacity_per_tour", 0))), confirmed=int(day.get("confirmed", 0)), open=bool(day.get("open", True)))
        data = await self._get("/v1/availability", {"date": date})
        return Availability(date=str(data["date"]), capacity=int(data["capacity"]), confirmed=int(data["confirmed"]), open=bool(data.get("open", True)))

    async def farm_facts(self) -> dict[str, Any]:
        """The approved farm sheet (prices, hours, days, directions, inclusions). Facts the speaker may state."""
        if self.simulated:
            return json.loads((self._fixtures / "farm.json").read_text(encoding="utf-8"))
        return await self._get("/v1/farm", {})

    async def owner_match(self, caller_sha256: str) -> bool:
        """Does this caller-id hash belong to the tenant's enrolled owner phone? Selects owner MODE only; grants nothing."""
        if not re.fullmatch(r"[0-9a-f]{64}", caller_sha256):
            return False
        try:
            if self.simulated:
                owner = json.loads((self._fixtures / "owner.json").read_text(encoding="utf-8"))
                return owner.get("enrolled_number_sha256") == caller_sha256
            data = await self._get("/v1/owner/match", {"sha256": caller_sha256})
        except Exception:  # noqa: BLE001 - any doubt (unreachable, timeout, bad JSON, bad status) is NOT the owner
            return False
        # Only a literal JSON true counts. "true", 1, "yes", a missing key or a non-object are all NOT the owner.
        return isinstance(data, dict) and data.get("match") is True

    async def pending_requests(self) -> list[dict[str, Any]]:
        """Requests waiting for Noor: refs, dates, party sizes, source. Never visitor names or numbers."""
        if self.simulated:
            data = json.loads((self._fixtures / "pending.json").read_text(encoding="utf-8"))
        else:
            data = await self._get("/v1/proposals", {"status": "pending_owner"})
        out: list[dict[str, Any]] = []
        for item in data.get("pending", []):
            out.append({k: item[k] for k in ("ref", "date", "party_size", "source", "filed_at") if k in item})
        return out

    async def feedback_summary(self) -> dict[str, Any]:
        """The feedback loop's painpoint summary (apps/hub/src/feedback): themes with counts, no quotes."""
        if self.simulated:
            return json.loads((self._fixtures / "feedback_summary.json").read_text(encoding="utf-8"))
        return await self._get("/v1/feedback/summary", {})

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        if httpx is None:
            raise HubError("httpx is not installed")
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(self._base + path, params=params, headers=headers)
        except Exception as exc:  # network errors are reported, never logged with URLs that may carry tokens
            raise HubError(f"hub unreachable: {type(exc).__name__}") from exc
        if r.status_code != 200:
            raise HubError(f"hub answered {r.status_code}")
        return r.json()


@dataclass(frozen=True)
class BookingRequest:
    date: str
    party_size: int
    visitor_name: str
    language: str
    note: str = ""


@dataclass(frozen=True)
class FiledRequest:
    ref: str
    action_id: str
    status: str  # always "pending_owner" from here: the agent never confirms


class HubActions:
    """The one write the speaker may perform: file a booking request for Noor to approve."""

    def __init__(self, base_url: str, token: str, runtime_dir: Path, tenant_id: str, timeout_s: float = 3.0) -> None:
        self._base = base_url.rstrip("/")
        self._token = token
        self._runtime = runtime_dir
        self._tenant = tenant_id
        self._timeout = timeout_s

    @property
    def simulated(self) -> bool:
        return not self._base

    async def file_booking_request(self, req: BookingRequest, call_id: str) -> FiledRequest:
        _check_date(req.date)
        if req.party_size < 1 or req.party_size > 200:
            raise HubError("party_size must be 1..200")
        body = {
            "tenant_id": self._tenant,
            "source": {"channel": "voice", "call_id": call_id},
            "booking": {"date": req.date, "party_size": req.party_size, "visitor_name": redact_text(req.visitor_name)[:80], "language": req.language},
            "note": redact_text(req.note)[:280],
        }
        if self.simulated:
            self._runtime.mkdir(parents=True, exist_ok=True)
            n = sum(1 for _ in (self._runtime / "proposals.jsonl").open(encoding="utf-8")) if (self._runtime / "proposals.jsonl").exists() else 0
            ref = chr(ord("A") + (n % 26))
            action_id = f"simulated-{n + 1:04d}"
            with (self._runtime / "proposals.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"synthetic": True, "ref": ref, "action_id": action_id, "status": "pending_owner", **body}, ensure_ascii=False) + "\n")
            return FiledRequest(ref=ref, action_id=action_id, status="pending_owner")
        if httpx is None:
            raise HubError("httpx is not installed")
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(self._base + "/v1/proposals", json=body, headers=headers)
        except Exception as exc:
            raise HubError(f"hub unreachable: {type(exc).__name__}") from exc
        if r.status_code not in (200, 201):
            raise HubError(f"hub answered {r.status_code}")
        data = r.json()
        return FiledRequest(ref=str(data["ref"]), action_id=str(data["action_id"]), status="pending_owner")

    async def file_owner_proposal(self, kind: str, text: str, about_ref: str | None, call_id: str) -> FiledRequest:
        """Noor asked for a change by voice ("nitachelewa kidogo", "funga Jumamosi"). This files a PROPOSAL; the hub reads
        it back to her enrolled phone with a one-time code. Her voice did not approve anything, and neither does this call."""
        if kind not in ("running_late", "close_day", "open_day", "capacity", "message_to_visitor", "other"):
            raise HubError("unknown change kind")
        body = {
            "tenant_id": self._tenant,
            "source": {"channel": "voice_owner", "call_id": call_id},
            "change": {"kind": kind, "text": redact_text(text)[:280], "about_ref": (about_ref or "")[:8]},
        }
        if self.simulated:
            self._runtime.mkdir(parents=True, exist_ok=True)
            path = self._runtime / "owner-proposals.jsonl"
            n = sum(1 for _ in path.open(encoding="utf-8")) if path.exists() else 0
            ref = f"N{n + 1}"
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"synthetic": True, "ref": ref, "action_id": f"simulated-owner-{n + 1:04d}", "status": "pending_owner", "read_back": "sms_with_code_to_enrolled_phone", **body}, ensure_ascii=False) + "\n")
            return FiledRequest(ref=ref, action_id=f"simulated-owner-{n + 1:04d}", status="pending_owner")
        if httpx is None:
            raise HubError("httpx is not installed")
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(self._base + "/v1/owner-proposals", json=body, headers=headers)
        except Exception as exc:
            raise HubError(f"hub unreachable: {type(exc).__name__}") from exc
        if r.status_code not in (200, 201):
            raise HubError(f"hub answered {r.status_code}")
        data = r.json()
        return FiledRequest(ref=str(data["ref"]), action_id=str(data["action_id"]), status="pending_owner")
