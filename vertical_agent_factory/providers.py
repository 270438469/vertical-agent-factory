import re

from .errors import RuntimeExecutionError


def _words(value):
    stop_words = {
        "a",
        "about",
        "all",
        "an",
        "and",
        "any",
        "for",
        "from",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "one",
        "or",
        "the",
        "to",
        "what",
        "which",
        "with",
    }
    return {
        word
        for word in re.findall(r"[\w\u4e00-\u9fff]+", (value or "").lower())
        if word not in stop_words
    }


def search_evidence(payload, package):
    if payload.get("simulate_failure"):
        raise RuntimeExecutionError("Simulated evidence provider failure")
    query_words = _words(payload.get("query"))
    results = []
    for document in package.knowledge.get("documents", []):
        haystack = "{} {}".format(document.get("title", ""), document.get("content", ""))
        score = len(query_words.intersection(_words(haystack)))
        if score or not query_words:
            item = dict(document)
            item["score"] = score
            results.append(item)
    results.sort(key=lambda item: item.get("score", 0), reverse=True)
    return {"evidence": results[:5]}


def synthesize_answer(payload, package):
    evidence = payload.get("evidence", [])
    if not evidence:
        return {
            "result": {
                "status": "INSUFFICIENT_EVIDENCE",
                "summary": "No matching evidence was found.",
                "facts": [],
                "inferences": [],
                "evidence": [],
                "actions": [],
                "warnings": ["Answer withheld because evidence is insufficient."],
                "uncertainties": ["The configured knowledge base may not cover the query."],
                "metadata": {},
            }
        }
    facts = [item.get("content", "") for item in evidence[:3]]
    return {
        "result": {
            "status": "SUCCESS",
            "summary": facts[0],
            "facts": facts,
            "inferences": [],
            "evidence": [
                {
                    "id": item.get("id"),
                    "source": item.get("source"),
                    "title": item.get("title"),
                    "timestamp": item.get("timestamp"),
                }
                for item in evidence[:3]
            ],
            "actions": [],
            "warnings": [],
            "uncertainties": [],
            "metadata": {"evidence_count": len(evidence)},
        }
    }


def validate_evidence(payload, package):
    result = payload.get("result", {})
    evidence = result.get("evidence", [])
    if result.get("status") == "SUCCESS" and not evidence:
        raise RuntimeExecutionError("Successful result has no evidence")
    result.setdefault("metadata", {})["validated"] = True
    return {"result": result}


def publish_report(payload, package):
    return {
        "result": {
            "status": "SUCCESS",
            "summary": "Report publication was approved and simulated.",
            "facts": [],
            "inferences": [],
            "evidence": [],
            "actions": [{"type": "publish", "target": payload.get("target", "demo")}],
            "warnings": ["Demo provider: no external system was modified."],
            "uncertainties": [],
            "metadata": {"simulated": True},
        }
    }


DEFAULT_HANDLERS = {
    "research_evidence_search": search_evidence,
    "research_answer_synthesize": synthesize_answer,
    "core_evidence_validate": validate_evidence,
    "research_report_publish": publish_report,
}
