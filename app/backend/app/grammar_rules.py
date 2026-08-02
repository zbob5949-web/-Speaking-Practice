"""Deterministic grammar rules run before any LLM analysis."""

from dataclasses import dataclass
import re
from typing import Callable


@dataclass(frozen=True)
class GrammarRule:
    rule_id: str
    error_type: str
    title: str
    explanation_zh: str
    source_key: str


@dataclass(frozen=True)
class RuleMatch:
    rule_id: str
    error_type: str
    original_fragment: str
    better_expression: str
    reason_zh: str
    severity: str
    confidence: float

    def to_dict(self) -> dict[str, object]:
        return {
            "feedback_type": "grammar",
            "rule_id": self.rule_id,
            "error_type": self.error_type,
            "feedback_text": f"{self.original_fragment} -> {self.better_expression}",
            "original_fragment": self.original_fragment,
            "better_expression": self.better_expression,
            "reason_zh": self.reason_zh,
            "severity": self.severity,
            "confidence": self.confidence,
        }


RULES: tuple[GrammarRule, ...] = (
    GrammarRule("subject_verb_agreement", "主谓一致", "主语和动词一致", "第三人称单数、be 动词和 have 要与主语匹配。", "subject_verb_agreement"),
    GrammarRule("third_person_present", "第三人称单数", "一般现在时第三人称", "he、she、it 后面的实义动词通常需要 -s 或 -es。", "third_person_present"),
    GrammarRule("past_simple", "一般过去时", "过去时间搭配", "yesterday、last...、...ago 等已结束时间通常搭配过去式。", "past_simple"),
    GrammarRule("present_perfect", "现在完成时", "have/has + 过去分词", "现在完成时需要 have/has 加过去分词。", "present_perfect"),
    GrammarRule("article_a_an", "冠词", "不定冠词", "单数可数名词第一次出现时通常需要 a 或 an。", "article_a_an"),
    GrammarRule("quantifiers", "数量词", "many/much 搭配", "many 修饰可数名词复数，much 修饰不可数名词。", "quantifiers"),
    GrammarRule("preposition_collocation", "介词搭配", "固定介词搭配", "部分形容词和动词需要固定介词搭配。", "preposition_collocation"),
    GrammarRule("gerund_infinitive", "非谓语动词", "动词后接形式", "enjoy/avoid/finish 后接动名词，want/need/hope 后接 to do。", "gerund_infinitive"),
    GrammarRule("modal_base_form", "情态动词", "情态动词后接原形", "can、should、must 后直接使用动词原形。", "modal_base_form"),
    GrammarRule("question_word_order", "疑问句语序", "疑问句倒装", "多数特殊疑问句需要把助动词或 be 动词放到主语前。", "question_word_order"),
    GrammarRule("comparative_form", "比较级", "比较级形式", "不要把 more 与已经带比较级的形容词重复使用。", "comparative_form"),
    GrammarRule("uncountable_nouns", "不可数名词", "不可数名词复数", "advice、information、feedback 等通常不加复数 -s。", "uncountable_nouns"),
    GrammarRule("because_so_conjunction", "连词冗余", "because 与 so 连用", "汉语“因为…所以…”成对迁移，英语一个连词即可。", "because_so_conjunction"),
    GrammarRule("although_but_conjunction", "让步连词冗余", "although 与 but 连用", "although 已表达让步，不能再加 but。", "although_but_conjunction"),
    GrammarRule("pronoun_gender_confusion", "人称代词性别混淆", "he/she 与性别名词不一致", "汉语“他/她”同音，英语代词要与所指的性别一致。", "pronoun_gender_confusion"),
    GrammarRule("countable_plural_missing", "可数名词漏复数", "数量词后的可数名词用复数", "中文没有复数概念，数字或数量词后的可数名词要用复数形式。", "countable_plural_missing"),
    GrammarRule("want_to_infinitive", "不定式缺失", "want 后接 to do", "want、need、hope、plan 等动词后要用 to 加动词原形。", "want_to_infinitive"),
    GrammarRule("very_adverb_position", "副词误用", "very 不能直接修饰动词", "very 修饰形容词或副词，动词前用 really，或用 like ... very much。", "very_adverb_position"),
    GrammarRule("there_is_are_agreement", "there be 一致", "there is 与复数主语", "there be 的 be 要与后面的名词一致，复数名词用 there are。", "there_is_are_agreement"),
    GrammarRule("time_preposition", "时间介词搭配", "in/at/on 时间误用", "星期用 on，一天中的时段用 in the，night/noon/midnight 用 at。", "time_preposition"),
    GrammarRule("if_will_conditional", "条件句时态", "if 从句不用 will", "if 条件从句用一般现在时表示将来，不用 will。", "if_will_conditional"),
    GrammarRule("so_such_confusion", "so/such 误用", "so 与 such 结构", "so 后接形容词，such a/an 后接形容词加名词。", "so_such_confusion"),
    GrammarRule("few_little_quantifier", "数量词误用", "a few 与 a little", "a few 修饰可数名词复数，a little 修饰不可数名词。", "few_little_quantifier"),
    GrammarRule("present_continuous_missing_be", "现在进行时缺 be", "进行时缺 be 动词", "现在进行时用 be + 动词ing，不能省略 be。", "present_continuous_missing_be"),
)

