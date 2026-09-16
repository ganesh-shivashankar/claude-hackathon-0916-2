#!/usr/bin/env python3
"""Search OEM pump manuals (markdown) by pump_id/model and topic/query.

Usage:
    python tools/search_oem_manual.py '{"pump_id":"P-07","topic":"bearing"}'
    python tools/search_oem_manual.py '{"pump_model":"Flowserve PVXM-3","topic":"vibration"}'
    python tools/search_oem_manual.py '{"query":"cavitation troubleshooting","pump_id":"P-03"}'
"""

import json
import os
import re
import sys

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))
REFERENCE_DIR = os.path.join(DATA_DIR, "reference_docs")

# Pump ID to manual file mapping
PUMP_TO_MANUAL = {
    "P-01": "flowserve_pvxm3_manual.md",
    "P-02": "flowserve_pvxm3_manual.md",
    "P-07": "flowserve_pvxm3_manual.md",
    "P-10": "flowserve_pvxm3_manual.md",
    "P-05": "ksb_etanorm_manual.md",
    "P-06": "ksb_etanorm_manual.md",
    "P-09": "ksb_etanorm_manual.md",
    "P-12": "ksb_etanorm_manual.md",
    "P-03": "sulzer_cpt50_manual.md",
    "P-04": "sulzer_cpt50_manual.md",
    "P-08": "sulzer_cpt50_manual.md",
    "P-11": "sulzer_cpt50_manual.md",
}

# Model name to manual file mapping
MODEL_TO_MANUAL = {
    "Flowserve PVXM-3": "flowserve_pvxm3_manual.md",
    "flowserve pvxm-3": "flowserve_pvxm3_manual.md",
    "pvxm-3": "flowserve_pvxm3_manual.md",
    "flowserve": "flowserve_pvxm3_manual.md",
    "KSB Etanorm 100-080": "ksb_etanorm_manual.md",
    "ksb etanorm 100-080": "ksb_etanorm_manual.md",
    "ksb etanorm": "ksb_etanorm_manual.md",
    "etanorm": "ksb_etanorm_manual.md",
    "ksb": "ksb_etanorm_manual.md",
    "Sulzer CPT-50": "sulzer_cpt50_manual.md",
    "sulzer cpt-50": "sulzer_cpt50_manual.md",
    "cpt-50": "sulzer_cpt50_manual.md",
    "sulzer": "sulzer_cpt50_manual.md",
}

# Pump ID to model name for display
PUMP_MODEL_MAP = {
    "P-01": "Flowserve PVXM-3", "P-02": "Flowserve PVXM-3",
    "P-07": "Flowserve PVXM-3", "P-10": "Flowserve PVXM-3",
    "P-05": "KSB Etanorm 100-080", "P-06": "KSB Etanorm 100-080",
    "P-09": "KSB Etanorm 100-080", "P-12": "KSB Etanorm 100-080",
    "P-03": "Sulzer CPT-50", "P-04": "Sulzer CPT-50",
    "P-08": "Sulzer CPT-50", "P-11": "Sulzer CPT-50",
}


def resolve_manual(pump_id=None, pump_model=None):
    """Determine which manual file to search."""
    if pump_id and pump_id in PUMP_TO_MANUAL:
        return PUMP_TO_MANUAL[pump_id]
    if pump_model:
        # Try exact match first, then case-insensitive
        if pump_model in MODEL_TO_MANUAL:
            return MODEL_TO_MANUAL[pump_model]
        lower = pump_model.lower().strip()
        if lower in MODEL_TO_MANUAL:
            return MODEL_TO_MANUAL[lower]
        # Partial match
        for key, val in MODEL_TO_MANUAL.items():
            if key.lower() in lower or lower in key.lower():
                return val
    return None


def parse_sections(lines):
    """Parse markdown into sections based on ## and ### headers.

    Returns a list of dicts: {header, header_level, line_start, line_end, text}
    Line numbers are 1-indexed to match file display.
    """
    sections = []
    current = None

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        # Check for markdown headers (## or ###)
        header_match = re.match(r'^(#{1,4})\s+(.+)', stripped)
        if header_match:
            # Close previous section
            if current is not None:
                current["line_end"] = i  # exclusive; last content line is i-1
                current["text"] = "\n".join(lines[current["_start_idx"]:i]).strip()
                sections.append(current)

            level = len(header_match.group(1))
            current = {
                "header": header_match.group(2).strip(),
                "header_level": level,
                "line_start": i + 1,  # 1-indexed
                "_start_idx": i,
            }

    # Close last section
    if current is not None:
        current["line_end"] = len(lines)
        current["text"] = "\n".join(lines[current["_start_idx"]:]).strip()
        sections.append(current)

    # Clean up internal keys
    for s in sections:
        del s["_start_idx"]

    return sections


def score_section(section, search_terms):
    """Score a section against search terms. Returns (score, matched_terms)."""
    header_lower = section["header"].lower()
    text_lower = section["text"].lower()
    score = 0
    matched = []

    for term in search_terms:
        term_lower = term.lower()
        # Header match is worth more
        if term_lower in header_lower:
            score += 10
            matched.append(f"header match: '{term}'")
        # Body match
        count = text_lower.count(term_lower)
        if count > 0:
            score += min(count, 5)  # Cap contribution per term
            if f"header match: '{term}'" not in matched:
                matched.append(f"content match: '{term}' ({count} occurrences)")

    return score, matched


