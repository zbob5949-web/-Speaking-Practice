"""Session and round error aggregation with stable deduplication and ranking."""

from collections import defaultdict
import re
from typing import Any


def _key(item: dict[str, object]) -> tuple[str, str]:
    error_type = str(item.get("error_type") or item.get("rule_id") or "general").strip().lower()
    better = re.sub(r"\s+", " ", str(item.get("better_expression") or "").strip().lower())
    return error_type, better


def aggregate_errors(feedback: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for item in feedback:
        if item.get("feedback_type") not in {None, "grammar", "usage", "correction", "general"}:
            continue
        if not item.get("original_fragment") and not item.get("better_expression") and not item.get("feedback_text"):
            continue
        key = _key(item)
        current = grouped.get(key)
        if current is None:
            current = dict(item)
            current["frequency"] = 0
            current["examples"] = []
            grouped[key] = current
        current["frequency"] = int(current["frequency"]) + 1
        fragment = str(item.get("original_fragment") or item.get("feedback_text") or "").strip()
        if fragment and fragment not in current["examples"] and len(current["examples"]) < 3:
            current["examples"].append(fragment)
        if not current.get("source") and item.get("source"):
            current["source"] = item["source"]
            current["source_url"] = item.get("source_url")

    severity_weight = {"high": 0, "medium": 1, "low": 2}
    errors = sorted(grouped.values(), key=lambda item: (-int(item["frequency"]), severity_weight.get(str(item.get("severity")), 3), str(item.get("error_type", ""))))
    by_type: dict[str, int] = defaultdict(int)
    for item in feedback:
        error_type = str(item.get("error_type") or item.get("rule_id") or "general")
        by_type[error_type] += 1
    return {
        "total_errors": len(feedback),
        "unique_errors": len(errors),
        "errors": errors,
        "by_error_type": dict(sorted(by_type.items(), key=lambda pair: (-pair[1], pair[0]))),
        "has_errors": bool(errors),
    }
