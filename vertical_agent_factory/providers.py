import re

from .errors import RuntimeExecutionError
from .finance_data import DISCLAIMER, FinanceDataGateway, build_finance_result


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


def finance_macro_load(payload, package):
    return {"market_data": FinanceDataGateway(mode=payload.get("_data_mode")).macro(payload)}


def finance_a_share_load(payload, package):
    return {"market_data": FinanceDataGateway(mode=payload.get("_data_mode")).a_share(payload)}


def finance_us_stock_load(payload, package):
    return {"market_data": FinanceDataGateway(mode=payload.get("_data_mode")).us_stock(payload)}


def finance_analysis_compose(payload, package):
    return {"result": build_finance_result(payload.get("market_data") or {})}


def finance_result_validate(payload, package):
    result = payload.get("result") or {}
    if result.get("status") == "SUCCESS":
        if not result.get("evidence"):
            raise RuntimeExecutionError("Successful finance result has no evidence")
        if not result.get("metadata", {}).get("as_of"):
            raise RuntimeExecutionError("Successful finance result has no as_of timestamp")
    if DISCLAIMER not in result.get("warnings", []):
        raise RuntimeExecutionError("Finance result is missing the investment disclaimer")
    result.setdefault("metadata", {})["validated"] = True
    return {"result": result}


def finance_briefing_publish(payload, package):
    return {
        "result": {
            "status": "SUCCESS",
            "summary": "Financial briefing publication was approved and simulated.",
            "facts": [],
            "inferences": [],
            "evidence": [],
            "actions": [{"type": "publish", "channel": payload.get("channel", "wechat")}],
            "warnings": [DISCLAIMER, "Demo provider: no WeChat broadcast was sent."],
            "uncertainties": [],
            "metadata": {"simulated": True, "validated": True},
        }
    }


DEFAULT_HANDLERS = {
    "research_evidence_search": search_evidence,
    "research_answer_synthesize": synthesize_answer,
    "core_evidence_validate": validate_evidence,
    "research_report_publish": publish_report,
    "finance_macro_load": finance_macro_load,
    "finance_a_share_load": finance_a_share_load,
    "finance_us_stock_load": finance_us_stock_load,
    "finance_analysis_compose": finance_analysis_compose,
    "finance_result_validate": finance_result_validate,
    "finance_briefing_publish": finance_briefing_publish,
}
