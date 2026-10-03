"""Shared plumbing for Noor's interfaces: offline guard, logging, safe error handling."""

from __future__ import annotations

import logging

from sauti import config
from sauti.storage import db
from sauti.workflows.setup_farm import Channel, Extractor, SetupResult, run_setup

log = logging.getLogger("sauti")

TECHNICAL_PROBLEM = "Samahani, kuna tatizo la kiufundi. Hakuna kilichohifadhiwa. Tafadhali jaribu tena."


def setup_logging() -> None:
    config.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=config.LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def load_extractor() -> Extractor | None:
    """Qwen if its file is present, otherwise None: the call then asks every field."""
    if not config.QWEN_PATH.exists():
        log.warning("Qwen model missing at %s, running without extractor", config.QWEN_PATH)
        return None
    from sauti.models.llm import QwenExtractor

    return QwenExtractor(config.QWEN_PATH)


def run_setup_call(channel: Channel, extractor: Extractor | None, source: str) -> SetupResult | None:
    conn = db.connect(config.DB_PATH)
    try:
        result = run_setup(
            channel,
            extractor,
            save=lambda sheet, transcript: db.save_farm_sheet(conn, sheet, source, transcript),
        )
        log.info("W1 finished, saved version=%s", result.saved_version)
        return result
    except Exception:
        # Full trace goes to the log file, never to Noor.
        log.exception("W1 call failed")
        channel.say(TECHNICAL_PROBLEM)
        return None
    finally:
        conn.close()
