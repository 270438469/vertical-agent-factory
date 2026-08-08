"""Handlers that connect semantic capabilities to a selected model provider."""

import json


SYSTEM_INSTRUCTIONS = """You synthesize an answer only from the supplied evidence.
Do not invent facts. If evidence conflicts, state the uncertainty. Return concise plain text.
"""


def make_research_synthesis_handler(gateway, provider, model, usage_sink=None):
    def synthesize(payload, package):
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
                    "uncertainties": [
                        "The configured knowledge base may not cover the query."
                    ],
                    "metadata": {},
                }
            }
        prompt = "Question:\n{}\n\nEvidence:\n{}".format(
            payload.get("query", ""),
            json.dumps(evidence[:5], ensure_ascii=False, sort_keys=True),
        )
        generated = gateway.generate(
            provider,
            model,
            prompt,
            instructions=SYSTEM_INSTRUCTIONS,
        )
        if usage_sink is not None:
            usage_sink(generated)
        return {
            "result": {
                "status": "SUCCESS",
                "summary": generated.text,
                "facts": [item.get("content", "") for item in evidence[:3]],
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
                "metadata": {
                    "evidence_count": len(evidence),
                    "model_provider": generated.provider,
                    "model": generated.model,
                    "vendor_request_id": generated.vendor_request_id,
                },
            }
        }

    return synthesize