def extract_search_terms(topic=None, query=None):
    """Build a list of search terms from topic and/or query."""
    terms = []
    if topic:
        terms.append(topic)
        # Add common related terms
        topic_expansions = {
            "bearing": ["bearing", "lubrication", "grease", "SKF", "NSK", "FAG", "L10", "temperature"],
            "vibration": ["vibration", "ISO 10816", "alignment", "balance", "resonance"],
            "seal": ["seal", "leak", "barrier fluid", "API Plan", "mechanical seal"],
            "cavitation": ["cavitation", "NPSH", "suction", "pressure"],
            "impeller": ["impeller", "wear ring", "clearance", "erosion", "vane"],
            "alignment": ["alignment", "coupling", "misalignment", "TIR", "baseplate"],
            "troubleshooting": ["troubleshooting", "fault", "diagnosis", "symptom", "cause"],
            "maintenance": ["maintenance", "inspection", "replacement", "procedure", "interval"],
        }
        for key, expansions in topic_expansions.items():
            if key in topic.lower():
                terms.extend([t for t in expansions if t.lower() != topic.lower()])
                break

    if query:
        # Split query into words, keep multi-word phrases too
        terms.append(query)
        words = [w for w in query.lower().split() if len(w) > 2]
        terms.extend(words)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in terms:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            unique.append(t)

    return unique


def search(pump_id=None, pump_model=None, topic=None, query=None):
    """Main search function."""
    manual_file = resolve_manual(pump_id, pump_model)
    if not manual_file:
        return {
            "status": "error",
            "message": f"Cannot determine which manual to search. Provide a valid pump_id (P-01 through P-12) or pump_model.",
            "valid_pump_ids": list(PUMP_TO_MANUAL.keys()),
            "valid_models": ["Flowserve PVXM-3", "KSB Etanorm 100-080", "Sulzer CPT-50"],
        }

    manual_path = os.path.join(REFERENCE_DIR, manual_file)
    if not os.path.exists(manual_path):
        return {
            "status": "error",
            "message": f"Manual file not found: {manual_file}",
            "path_checked": manual_path,
        }

    with open(manual_path, "r") as f:
        content = f.read()
    lines = content.split("\n")

    # Parse into sections
    sections = parse_sections(lines)

    # Build search terms
    search_terms = extract_search_terms(topic, query)
    if not search_terms:
        # No search terms: return table of contents
        toc = [{"section": s["header"], "line_start": s["line_start"], "line_end": s["line_end"]} for s in sections if s["header_level"] <= 2]
        return {
            "status": "ok",
            "pump_id": pump_id,
            "pump_model": pump_model or PUMP_MODEL_MAP.get(pump_id, "unknown"),
            "manual_file": manual_file,
            "message": "No topic/query provided. Returning table of contents.",
            "table_of_contents": toc,
            "source": {
                "file": f"reference_docs/{manual_file}",
                "total_lines": len(lines),
            }
        }

    # Score each section
    scored = []
    for s in sections:
        score, matched = score_section(s, search_terms)
        if score > 0:
            scored.append((score, matched, s))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return {
            "status": "no_matches",
            "pump_id": pump_id,
            "pump_model": pump_model or PUMP_MODEL_MAP.get(pump_id, "unknown"),
            "manual_file": manual_file,
            "search_terms": search_terms,
            "message": f"No sections matched the search terms in {manual_file}",
            "source": {
                "file": f"reference_docs/{manual_file}",
                "total_lines": len(lines),
            }
        }

    # Return top matching sections (limit to top 5 to keep output manageable)
    results = []
    for score, matched, s in scored[:5]:
        section_text = s["text"]
        # Truncate very long sections to keep output reasonable
        if len(section_text) > 2000:
            section_text = section_text[:2000] + "\n... [truncated — see full manual for complete section]"

        results.append({
            "section_header": s["header"],
            "relevance_score": score,
            "matched_terms": matched,
            "line_start": s["line_start"],
            "line_end": s["line_end"],
            "content": section_text,
        })

    return {
        "status": "ok",
        "pump_id": pump_id,
        "pump_model": pump_model or PUMP_MODEL_MAP.get(pump_id, "unknown"),
        "manual_file": manual_file,
        "search_terms": search_terms,
        "matches_found": len(scored),
        "top_results": results,
        "source": {
            "file": f"reference_docs/{manual_file}",
            "line_ranges": [[r["line_start"], r["line_end"]] for r in results],
            "total_lines": len(lines),
        }
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: search_oem_manual.py '{\"pump_id\":\"P-07\",\"topic\":\"bearing\"}'",
            "examples": [
                '{"pump_id": "P-07", "topic": "bearing"}',
                '{"pump_model": "Flowserve PVXM-3", "topic": "vibration"}',
                '{"query": "cavitation troubleshooting", "pump_id": "P-03"}',
            ]
        }))
        sys.exit(1)

    params = json.loads(sys.argv[1])
    result = search(**params)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
