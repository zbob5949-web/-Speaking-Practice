from app.difficulty_agent import DifficultyAdjustmentAgent
from app.error_aggregation import aggregate_errors
from app.grammar_rag import GRAMMAR_KNOWLEDGE, GrammarKnowledgeRetriever
from app.grammar_rules import RULES, RuleBasedGrammarChecker
from app.grammar_service import GrammarAnalysisService
from app.scenarios import list_scenarios


def test_catalog_and_bands():
    scenarios = list_scenarios("B1")
    assert len(scenarios) >= 5
    assert all(len(item["bands"]) == 5 for item in scenarios)


def test_rule_first_and_citation():
    assert len(RULES) >= 10
    feedback = GrammarAnalysisService().analyze("I enjoy to practice English.", "B1")
    assert any(item["rule_id"] == "gerund_infinitive" for item in feedback)
    assert any(item.get("source") for item in feedback)


def test_core_rules():
    rule_ids = {item.rule_id for item in RuleBasedGrammarChecker().check("She go yesterday. I am student. What you are doing?")}
    assert {"third_person_present", "past_simple", "question_word_order", "article_a_an"} <= rule_ids


def test_rag_source():
    docs = GrammarKnowledgeRetriever().invoke("subject verb agreement", level="A1", rule_ids=["subject_verb_agreement"])
    assert docs and docs[0].metadata["source_url"].startswith("https://")


def test_aggregation_and_difficulty():
    feedback = [{"feedback_type": "grammar", "error_type": "tense", "original_fragment": "go yesterday", "better_expression": "went yesterday"}] * 2
    feedback.append({"feedback_type": "grammar", "error_type": "article", "original_fragment": "am student", "better_expression": "am a student"})
    report = aggregate_errors(feedback)
    assert report["total_errors"] == 3 and report["unique_errors"] == 2 and report["errors"][0]["frequency"] == 2
    agent = DifficultyAdjustmentAgent()
    assert agent.decide("A2", [{"has_errors": False}] * 4)["next_level"] == "B1"
    assert agent.decide("B1", [{"has_errors": True}] * 3 + [{"has_errors": False}])["next_level"] == "A2"


def test_extended_rules_hit_chinese_learner_errors():
    checker = RuleBasedGrammarChecker()
    cases = {
        "because_so_conjunction": "Because I was tired, so I went to bed.",
        "although_but_conjunction": "Although it rained, but we still went out.",
        "pronoun_gender_confusion": "My sister, he is a teacher.",
        "countable_plural_missing": "I have two book and many friend.",
        "want_to_infinitive": "I want go home now.",
        "very_adverb_position": "I very like this movie.",
        "there_is_are_agreement": "There is many people in the park.",
        "time_preposition": "I go to school in Monday.",
        "if_will_conditional": "If it will rain, we will stay home.",
        "so_such_confusion": "It is so a beautiful place.",
        "few_little_quantifier": "I have a little friends.",
        "present_continuous_missing_be": "I going to the store now.",
    }
    for rule_id, sentence in cases.items():
        hits = {item.rule_id for item in checker.check(sentence)}
        assert rule_id in hits, f"{rule_id} 未命中: {sentence}"


def test_extended_rules_keep_clean_sentences_quiet():
    checker = RuleBasedGrammarChecker()
    clean = [
        "I want to go home now.",
        "There are many people in the park.",
        "I have a few friends.",
        "I really like this movie.",
        "If it rains, we will stay home.",
        "She is cooking dinner right now.",
        "I am going to the store now.",
        "It is such a beautiful place.",
    ]
    for sentence in clean:
        hits = {item.rule_id for item in checker.check(sentence)}
        assert not hits, f"干净句子被误报: {sentence} -> {hits}"


def test_extended_knowledge_base_and_sources():
    assert len(GRAMMAR_KNOWLEDGE) >= 24
    assert len(RULES) >= 24
    feedback = GrammarAnalysisService().analyze("I want go home and there is many people.", "A2")
    rule_ids = {item["rule_id"] for item in feedback}
    assert "want_to_infinitive" in rule_ids
    assert "there_is_are_agreement" in rule_ids
    assert all(item.get("source") for item in feedback if item.get("rule_id"))
