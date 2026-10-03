"""Fetch the problem-is-real evidence for Kenya and save a dated, cited summary.

    .venv/bin/python scripts/business/fetch_evidence.py

Sources (from the challenge brief, section 7.3 and annex C):
- World Bank WDI via the Data360 API (tourism series, Global Findex account ownership,
  internet users, female employment in agriculture). License: CC BY 4.0.
- OpenStreetMap via Overpass: the findability baseline around a coffee area. License: ODbL.
Phone numbers and other contact tags are dropped before saving.
"""

from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import certifi

OUT = Path(__file__).resolve().parents[2] / "data" / "evidence" / "kenya_evidence.json"
USER_AGENT = "SautiHost-hackathon/0.1 (Hack-Nation x World Bank, Challenge 04)"
TIMEOUT_S = 60
# python.org builds on macOS ship without a CA bundle; use certifi's.
_SSL = ssl.create_default_context(cafile=certifi.where())

WDI_INDICATORS = {
    "ST_INT_ARVL": "International tourism, number of arrivals",
    "ST_INT_RCPT_CD": "International tourism, receipts (current US$)",
    "ST_INT_RCPT_XP_ZS": "International tourism, receipts (% of total exports)",
    "FX_OWN_TOTL_FE_ZS": "Account ownership, female (% age 15+) [Global Findex]",
    "FX_OWN_TOTL_MA_ZS": "Account ownership, male (% age 15+) [Global Findex]",
    "IT_NET_USER_ZS": "Individuals using the Internet (% of population)",
    "SL_AGR_EMPL_FE_ZS": "Employment in agriculture, female (% of female employment, modeled ILO)",
}

# Othaya, Nyeri county: central Kenya coffee belt. 15 km radius.
OSM_CENTER = (-0.5470, 36.9430)
OSM_RADIUS_M = 15_000
_CONTACT_TAGS = {"phone", "contact:phone", "mobile", "contact:mobile", "email", "contact:email", "fax"}


def _get(url: str, data: bytes | None = None, attempts: int = 3) -> bytes:
    """GET (or POST when data is given) with a timeout and backoff on 429/5xx/network errors."""
    request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S, context=_SSL) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500 or attempt == attempts - 1:
                raise
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
        time.sleep(5 * 3**attempt)
    raise RuntimeError("unreachable")


def fetch_wdi(code: str) -> list[dict[str, str]]:
    query = urllib.parse.urlencode({"DATABASE_ID": "WB_WDI", "INDICATOR": f"WB_WDI_{code}", "REF_AREA": "KEN"})
    payload = json.loads(_get(f"https://data360api.worldbank.org/data360/data?{query}"))
    rows = [{"year": r["TIME_PERIOD"], "value": r["OBS_VALUE"]} for r in payload.get("value", []) if r.get("OBS_VALUE")]
    return sorted(rows, key=lambda r: r["year"])


def fetch_osm() -> dict[str, object]:
    lat, lon = OSM_CENTER
    around = f"around:{OSM_RADIUS_M},{lat},{lon}"
    query = (
        f'[out:json][timeout:60];(nwr({around})["tourism"];nwr({around})["crop"="coffee"];'
        f'nwr({around})["produce"="coffee"];);out tags center;'
    )
    payload = json.loads(_get("https://overpass-api.de/api/interpreter", urllib.parse.urlencode({"data": query}).encode()))
    features = []
    for element in payload["elements"]:
        tags = {k: v for k, v in element.get("tags", {}).items() if k not in _CONTACT_TAGS}
        features.append({"osm_type": element["type"], "osm_id": element["id"], "tags": tags})
    by_kind: dict[str, int] = {}
    for feature in features:
        kind = feature["tags"].get("tourism") or "coffee"
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "center": OSM_CENTER,
        "radius_m": OSM_RADIUS_M,
        "osm_base": payload.get("osm3s", {}).get("timestamp_osm_base"),
        "counts": by_kind,
        "farm_or_coffee_tours": sum(1 for f in features if f["tags"].get("tourism") in ("attraction", "farm") or "coffee" in json.dumps(f["tags"]).lower()),
        "features": features,
    }


def main() -> int:
    result: dict[str, object] = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "wdi_kenya": {}, "osm_othaya": None}
    for code, label in WDI_INDICATORS.items():
        try:
            result["wdi_kenya"][code] = {"label": label, "series": fetch_wdi(code)}  # type: ignore[index]
        except Exception as exc:  # keep going: one failing source must not hide the others
            result["wdi_kenya"][code] = {"label": label, "error": type(exc).__name__}  # type: ignore[index]
    try:
        result["osm_othaya"] = fetch_osm()
    except Exception as exc:
        result["osm_othaya"] = {"error": type(exc).__name__}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
