# Data grounding: the brief's datasets in our demo

Lane: Cosme (buyer/economics/distribution). Draft by cosme-claude, **not yet signed off by Cosme**.
Judging weight: "Data grounding" 15%. The brief scores "what your data does not cover" (section 7.2).
Reproduce the numbers with `.venv/bin/python scripts/business/fetch_evidence.py`. It writes `data/evidence/kenya_evidence.json` with the retrieval date; contact tags are stripped.

## 1. Demo-ready facts (MEASURED = fetched by our script on 2026-10-03)

| # | Fact for the video | Value | Source (brief link) | Status |
|---|---|---|---|---|
| F1 | Tourist-facing places OSM shows within 15 km of Othaya (Nyeri coffee belt) | 24: 17 hotels, 2 guest houses, 2 camp sites, 1 motel, 1 apartment, 1 museum | OpenStreetMap via Overpass (annex C), OSM base 2026-10-03T22:01Z | MEASURED |
| F2 | Farm tours or coffee places among them | **0** | same | MEASURED |
| F3 | Tourism receipts, Kenya | US$1.76 bn = **15.4% of exports** (2019, last WDI year) | WDI tourism series (annex C) | MEASURED |
| F4 | International arrivals, Kenya | 2.05 M (2019, WDI); 2.65 M (2025, Tourism Research Institute, via press) | WDI + TRI | MEASURED / VERIFIED (secondary) |
| F5 | Adults online, Kenya | **35.0%** use the internet (2024) | WDI IT.NET.USER.ZS (section 7.3 D) | MEASURED |
| F6 | Women vs men with an account (incl. mobile money) | 86.5% vs 93.9% (2024) | Global Findex via WDI (section 7.3 B) | MEASURED |
| F7 | Women's employment in agriculture | 53.4% of employed women (2025, ILO modeled) | WDI SL.AGR.EMPL.FE.ZS | MEASURED (modeled series) |
| F8 | Handset cost as share of monthly income, LMICs | women 24%, men 12% | GSMA Mobile Gender Gap Report 2025 (section 7.3 B) | VERIFIED (secondary summary) |

**What these mean for the story:** Noor is invisible online (F1, F2). Tourism money matters to Kenya (F3, F4), but two thirds of people are offline (F5). She is reachable through mobile money (F6) and the cooperative, not through an app store. Women are the farm workforce (F7), and a new phone is a big expense (F8), so the tool runs on the household phone.

**Draft problem statement (brief section 8), PROPOSED:**
> Because of Sauti Host, Noor will answer a foreign visitor's message in their language and keep the booking direct the same day she sees it, that she would otherwise answer days late through a guide or lose; we know because her farm has no online presence at all (0 farm or coffee listings within 15 km of Othaya on OpenStreetMap, F2) and only 35% of Kenyans are online (F5).

## 2. Every dataset in the brief, and what we do with it

| Brief dataset | Use in Sauti / demo | License, size | What it does not cover | Owner lane | Status |
|---|---|---|---|---|---|
| **OpenStreetMap via Overpass** | Findability baseline F1/F2; W5 later: an OSM listing for Noor | ODbL; 24 features (20 KB) | OSM completeness in rural Kenya is low: 0 may partly mean "unmapped", not "absent" | Cosme | MEASURED |
| **WDI tourism series** | Problem is real (F3, F4) | CC BY 4.0 | Stops at 2019 in WDI; national, nothing on rural farm tours | Cosme | MEASURED |
| **Global Findex** | Women's mobile money access (F6) | CC BY 4.0 | Account ownership ≠ smartphone use | Cosme | MEASURED |
| **GSMA Mobile Gender Gap** | Device and affordability constraint (F8) | GSMA terms, cite only | LMIC averages; Kenya-specific handset figures not extracted | Cosme | VERIFIED (secondary) |
| **World Development Indicators** | Internet use, women in agriculture (F5, F7) | CC BY 4.0 | F7 is modeled (ILO) | Cosme | MEASURED |
| **Mozilla Common Voice (Swahili)** | Whisper WER test set | CC0; v23: 1,119 h recorded, 411 h validated, 1,484 speakers; v25 20.9 GB | Read speech, not rural accented spontaneous speech; no Kikuyu | Max / Nat (eval) | VERIFIED (dataset page) |
| **FLEURS** | Published ASR benchmark for Swahili, comparing against a standard | CC BY 4.0 | Read Wikipedia sentences, studio-like | Max / Nat | VERIFIED (HF card) |
| **MASSIVE (sw-KE)** | Intent classifier (price/date/directions/booking/other) | CC BY 4.0 | Smart-assistant utterances, not tourist SMS; no tourism intents as such | Domain / Max | VERIFIED (HF card) |
| **FLORES-200 / NLLB-200** | Translation quality test; NLLB model | FLORES+: CC BY-SA 4.0 (gated); NLLB model: CC-BY-NC | **NLLB is non-commercial: conflicts with the addendum's MIT/Apache rule** | Experience / Max | VERIFIED; blocked for product use |
| **MMS (Meta)** | Swahili TTS used in W1 prototype | CC-BY-NC | **Same license conflict**; needs an MIT/Apache replacement | Experience / Max | VERIFIED; blocked for product use |
| **Wikivoyage** | Generate realistic visitor questions (synthetic, labelled) | CC BY-SA | Destination guides, not farm-tour Q&A | Nat (fixtures) | PROPOSED |
| **Yelp Open Dataset** | Review-analysis fixtures for W3 | Yelp dataset terms: personal, educational, academic use | Mostly urban US businesses; **not for a commercial product**; no coffee farm tours | Nat (fixtures) | PROPOSED, license check needed |
| **UN Tourism statistics** | Second source for arrivals/receipts | UN Tourism terms | National totals only | Cosme | UNKNOWN (not fetched yet) |
| **World Bank Enterprise Surveys** | Constraints of small firms (finance, skills, informality) | Free with registration | Formal firms; informal farm tours under-covered | Cosme | UNKNOWN (registration needed) |
| **OpenCelliD** | Show where signal really is around Othaya | CC BY-SA 4.0; needs API key | Crowdsourced tower positions, not coverage quality | Cosme | UNKNOWN (no key) |
| **WorldPop / VIIRS / HDX / Data360 / Microdata** | Not needed for this demo | n/a | n/a | n/a | Not used, on purpose |
| **Masakhane** | Pointer for Kikuyu (less-supported language question) | various | Kikuyu ASR/TTS coverage is thin | Experience | PROPOSED |
| AI4Bharat, health and agriculture annexes | Out of scope (tourism track) | n/a | n/a | n/a | Not used |

## 3. Answer to "how would it fare in a less-supported language?" (brief section 6)

Kikuyu, the language Noor speaks at home in our Kenyan setting:
- Whisper has no Kikuyu.
- NLLB lists Kikuyu (`kik_Latn`), but has the same non-commercial license.
- Common Voice Kikuyu data is small.

Our honest answer: Swahili first. In Kikuyu, the keypad fallback (1 yes, 2 no, 3 repeat) and reading the facts back in Swahili keep Noor in control. Collecting Kikuyu voice data through Common Voice is the path forward, and that data goes back to the community (the brief encourages this).

## 4. Next steps in this lane

1. Cosme signs off on the facts and the problem statement.
2. Fetch UN Tourism and Enterprise Surveys (registration needed).
3. Hand F1–F8 to Experience for the demo script and to Carter for the video.
