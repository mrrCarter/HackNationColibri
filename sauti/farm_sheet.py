"""The farm sheet: the single source of truth for facts about Noor's tours.

Written only by W1 after Noor confirmed each value. Read by W2 (prices,
capacity, directions) and W5 (listings). A field left as None means
"Noor has not told us": readers must answer "not sure, ask Noor".
"""

from __future__ import annotations

import hashlib
import json
from datetime import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class OpeningHours(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: time
    end: time

    @model_validator(mode="after")
    def _end_after_start(self) -> OpeningHours:
        if self.end <= self.start:
            raise ValueError("tour must end after it starts")
        return self


class FarmSheet(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Assumption: one price per visitor, in Kenyan shillings. No child rate yet.
    price_per_person_kes: int | None = Field(default=None, ge=1, le=1_000_000)
    # Assumption: maximum number of visitors in one tour (one slot).
    capacity_per_tour: int | None = Field(default=None, ge=1, le=200)
    days: list[Weekday] | None = None
    hours: OpeningHours | None = None
    directions_sw: str | None = Field(default=None, max_length=2000)
    inclusions_sw: list[str] | None = None

    def missing_fields(self) -> list[str]:
        return [name for name, value in self if value is None]

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
