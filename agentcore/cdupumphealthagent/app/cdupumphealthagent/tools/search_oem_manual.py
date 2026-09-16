"""Search OEM equipment manuals for troubleshooting and maintenance guidance."""

import re
from typing import Optional

from strands import tool

from config import DATA_DIR, pump_manual, pump_model, MANUAL_MAP, MANUAL_TOP_K, MANUAL_MAX_SECTION_CHARS

TOPIC_KEYWORDS = {
    "bearing": ["bearing", "temperature", "lubrication", "grease", "SKF", "clearance", "thermal"],
    "vibration": ["vibration", "ISO 10816", "alignment", "balance", "resonance", "displacement"],
    "seal": ["seal", "mechanical seal", "leak", "flush", "barrier fluid", "pressure"],
    "troubleshooting": ["troubleshooting", "fault", "diagnosis", "symptom", "cause", "remedy"],
    "maintenance": ["maintenance", "inspection", "overhaul", "interval", "procedure", "torque"],
    "cavitation": ["cavitation", "NPSH", "suction", "vapor", "bubble", "erosion"],
}


def _load_manual(manual_file: str) -> list[dict]:
    path = DATA_DIR / "reference_docs" / manual_file
    if not path.exists():
        return []

    text = path.read_text()
    sections = []
    current_header = "Introduction"
    current_lines = []
    start_line = 1

    for i, line in enumerate(text.splitlines(), start=1):
        if line.startswith("#"):
            if current_lines:
                sections.append({
                    "header": current_header,
                    "text": "\n".join(current_lines).strip(),
                    "line_start": start_line,
                    "line_end": i - 1,
                })
            current_header = line.lstrip("#").strip()
            current_lines = [line]
            start_line = i
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "header": current_header,
            "text": "\n".join(current_lines).strip(),
            "line_start": start_line,
            "line_end": start_line + len(current_lines) - 1,
        })

    return sections


def _score_section(section: dict, terms: list[str]) -> float:
    header_lower = section["header"].lower()
    text_lower = section["text"].lower()
    score = 0.0

    for term in terms:
        t = term.lower()
        if t in header_lower:
            score += 10.0
        count = text_lower.count(t)
        score += min(count, 5)

    return score


@tool
def search_oem_manual(
    pump_id: Optional[str] = None,
    pump_model_name: Optional[str] = None,
    topic: Optional[str] = None,
    query: Optional[str] = None,
) -> dict:
    """Search OEM equipment manuals (Flowserve PVXM-3, Sulzer CPT-50, KSB Etanorm).

    Returns relevant sections with line numbers for citation.

    Parameters:
        pump_id: Pump ID — determines which manual to search
        pump_model_name: Alternative — specify model name directly
        topic: Topic keyword: bearing, vibration, seal, troubleshooting, maintenance, cavitation
        query: Free-text search query
    """
    if pump_id:
        manual_file = pump_manual(pump_id)
        model = pump_model(pump_id)
    elif pump_model_name:
        manual_file = None
        for m, f in MANUAL_MAP.items():
            if pump_model_name.lower() in m.lower() or m.lower() in pump_model_name.lower():
                manual_file = f
                model = m
                break
        if not manual_file:
            return {"status": "not_found", "message": f"No manual found for model '{pump_model_name}'"}
    else:
        return {"status": "error", "message": "Provide pump_id or pump_model_name"}

    sections = _load_manual(manual_file)
    if not sections:
        return {"status": "no_manual", "message": f"Manual {manual_file} not found or empty"}

    search_terms = []
    if topic and topic.lower() in TOPIC_KEYWORDS:
        search_terms.extend(TOPIC_KEYWORDS[topic.lower()])
    if query:
        search_terms.extend(query.split())
    if not search_terms:
        search_terms = ["maintenance", "troubleshooting"]

    scored = [(s, _score_section(s, search_terms)) for s in sections]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:MANUAL_TOP_K]

    results = []
    for section, score in top:
        if score <= 0:
            continue
        text = section["text"][:MANUAL_MAX_SECTION_CHARS]
        if len(section["text"]) > MANUAL_MAX_SECTION_CHARS:
            text += f"\n... (truncated, {len(section['text'])} chars total)"
        results.append({
            "header": section["header"],
            "relevance_score": round(score, 1),
            "text": text,
            "source": {
                "file": f"reference_docs/{manual_file}",
                "lines": f"{section['line_start']}-{section['line_end']}",
            },
        })

    return {
        "status": "ok",
        "pump_model": model,
        "manual_file": manual_file,
        "search_terms": search_terms,
        "results": results,
        "source": {"file": f"reference_docs/{manual_file}"},
    }
