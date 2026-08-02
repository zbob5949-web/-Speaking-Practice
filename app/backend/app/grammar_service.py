"""Rule-first grammar analysis, RAG citations, and optional LLM deep review."""

import json
import re
from typing import Any

from app.grammar_rag import GrammarKnowledgeRetriever, knowledge_for_rule
from app.grammar_rules import RuleBasedGrammarChecker


def _json_array(text: str) -> list[dict[str, object]]:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed) else []


class GrammarAnalysisService:
    def __init__(self, checker: RuleBasedGrammarChecker | None = None, retriever: GrammarKnowledgeRetriever | None = None):
        self.checker = checker or RuleBasedGrammarChecker()
        self.retriever = retriever or GrammarKnowledgeRetriever()

    def analyze(self, text: str, level: str = "A2", llm: Any | None = None, context: str = "") -> list[dict[str, object]]:
        rule_feedback: list[dict[str, object]] = []
        for match in self.checker.check(text):
            item = match.to_dict()
            sources = knowledge_for_rule(match.rule_id, level)
            item["knowledge_sources"] = sources
            item["source"] = sources[0].get("source") if sources else "SpeakMate Grammar Notes"
            item["source_url"] = sources[0].get("source_url") if sources else None
            item["example_sentence"] = self._example(match.rule_id, match.better_expression)
            rule_feedback.append(item)

        deep_feedback = self._deep_analysis(text, level, llm, context, rule_feedback)
        merged = rule_feedback + deep_feedback
        return self._deduplicate(merged)

    def _deep_analysis(self, text: str, level: str, llm: Any | None, context: str, rule_feedback: list[dict[str, object]]) -> list[dict[str, object]]:
        if llm is None:
            return []
        retrieved = self.retriever.invoke(text, level=level, k=4)
        source_context = "\n".join(f"- {document.metadata.get('rule_id')}: {document.page_content} (出处: {document.metadata.get('source')})" for document in retrieved)
        system_prompt = (
            "You are the deep grammar review stage after deterministic rules. "
            "Return only a JSON array. Each item must contain feedback_type, error_type, "
            "original_fragment, better_expression, reason_zh, severity, and optionally example_sentence. "
            "Do not repeat a correction already found by the rules. Keep feedback_type as grammar or usage."
        )
        user_prompt = json.dumps({"text": text, "level": level, "context": context, "rule_feedback": rule_feedback, "retrieved_grammar": source_context}, ensure_ascii=False)
        try:
            return [self._attach_source(item, level) for item in _json_array(llm.complete(system_prompt=system_prompt, user_prompt=user_prompt))]
        except Exception:
            return []

    def _attach_source(self, item: dict[str, object], level: str) -> dict[str, object]:
        normalized = dict(item)
        normalized.setdefault("feedback_type", "grammar")
        normalized.setdefault("error_type", "LLM 深度分析")
        normalized.setdefault("severity", "low")
        normalized.setdefault("confidence", 0.65)
        rule_id = str(normalized.get("rule_id") or "")
        sources = knowledge_for_rule(rule_id, level) if rule_id else []
        if sources:
            normalized.setdefault("source", sources[0].get("source"))
            normalized.setdefault("source_url", sources[0].get("source_url"))
            normalized.setdefault("knowledge_sources", sources)
        return normalized

    @staticmethod
    def _deduplicate(items: list[dict[str, object]]) -> list[dict[str, object]]:
        unique: dict[tuple[str, str, str], dict[str, object]] = {}
        for item in items:
            original = str(item.get("original_fragment") or item.get("feedback_text") or "").strip().lower()
            better = str(item.get("better_expression") or "").strip().lower()
            error_type = str(item.get("error_type") or item.get("rule_id") or "general")
            if not original and not better:
                continue
            key = (error_type, original, better)
            if key not in unique:
                unique[key] = item
            elif float(item.get("confidence") or 0) > float(unique[key].get("confidence") or 0):
                unique[key] = item
        return list(unique.values())

    @staticmethod
    def _example(rule_id: str, corrected: str) -> str:
        examples = {
            "subject_verb_agreement": f"The receptionist {corrected.split()[-1] if corrected else 'is'} helpful.",
            "third_person_present": "She works at the airport.",
            "past_simple": "I arrived yesterday.",
            "present_perfect": "I have seen this room before.",
            "article_a_an": "She is a manager.",
            "quantifiers": "We have many options.",
            "preposition_collocation": "I am interested in this role.",
            "gerund_infinitive": "I enjoy practicing English.",
            "modal_base_form": "Could you help me?",
            "question_word_order": "Where are you staying?",
            "comparative_form": "This option is better.",
            "uncountable_nouns": "Could you give me some advice?",
            "because_so_conjunction": "Because it rained, we stayed home.",
            "although_but_conjunction": "Although it was late, we continued.",
            "pronoun_gender_confusion": "She is my sister and works in a hospital.",
            "countable_plural_missing": "I bought two books yesterday.",
            "want_to_infinitive": "I want to go home now.",
            "very_adverb_position": "I really like this movie.",
            "there_is_are_agreement": "There are many people in the park.",
            "time_preposition": "I have a meeting on Monday morning.",
            "if_will_conditional": "If it rains, we will stay home.",
            "so_such_confusion": "It is such a beautiful place.",
            "few_little_quantifier": "I have a few friends and a little money.",
            "present_continuous_missing_be": "She is cooking dinner right now.",
        }
        return examples.get(rule_id, corrected)