_BASE_VERBS = {"go", "come", "work", "live", "like", "want", "need", "have", "do", "make", "take", "eat", "see", "study", "watch", "play", "ask", "book", "call", "arrive", "start", "finish", "visit", "buy", "pay", "feel", "look", "use", "speak", "drive", "get"}
_PAST_FORMS = {"go": "went", "come": "came", "have": "had", "do": "did", "make": "made", "take": "took", "eat": "ate", "see": "saw", "buy": "bought", "get": "got", "feel": "felt", "speak": "spoke", "drive": "drove", "write": "wrote"}
_PARTICIPLES = {"went": "gone", "came": "come", "had": "had", "did": "done", "made": "made", "took": "taken", "ate": "eaten", "saw": "seen", "bought": "bought", "got": "gotten", "felt": "felt", "spoke": "spoken", "drove": "driven", "wrote": "written"}
_COUNTABLE = {"apples", "books", "tickets", "bags", "people", "rooms", "questions", "problems", "options", "ideas", "emails"}
_UNCOUNTABLE = {"water", "information", "advice", "feedback", "money", "time", "equipment", "help", "rice", "work"}
_ARTICLE_NOUNS = {"student", "teacher", "doctor", "manager", "passenger", "guest", "customer", "engineer", "employee", "candidate"}


def _match(rule_id: str, error_type: str, fragment: str, better: str, reason: str, severity: str = "medium", confidence: float = 0.94) -> RuleMatch:
    return RuleMatch(rule_id, error_type, fragment, better, reason, severity, confidence)


