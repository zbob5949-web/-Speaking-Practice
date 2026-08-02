"""Small, local grammar knowledge base exposed through a LangChain retriever shape."""

from dataclasses import dataclass
import re
from typing import Any

try:  # LangChain is optional at import time so rule-only mode remains usable offline.
    from langchain_core.documents import Document
except ImportError:  # pragma: no cover - exercised only before optional install
    @dataclass(frozen=True)
    class Document:  # type: ignore[no-redef]
        page_content: str
        metadata: dict[str, Any]


GRAMMAR_KNOWLEDGE: tuple[dict[str, object], ...] = (
    {"rule_id": "subject_verb_agreement", "levels": ("A1", "A2", "B1"), "title": "Subject-verb agreement", "content": "A singular third-person subject normally takes a singular verb in the present. He works, she has, and it is.", "source": "SpeakMate Grammar Notes: Subject-verb agreement", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/present-simple"},
    {"rule_id": "third_person_present", "levels": ("A1", "A2", "B1"), "title": "Third-person present simple", "content": "With he, she, or it, add -s or -es to most present-simple verbs. Study becomes studies and watch becomes watches.", "source": "SpeakMate Grammar Notes: Present simple", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/present-simple"},
    {"rule_id": "past_simple", "levels": ("A1", "A2", "B1"), "title": "Past simple with finished time", "content": "Use the past simple for a finished event at a finished time, such as yesterday, last week, or two days ago.", "source": "SpeakMate Grammar Notes: Past simple", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/past-simple"},
    {"rule_id": "present_perfect", "levels": ("A2", "B1", "B2"), "title": "Present perfect form", "content": "Use have or has plus a past participle. Common irregular forms include gone, eaten, seen, and done.", "source": "SpeakMate Grammar Notes: Present perfect", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/present-perfect"},
    {"rule_id": "article_a_an", "levels": ("A1", "A2", "B1"), "title": "Indefinite articles", "content": "Use a or an before a singular countable noun when it is not specific. Use an before a vowel sound, as in an engineer.", "source": "SpeakMate Grammar Notes: Articles", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/articles"},
    {"rule_id": "quantifiers", "levels": ("A2", "B1"), "title": "Many and much", "content": "Use many with plural countable nouns and much with uncountable nouns: many apples, much water.", "source": "SpeakMate Grammar Notes: Quantifiers", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/quantifiers"},
    {"rule_id": "preposition_collocation", "levels": ("A2", "B1", "B2"), "title": "Common preposition combinations", "content": "Some adjectives and verbs select a conventional preposition: interested in, good at, depend on, and arrive at/in.", "source": "SpeakMate Grammar Notes: Prepositions", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/prepositions"},
    {"rule_id": "gerund_infinitive", "levels": ("B1", "B2"), "title": "Verb patterns", "content": "Enjoy, avoid, and finish are followed by a gerund. Want, need, and hope are commonly followed by to plus the base verb.", "source": "SpeakMate Grammar Notes: Verb patterns", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/verb-patterns"},
    {"rule_id": "modal_base_form", "levels": ("A2", "B1"), "title": "Modal plus base verb", "content": "A modal such as can, should, or must is followed by the base form without to: can go, should ask, must leave.", "source": "SpeakMate Grammar Notes: Modal verbs", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/modal-verbs"},
    {"rule_id": "question_word_order", "levels": ("A1", "A2", "B1"), "title": "Question word order", "content": "In most wh-questions, put the auxiliary or be before the subject: What are you doing? Where did she go?", "source": "SpeakMate Grammar Notes: Questions", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/question-forms"},
    {"rule_id": "comparative_form", "levels": ("A2", "B1"), "title": "Comparative adjectives", "content": "Do not combine more with an adjective that already has a comparative form. Say better, easier, or more useful.", "source": "SpeakMate Grammar Notes: Comparatives", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/comparative-and-superlative-adjectives"},
    {"rule_id": "uncountable_nouns", "levels": ("A2", "B1", "B2"), "title": "Uncountable nouns", "content": "Advice, information, feedback, and equipment are normally uncountable in standard English and do not take a plural -s.", "source": "SpeakMate Grammar Notes: Countable and uncountable nouns", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/nouns-countable-and-uncountable"},
    {"rule_id": "because_so_conjunction", "levels": ("A2", "B1"), "title": "Because and so", "content": "Use because to give a reason or so to show a result, but not both in the same clause: Because I was tired, I went to bed early. / I was tired, so I went to bed early.", "source": "SpeakMate Grammar Notes: Conjunctions", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference"},
    {"rule_id": "although_but_conjunction", "levels": ("A2", "B1", "B2"), "title": "Although and but", "content": "Although already expresses contrast, so it is not combined with but in the same clause: Although it was raining, we still went out.", "source": "SpeakMate Grammar Notes: Conjunctions", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference"},
    {"rule_id": "pronoun_gender_confusion", "levels": ("A1", "A2"), "title": "He and she", "content": "English pronouns must match the gender of the person: use she for a woman or girl and he for a man or boy, even though the Chinese words sound the same.", "source": "SpeakMate Grammar Notes: Pronouns", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference"},
    {"rule_id": "countable_plural_missing", "levels": ("A1", "A2"), "title": "Plural countable nouns", "content": "A number or quantifier such as two, many, or several is followed by a plural countable noun: two books, many students.", "source": "SpeakMate Grammar Notes: Countable and uncountable nouns", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/quantifiers"},
    {"rule_id": "want_to_infinitive", "levels": ("A1", "A2"), "title": "Want to do", "content": "Verbs like want, need, hope, and plan are followed by to plus the base verb: I want to go home.", "source": "SpeakMate Grammar Notes: Verb patterns", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference"},
    {"rule_id": "very_adverb_position", "levels": ("A1", "A2"), "title": "Very with verbs", "content": "Very modifies adjectives or adverbs, not verbs. Say I really like it or I like it very much, not I very like it.", "source": "SpeakMate Grammar Notes: Adverbs", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference"},
    {"rule_id": "there_is_are_agreement", "levels": ("A1", "A2"), "title": "There is and there are", "content": "The verb in there is / there are agrees with the noun that follows: There are many people in the park. There is a book on the table.", "source": "SpeakMate Grammar Notes: There is and there are", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference"},
    {"rule_id": "time_preposition", "levels": ("A1", "A2", "B1"), "title": "Prepositions of time", "content": "Use on with days (on Monday), in with parts of the day (in the morning), and at with night, noon, and midnight (at night).", "source": "SpeakMate Grammar Notes: Prepositions of time", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference"},
    {"rule_id": "if_will_conditional", "levels": ("B1", "B2"), "title": "First conditional", "content": "In a real conditional, the if-clause uses the present simple, not will: If it rains, we will stay home.", "source": "SpeakMate Grammar Notes: Conditionals", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/present-simple"},
    {"rule_id": "so_such_confusion", "levels": ("B1", "B2"), "title": "So and such", "content": "So comes before an adjective (so beautiful), while such a/an comes before an adjective plus noun (such a beautiful place).", "source": "SpeakMate Grammar Notes: So and such", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference"},
    {"rule_id": "few_little_quantifier", "levels": ("B1",), "title": "A few and a little", "content": "A few goes with plural countable nouns (a few friends), and a little goes with uncountable nouns (a little water).", "source": "SpeakMate Grammar Notes: Quantifiers", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/quantifiers"},
    {"rule_id": "present_continuous_missing_be", "levels": ("A1", "A2"), "title": "Present continuous form", "content": "The present continuous is be plus the -ing form: I am going, she is cooking. Do not drop the be verb.", "source": "SpeakMate Grammar Notes: Present continuous", "source_url": "https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/present-continuous"},
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


class GrammarKnowledgeRetriever:
    """A local LangChain-compatible retriever with level-aware lexical ranking.

    The corpus is intentionally small and bundled with the application. It can
    later be replaced by a Chroma/FAISS vector store without changing the API.
    """

    def __init__(self, documents: tuple[dict[str, object], ...] = GRAMMAR_KNOWLEDGE):
        self.documents = tuple(
            Document(
                page_content=str(item["content"]),
                metadata={key: value for key, value in item.items() if key != "content"},
            )
            for item in documents
        )

    def invoke(self, query: str, *, level: str = "A2", rule_ids: list[str] | None = None, k: int = 4) -> list[Document]:
        level_code = (level or "A2").upper()
        query_tokens = _tokens(query)
        wanted = set(rule_ids or [])
        ranked: list[tuple[int, Document]] = []
        for document in self.documents:
            metadata = document.metadata
            levels = set(metadata.get("levels", ()))
            rule_id = str(metadata.get("rule_id", ""))
            score = len(query_tokens & _tokens(document.page_content + " " + str(metadata.get("title", ""))))
            if wanted and rule_id in wanted:
                score += 100
            if level_code in levels:
                score += 5
            elif levels and level_code not in levels:
                score -= 2
            ranked.append((score, document))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [document for score, document in ranked if score > 0][:k]

    def get_relevant_documents(self, query: str, level: str = "A2", k: int = 4) -> list[Document]:
        return self.invoke(query, level=level, k=k)


def knowledge_for_rule(rule_id: str, level: str = "A2") -> list[dict[str, object]]:
    retriever = GrammarKnowledgeRetriever()
    return [
        {**document.metadata, "content": document.page_content}
        for document in retriever.invoke(rule_id, level=level, rule_ids=[rule_id], k=1)
    ]
