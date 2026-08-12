"""
Report Generator for single-document plagiarism check against web sources.
"""

from datetime import datetime
from typing import Dict, List, Optional


VERDICT_MAP = [
    (0.70, "plagiarism",    "Plagiarism Detected",                      "#E24B4A", "#FCEBEB"),
    (0.50, "high_risk",     "High Similarity — Likely Plagiarised",     "#BA7517", "#FAEEDA"),
    (0.30, "moderate_risk", "Moderate Overlap — Review Recommended",    "#9A7D20", "#FFFAE5"),
    (0.10, "low_risk",      "Low Similarity — Minor Overlap Found",     "#1D9E75", "#E1F5EE"),
    (0.00, "clean",         "No Plagiarism Detected",                   "#639922", "#EAF3DE"),
]


def generate_single_doc_report(
    text: str,
    stats: Dict,
    sources: List[Dict],
    meta: Optional[Dict] = None,
) -> Dict:

    # Overall plagiarism score = max source similarity (weighted)
    if sources:
        top_score = sources[0]["similarity"] / 100
        # Weighted: top source counts most
        weights = [1 / (i + 1) for i in range(len(sources))]
        total_w = sum(weights)
        weighted = sum(s["similarity"] / 100 * w for s, w in zip(sources, weights)) / total_w
        overall = top_score * 0.6 + weighted * 0.4
    else:
        overall = 0.0

    verdict, label, color, bg = _get_verdict(overall)

    # Unique domains found
    import re
    domains = []
    seen = set()
    for s in sources:
        m = re.search(r'https?://(?:www\.)?([^/]+)', s.get("url", ""))
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            domains.append(m.group(1))

    return {
        "id":               f"rpt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "timestamp":        datetime.utcnow().isoformat() + "Z",
        "verdict":          verdict,
        "verdict_label":    label,
        "verdict_color":    color,
        "verdict_bg":       bg,
        "overall_score":    round(overall * 100, 1),
        "sources_found":    len(sources),
        "domains_found":    domains[:5],
        "document": {
            "stats": stats,
            "meta":  meta or {},
            "preview": text[:400] + ("…" if len(text) > 400 else ""),
        },
        "sources": sources,
        "recommendations": _recommendations(verdict, sources),
        "summary": {
            "checked_sentences": 6,
            "matching_sources":  len(sources),
            "highest_match":     sources[0]["similarity"] if sources else 0,
            "top_source":        sources[0]["url"] if sources else None,
        }
    }


def _get_verdict(score: float):
    for threshold, key, label, color, bg in VERDICT_MAP:
        if score >= threshold:
            return key, label, color, bg
    return "clean", "No Plagiarism Detected", "#639922", "#EAF3DE"


def _recommendations(verdict: str, sources: List) -> List[str]:
    if verdict == "plagiarism":
        return [
            "Strong plagiarism evidence found. Review all highlighted sources.",
            "Rewrite flagged sections in your own words and add proper citations.",
            f"Top match: {sources[0]['url']}" if sources else "",
        ]
    elif verdict == "high_risk":
        return [
            "Significant overlap with online sources detected.",
            "Verify all borrowed ideas are properly cited.",
        ]
    elif verdict == "moderate_risk":
        return [
            "Some overlap found — may reflect common phrasing or shared topic.",
            "Review highlighted sources and add citations where needed.",
        ]
    elif verdict == "low_risk":
        return ["Minor overlap detected. Document appears mostly original."]
    return ["No significant online plagiarism detected. Document appears original."]