def _subject_verb(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    patterns = [
        (r"\b(he|she|it)\s+(are|am)\b", "is"),
        (r"\b(i)\s+is\b", "am"),
        (r"\b(you|we|they)\s+is\b", "are"),
        (r"\b(he|she|it)\s+have\b", "has"),
        (r"\b(you|we|they)\s+has\b", "have"),
        (r"\b(he|she|it)\s+don't\b", "doesn't"),
        (r"\b(you|we|they)\s+doesn't\b", "don't"),
    ]
    for pattern, replacement in patterns:
        for found in re.finditer(pattern, text, flags=re.IGNORECASE):
            fragment = found.group(0)
            subject = fragment.split()[0]
            better = re.sub(r"\S+$", replacement, fragment)
            matches.append(_match("subject_verb_agreement", "主谓一致", fragment, better, "主语与 be/have/do 的形式不匹配。"))
    return matches


def _third_person(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for found in re.finditer(r"\b(he|she|it)\s+([a-z]+)\b", text, flags=re.IGNORECASE):
        verb = found.group(2).lower()
        if verb not in _BASE_VERBS or verb in {"is", "has", "does"}:
            continue
        if verb == "have":
            inflected = "has"
        elif verb == "do":
            inflected = "does"
        elif verb.endswith(("s", "sh", "ch", "x", "o")):
            inflected = verb + "es"
        elif verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
            inflected = verb[:-1] + "ies"
        else:
            inflected = verb + "s"
        fragment = found.group(0)
        matches.append(_match("third_person_present", "第三人称单数", fragment, f"{found.group(1)} {inflected}", "一般现在时的 he、she、it 后面需要第三人称单数形式。"))
    return matches


def _past_simple(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    if not re.search(r"\b(yesterday|last\s+\w+|\d+\s+days?\s+ago)\b", text, re.IGNORECASE):
        return matches
    for found in re.finditer(r"\b(I|he|she|we|they|you)\s+(" + "|".join(sorted(_BASE_VERBS, key=len, reverse=True)) + r")\b", text, flags=re.IGNORECASE):
        verb = found.group(2).lower()
        past = _PAST_FORMS.get(verb, verb + "d" if verb.endswith("e") else verb + "ed")
        fragment = found.group(0)
        matches.append(_match("past_simple", "一般过去时", fragment, f"{found.group(1)} {past}", "句子包含已结束的过去时间，需要使用过去式。"))
    return matches


def _present_perfect(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for found in re.finditer(r"\b(have|has)\s+(" + "|".join(_PARTICIPLES) + r")\b", text, flags=re.IGNORECASE):
        past = found.group(2).lower()
        corrected = _PARTICIPLES[past]
        matches.append(_match("present_perfect", "现在完成时", found.group(0), f"{found.group(1)} {corrected}", "have/has 后需要过去分词，而不是一般过去时形式。"))
    return matches


def _article(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for found in re.finditer(r"\b(I|he|she|we|they)\s+(am|is|are)\s+(" + "|".join(_ARTICLE_NOUNS) + r")\b", text, flags=re.IGNORECASE):
        article = "an" if found.group(3)[0].lower() in "aeiou" else "a"
        fragment = found.group(0)
        better = f"{found.group(1)} {found.group(2)} {article} {found.group(3)}"
        matches.append(_match("article_a_an", "冠词", fragment, better, "单数可数职业或身份名词前需要不定冠词。"))
    return matches


def _quantifiers(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for found in re.finditer(r"\b(many|much)\s+([a-z]+)\b", text, flags=re.IGNORECASE):
        quantifier, noun = found.group(1).lower(), found.group(2).lower()
        if quantifier == "much" and noun in _COUNTABLE:
            matches.append(_match("quantifiers", "数量词", found.group(0), f"many {noun}", "many 修饰可数名词复数。"))
        elif quantifier == "many" and noun in _UNCOUNTABLE:
            matches.append(_match("quantifiers", "数量词", found.group(0), f"much {noun}", "much 修饰不可数名词。"))
    return matches


def _prepositions(text: str) -> list[RuleMatch]:
    replacements = {"interested on": "interested in", "good in": "good at", "depend of": "depend on", "married with": "married to", "discuss about": "discuss", "arrive to": "arrive at/in"}
    matches: list[RuleMatch] = []
    for wrong, right in replacements.items():
        for found in re.finditer(r"\b" + re.escape(wrong) + r"\b", text, flags=re.IGNORECASE):
            matches.append(_match("preposition_collocation", "介词搭配", found.group(0), right, "这里应使用更自然的固定介词搭配。"))
    return matches


def _verb_patterns(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for found in re.finditer(r"\b(enjoy|avoid|finish)\s+to\s+([a-z]+)\b", text, flags=re.IGNORECASE):
        matches.append(_match("gerund_infinitive", "非谓语动词", found.group(0), f"{found.group(1)} {found.group(2)}ing", "enjoy、avoid、finish 后面通常使用动名词。"))
    for found in re.finditer(r"\b(want|need|hope)\s+([a-z]+ing)\b", text, flags=re.IGNORECASE):
        base = found.group(2)[:-3]
        matches.append(_match("gerund_infinitive", "非谓语动词", found.group(0), f"{found.group(1)} to {base}", "want、need、hope 后面通常使用 to 加动词原形。"))
    return matches


def _modal(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for found in re.finditer(r"\b(can|could|should|must|may|might)\s+(?:to\s+)?([a-z]+)\b", text, flags=re.IGNORECASE):
        modal, verb = found.group(1), found.group(2).lower()
        if "to" not in found.group(0).lower() and verb not in _PAST_FORMS:
            continue
        base = next((key for key, value in _PAST_FORMS.items() if value == verb), verb)
        better = f"{modal} {base}"
        matches.append(_match("modal_base_form", "情态动词", found.group(0), better, "情态动词后直接接动词原形，不加 to，也不用过去式。"))
    return matches


def _question_order(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    patterns = [
        (r"\b(what|where|when|why|how)\s+(you|he|she|they|we)\s+(are|is|am)\b", lambda m: f"{m.group(1)} {m.group(3)} {m.group(2)}"),
        (r"\b(what|where|when|why|how)\s+(you|he|she|they|we)\s+(do|does|did)\b", lambda m: f"{m.group(1)} {m.group(3)} {m.group(2)}"),
    ]
    for pattern, builder in patterns:
        for found in re.finditer(pattern, text, flags=re.IGNORECASE):
            matches.append(_match("question_word_order", "疑问句语序", found.group(0), builder(found), "特殊疑问句中助动词或 be 动词需要放在主语前。"))
    return matches


def _comparative(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for found in re.finditer(r"\b(more\s+(better|easier|bigger|smaller|faster)|most\s+(best|easiest))\b", text, flags=re.IGNORECASE):
        word = found.group(2) or found.group(3)
        corrected = {"better": "better", "easier": "easier", "bigger": "bigger", "smaller": "smaller", "faster": "faster", "best": "best", "easiest": "easiest"}[word.lower()]
        matches.append(_match("comparative_form", "比较级", found.group(0), corrected, "more 或 most 不能与已经变化过的比较级/最高级重复。"))
    return matches


def _uncountable(text: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for found in re.finditer(r"\b(informations|advices|feedbacks|equipments)\b", text, flags=re.IGNORECASE):
        matches.append(_match("uncountable_nouns", "不可数名词", found.group(0), found.group(0)[:-1], "该名词通常是不可数名词，不需要复数 -s。"))
    return matches


_FEMALE_NOUNS = {"sister", "mother", "aunt", "grandmother", "grandma", "girl", "woman", "wife", "daughter", "girlfriend", "niece", "lady"}
_MALE_NOUNS = {"brother", "father", "uncle", "grandfather", "grandpa", "boy", "man", "husband", "son", "boyfriend", "nephew", "gentleman"}


def _snippet(text: str, word: str) -> str:
    match = re.search(r"\b" + word + r"\b", text, re.IGNORECASE)
    if not match:
        return text.strip()[:60]
    start = max(0, match.start() - 15)
    end = min(len(text), match.end() + 25)
    return text[start:end].strip()


def _conjunction_doubling(text: str, first: str, second: str, rule_id: str, error_type: str, reason: str) -> list[RuleMatch]:
    matches = []
    pattern = re.compile(r"\b" + first + r"\b[^.!?;]*?\b" + second + r"\b[^.!?;]*", re.IGNORECASE)
    for found in pattern.finditer(text):
        fragment = found.group(0)
        better = re.sub(r"\b,\s*" + second + r"\b|\b" + second + r"\b", ", ", fragment, count=1, flags=re.IGNORECASE)
        better = re.sub(r"\s+", " ", better).strip()
        matches.append(_match(rule_id, error_type, fragment, better, reason, severity="medium", confidence=0.9))
    return matches


def _because_so(text: str) -> list[RuleMatch]:
    return _conjunction_doubling(text, "because", "so", "because_so_conjunction", "连词冗余", "because 与 so 只需保留一个，汉语“因为…所以…”不能直接搬到英语。")


def _although_but(text: str) -> list[RuleMatch]:
    return _conjunction_doubling(text, "although", "but", "although_but_conjunction", "让步连词冗余", "although 已表达让步，后面的 but 需要删掉。")


def _pronoun_gender(text: str) -> list[RuleMatch]:
    matches = []
    for segment in re.split(r"[.!?;]", text):
        low = segment.lower()
        female_noun = next((noun for noun in _FEMALE_NOUNS if re.search(r"\b" + noun + r"\b", low)), None)
        male_noun = next((noun for noun in _MALE_NOUNS if re.search(r"\b" + noun + r"\b", low)), None)
        if female_noun and re.search(r"\bhe\b", low):
            matches.append(_match("pronoun_gender_confusion", "人称代词性别混淆", _snippet(segment, "he"), "she", f"句子提到女性身份（{female_noun}），代词用 she 而不是 he（中文“他/她”同音，英语要区分）。", severity="low", confidence=0.6))
        elif male_noun and re.search(r"\bshe\b", low):
            matches.append(_match("pronoun_gender_confusion", "人称代词性别混淆", _snippet(segment, "she"), "he", f"句子提到男性身份（{male_noun}），代词用 he 而不是 she。", severity="low", confidence=0.6))
    return matches


_COUNT_NOUNS = {
    "book": "books", "student": "students", "friend": "friends", "ticket": "tickets", "bag": "bags",
    "room": "rooms", "apple": "apples", "question": "questions", "problem": "problems", "day": "days",
    "hour": "hours", "minute": "minutes", "week": "weeks", "month": "months", "year": "years",
    "dollar": "dollars", "idea": "ideas", "email": "emails", "phone": "phones", "table": "tables",
    "chair": "chairs", "car": "cars", "bus": "buses", "train": "trains", "plane": "planes",
    "hotel": "hotels", "restaurant": "restaurants", "store": "stores", "shop": "shops", "city": "cities",
    "country": "countries", "teacher": "teachers", "doctor": "doctors", "engineer": "engineers",
    "manager": "managers", "customer": "customers", "guest": "guests", "passenger": "passengers",
    "member": "members", "colleague": "colleagues", "meeting": "meetings", "appointment": "appointments",
    "reservation": "reservations", "flight": "flights", "option": "options", "example": "examples",
    "place": "places", "job": "jobs", "child": "children", "person": "people", "man": "men",
    "woman": "women", "foot": "feet", "tooth": "teeth",
}
_PLURAL_QUANTIFIERS = r"(?:two|three|four|five|six|seven|eight|nine|ten|many|several|a few|both|these|those|a couple of|a lot of)"


def _countable_plural(text: str) -> list[RuleMatch]:
    matches = []
    for found in re.finditer(r"\b(" + _PLURAL_QUANTIFIERS + r")\s+([a-z]+)\b", text, re.IGNORECASE):
        noun = found.group(2).lower()
        if noun in _COUNT_NOUNS:
            matches.append(_match("countable_plural_missing", "可数名词漏复数", found.group(0), f"{found.group(1)} {_COUNT_NOUNS[noun]}", "数字或数量词后面的可数名词要用复数（中文没有复数概念，注意加 -s 或变化形式）。", severity="medium", confidence=0.8))
    return matches


_WANT_TO_VERBS = r"(?:want|wants|wanted|need|needs|needed|hope|hopes|hoped|plan|plans|planned|decide|decides|decided|learn|learns|learned)"


def _want_to(text: str) -> list[RuleMatch]:
    matches = []
    verbs = "|".join(sorted(_BASE_VERBS, key=len, reverse=True))
    for found in re.finditer(r"\b(" + _WANT_TO_VERBS + r")\s+(" + verbs + r")\b", text, re.IGNORECASE):
        matches.append(_match("want_to_infinitive", "不定式缺失", found.group(0), f"{found.group(1)} to {found.group(2).lower()}", "want/need/hope/plan 等动词后面要接 to 加动词原形，不能直接跟动词。", severity="medium", confidence=0.9))
    return matches


_VERBS_AFTER_VERY = r"(?:like|enjoy|love|want|need|agree|hate|hope|understand|know|believe|think|care|mind|appreciate|prefer|dislike|miss|admire|respect|trust|doubt|wish)"


def _very_adverb(text: str) -> list[RuleMatch]:
    matches = []
    for found in re.finditer(r"\bvery\s+(" + _VERBS_AFTER_VERY + r")\b", text, re.IGNORECASE):
        verb = found.group(1).lower()
        matches.append(_match("very_adverb_position", "副词误用", found.group(0), f"really {verb}", "very 修饰形容词或副词，不能直接修饰动词；可以说 really like 或 like ... very much。", severity="medium", confidence=0.85))
    return matches


def _there_be(text: str) -> list[RuleMatch]:
    matches = []
    for found in re.finditer(r"\bthere\s+is\s+(many|several|a few|two|three|four|five|six|seven|eight|nine|ten)\s+([a-z]+)\b", text, re.IGNORECASE):
        matches.append(_match("there_is_are_agreement", "there be 一致", found.group(0), f"there are {found.group(1)} {found.group(2)}", "there be 的 be 要与后面的名词一致，复数名词用 there are。", severity="medium", confidence=0.9))
    for found in re.finditer(r"\bthere\s+are\s+(a|an)\s+(?!few|lot)([a-z]+)\b", text, re.IGNORECASE):
        matches.append(_match("there_is_are_agreement", "there be 一致", found.group(0), f"there is {found.group(1)} {found.group(2)}", "单数名词前面用 there is。", severity="medium", confidence=0.9))
    return matches


_TIME_PREPOSITIONS = {
    "monday": ("on", "on Monday"), "tuesday": ("on", "on Tuesday"), "wednesday": ("on", "on Wednesday"),
    "thursday": ("on", "on Thursday"), "friday": ("on", "on Friday"), "saturday": ("on", "on Saturday"),
    "sunday": ("on", "on Sunday"), "weekend": ("on", "at the weekend"),
    "morning": ("in", "in the morning"), "afternoon": ("in", "in the afternoon"), "evening": ("in", "in the evening"),
    "night": ("at", "at night"), "noon": ("at", "at noon"), "midnight": ("at", "at midnight"),
}


def _time_preposition(text: str) -> list[RuleMatch]:
    matches = []
    for word, (correct_prep, fixed) in _TIME_PREPOSITIONS.items():
        for found in re.finditer(r"\b(in|at|on)\s+" + word + r"\b", text, re.IGNORECASE):
            if word != "weekend" and found.group(1).lower() == correct_prep:
                continue
            matches.append(_match("time_preposition", "时间介词搭配", found.group(0), fixed, f"表示 {word} 时通常说 {fixed}，注意与中文的“在…”不同。", severity="medium", confidence=0.9))
    return matches


def _third_person_singular(verb: str) -> str:
    if verb in {"is", "has", "does"}:
        return verb
    if verb == "have":
        return "has"
    if verb == "do":
        return "does"
    if verb.endswith(("s", "sh", "ch", "x", "o")):
        return verb + "es"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
    return verb + "s"


def _if_will(text: str) -> list[RuleMatch]:
    matches = []
    for found in re.finditer(r"\bif\s+(i|you|he|she|it|we|they)\s+will\s+([a-z]+)\b", text, re.IGNORECASE):
        subj = found.group(1).lower()
        verb = found.group(2).lower()
        present = _third_person_singular(verb) if subj in {"he", "she", "it"} else verb
        matches.append(_match("if_will_conditional", "条件句时态", found.group(0), f"if {subj} {present}", "if 条件从句用一般现在时表示将来，不用 will。", severity="low", confidence=0.65))
    return matches


def _so_such(text: str) -> list[RuleMatch]:
    matches = []
    for found in re.finditer(r"\bso\s+(a|an)\s+([a-z]+)\b", text, re.IGNORECASE):
        matches.append(_match("so_such_confusion", "so/such 误用", found.group(0), f"such {found.group(1)} {found.group(2)}", "so 后接形容词，such a/an 后接形容词加名词。", severity="medium", confidence=0.85))
    return matches


_LITTLE_COUNTABLE = {"friends", "people", "books", "days", "questions", "problems", "tickets", "rooms", "apples", "ideas", "emails", "students", "teachers", "hours", "minutes", "weeks", "months", "years", "dollars", "options", "examples", "times", "places", "children"}
_FEW_UNCOUNTABLE = {"water", "money", "time", "information", "advice", "feedback", "rice", "work", "help", "equipment", "furniture", "news", "research", "knowledge", "traffic", "weather", "bread", "coffee", "tea", "juice", "milk", "sugar", "salt", "fun", "progress", "homework"}


def _few_little(text: str) -> list[RuleMatch]:
    matches = []
    for found in re.finditer(r"\ba\s+little\s+([a-z]+)\b", text, re.IGNORECASE):
        noun = found.group(1).lower()
        if noun in _LITTLE_COUNTABLE:
            matches.append(_match("few_little_quantifier", "数量词误用", found.group(0), f"a few {noun}", "a few 修饰可数名词复数，a little 修饰不可数名词。", severity="medium", confidence=0.85))
    for found in re.finditer(r"\ba\s+few\s+([a-z]+)\b", text, re.IGNORECASE):
        noun = found.group(1).lower()
        if noun in _FEW_UNCOUNTABLE:
            matches.append(_match("few_little_quantifier", "数量词误用", found.group(0), f"a little {noun}", "a little 修饰不可数名词，a few 修饰可数名词复数。", severity="medium", confidence=0.85))
    return matches


_ING_VERBS = {"going", "coming", "working", "living", "doing", "making", "taking", "eating", "seeing", "watching", "playing", "studying", "asking", "booking", "calling", "arriving", "leaving", "starting", "finishing", "visiting", "buying", "paying", "feeling", "looking", "using", "speaking", "driving", "getting", "walking", "running", "cooking", "sleeping", "reading", "writing", "learning", "waiting", "staying", "talking", "listening", "shopping", "swimming", "flying", "sitting", "standing", "trying"}
_ING_NONVERBS = {"morning", "evening", "thing", "something", "anything", "everything", "nothing", "during", "according", "interesting", "exciting", "boring", "amazing", "surprising", "willing", "ceiling", "building", "meeting", "training"}
_BE_FOR_SUBJECT = {"i": "am", "you": "are", "we": "are", "they": "are", "he": "is", "she": "is", "it": "is"}


def _present_continuous(text: str) -> list[RuleMatch]:
    matches = []
    pattern = re.compile(r"\b(i|you|we|they|he|she|it)\s+(?!am\b|is\b|are\b|was\b|were\b|can\b|will\b|should\b|could\b|would\b|may\b|might\b|must\b|do\b|does\b|did\b|have\b|has\b|had\b)([a-z]+ing)\b", re.IGNORECASE)
    for found in pattern.finditer(text):
        verb = found.group(2).lower()
        if verb in _ING_NONVERBS or verb not in _ING_VERBS:
            continue
        subj = found.group(1).lower()
        matches.append(_match("present_continuous_missing_be", "现在进行时缺 be", found.group(0), f"{subj} {_BE_FOR_SUBJECT[subj]} {verb}", "现在进行时是 be + 动词ing，不能省略 be 动词。", severity="medium", confidence=0.75))
    return matches


CHECKERS: dict[str, Callable[[str], list[RuleMatch]]] = {
    "subject_verb_agreement": _subject_verb,
    "third_person_present": _third_person,
    "past_simple": _past_simple,
    "present_perfect": _present_perfect,
    "article_a_an": _article,
    "quantifiers": _quantifiers,
    "preposition_collocation": _prepositions,
    "gerund_infinitive": _verb_patterns,
    "modal_base_form": _modal,
    "question_word_order": _question_order,
    "comparative_form": _comparative,
    "uncountable_nouns": _uncountable,
    "because_so_conjunction": _because_so,
    "although_but_conjunction": _although_but,
    "pronoun_gender_confusion": _pronoun_gender,
    "countable_plural_missing": _countable_plural,
    "want_to_infinitive": _want_to,
    "very_adverb_position": _very_adverb,
    "there_is_are_agreement": _there_be,
    "time_preposition": _time_preposition,
    "if_will_conditional": _if_will,
    "so_such_confusion": _so_such,
    "few_little_quantifier": _few_little,
    "present_continuous_missing_be": _present_continuous,
}


class RuleBasedGrammarChecker:
    def check(self, text: str) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        for rule in RULES:
            matches.extend(CHECKERS[rule.rule_id](text))
        unique: dict[tuple[str, str, str], RuleMatch] = {}
        for match in matches:
            unique[(match.rule_id, match.original_fragment.lower(), match.better_expression.lower())] = match
        return list(unique.values())
