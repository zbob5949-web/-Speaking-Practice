"""Curated role-play scenarios used by the speaking coach.

The catalog is deliberately deterministic. An LLM may enrich a lesson brief,
but it cannot silently change the learning objective or difficulty contract.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DifficultyBand:
    level: str
    vocabulary_range: str
    sentence_complexity: str
    target_functions: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    category: str
    background: str
    npc_role: str
    learner_role: str
    objective: str
    bands: tuple[DifficultyBand, ...]

    def to_dict(self, level: str | None = None) -> dict[str, object]:
        selected = select_band(self, level or "A2")
        data = asdict(self)
        data["bands"] = [asdict(band) for band in self.bands]
        data["difficulty"] = asdict(selected)
        return data


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        id="airport-check-in",
        category="出行",
        title="Airport check-in",
        background="You arrive at an airport and need to check in, choose a seat, and ask about baggage.",
        npc_role="Airline check-in agent",
        learner_role="Passenger",
        objective="Complete check-in and confirm baggage and boarding details.",
        bands=(
            DifficultyBand("A1", "80-150 high-frequency travel words", "Short present-tense requests", ("greet", "state destination", "ask for help")),
            DifficultyBand("A2", "150-300 travel and time words", "Because/when clauses and polite can/could requests", ("give booking details", "ask about baggage", "confirm time")),
            DifficultyBand("B1", "300-600 travel-service words", "Past explanations and connected follow-up questions", ("explain a problem", "negotiate a seat", "confirm a solution")),
            DifficultyBand("B2", "600-900 service and policy words", "Conditionals, modifiers, and precise clarification", ("compare options", "challenge a restriction", "summarize the agreement")),
            DifficultyBand("C1", "900+ nuanced service vocabulary", "Spontaneous multi-clause negotiation", ("handle an exception", "justify a request", "paraphrase policy")),
        ),
    ),
    Scenario(
        id="hotel-check-in",
        category="出行",
        title="Hotel check-in",
        background="You arrive at a hotel, explain a delayed flight, check your reservation, and request a room service.",
        npc_role="Hotel receptionist",
        learner_role="Guest",
        objective="Check in smoothly and resolve one reservation or room request.",
        bands=(
            DifficultyBand("A1", "80-150 hotel and personal words", "Simple be/have sentences", ("give your name", "show a booking", "ask for a key")),
            DifficultyBand("A2", "150-300 hotel and time words", "Past simple reasons plus polite requests", ("explain arrival", "ask about breakfast", "confirm checkout")),
            DifficultyBand("B1", "300-600 accommodation words", "Relative clauses and cause/effect connectors", ("report a booking issue", "request a change", "confirm alternatives")),
            DifficultyBand("B2", "600-900 hospitality and policy words", "Conditionals and nuanced complaints", ("negotiate compensation", "compare room options", "justify a preference")),
            DifficultyBand("C1", "900+ formal hospitality vocabulary", "Flexible register and complex negotiation", ("resolve a dispute", "reframe a policy", "reach a compromise")),
        ),
    ),
    Scenario(
        id="restaurant-order",
        category="餐饮",
        title="Restaurant order",
        background="You are ordering a meal, checking ingredients, and responding to a change in availability.",
        npc_role="Waiter or restaurant manager",
        learner_role="Diner",
        objective="Order a suitable meal and handle one dietary or availability constraint.",
        bands=(
            DifficultyBand("A1", "80-150 food words", "Short requests with like/want", ("choose a dish", "ask for water", "pay")),
            DifficultyBand("A2", "150-300 food and preference words", "Countable nouns and simple questions", ("ask about ingredients", "state a preference", "request the bill")),
            DifficultyBand("B1", "300-600 menu and dietary words", "Reason clauses and comparatives", ("explain a restriction", "choose an alternative", "give feedback")),
            DifficultyBand("B2", "600-900 culinary and service words", "Concessions, conditionals, and precise qualifiers", ("customize an order", "raise a problem", "propose a solution")),
            DifficultyBand("C1", "900+ nuanced food and service vocabulary", "Persuasive and tactful discourse", ("discuss provenance", "resolve a service failure", "recommend an option")),
        ),
    ),
    Scenario(
        id="job-interview",
        category="职场",
        title="Job interview",
        background="You are interviewing for a role and must describe experience, strengths, and a response to a work problem.",
        npc_role="Hiring manager",
        learner_role="Candidate",
        objective="Answer competency questions with evidence and ask one informed question.",
        bands=(
            DifficultyBand("A1", "100-200 work and personal words", "Simple past and present sentences", ("introduce yourself", "state a skill", "answer a simple question")),
            DifficultyBand("A2", "200-400 common workplace words", "Past events with first/then/because", ("describe a task", "state a strength", "ask about work")),
            DifficultyBand("B1", "400-700 role-specific words", "STAR-style narratives and contrasting clauses", ("give evidence", "explain a challenge", "ask a follow-up")),
            DifficultyBand("B2", "700-1100 professional vocabulary", "Conditionals, passive voice, and nuanced claims", ("defend a decision", "compare approaches", "discuss trade-offs")),
            DifficultyBand("C1", "1100+ domain and strategic vocabulary", "Structured persuasive answers with register control", ("lead a case discussion", "challenge an assumption", "summarize impact")),
        ),
    ),
    Scenario(
        id="doctor-visit",
        category="医疗",
        title="Doctor visit",
        background="You describe symptoms, answer follow-up questions, and clarify a treatment instruction.",
        npc_role="Doctor or nurse",
        learner_role="Patient",
        objective="Describe symptoms accurately and confirm what to do next.",
        bands=(
            DifficultyBand("A1", "80-160 body and symptom words", "Simple have/be sentences", ("name a symptom", "say when it started", "ask for help")),
            DifficultyBand("A2", "160-320 health and time words", "Since/for, frequency, and simple comparisons", ("describe duration", "rate severity", "confirm medicine")),
            DifficultyBand("B1", "320-650 health-service words", "Sequenced history and conditional advice", ("explain change", "report a response", "ask about warning signs")),
            DifficultyBand("B2", "650-1000 clinical and lifestyle words", "Precise qualifiers and reported information", ("compare symptoms", "clarify risk", "summarize instructions")),
            DifficultyBand("C1", "1000+ nuanced health vocabulary", "Tactful, precise explanation of uncertainty", ("question a plan", "weigh options", "negotiate follow-up")),
        ),
    ),
    Scenario(
        id="shopping-return",
        category="购物",
        title="Shopping and return",
        background="You bought an item, discover a problem, and ask a shop assistant about an exchange or refund.",
        npc_role="Shop assistant",
        learner_role="Customer",
        objective="Explain the issue, refer to the purchase, and agree on a remedy.",
        bands=(
            DifficultyBand("A1", "80-160 shopping words", "Short statements and can/can't", ("name an item", "state a problem", "ask the price")),
            DifficultyBand("A2", "160-320 shopping and payment words", "Past purchase details and polite questions", ("show a receipt", "ask for an exchange", "confirm a size")),
            DifficultyBand("B1", "320-650 product and policy words", "Cause/effect and comparison", ("describe a defect", "explain preference", "ask about policy")),
            DifficultyBand("B2", "650-1000 consumer-service words", "Conditionals and tactful disagreement", ("challenge a decision", "propose a remedy", "summarize terms")),
            DifficultyBand("C1", "1000+ formal consumer vocabulary", "Persuasive complaint with concessions", ("escalate a case", "reference evidence", "reach a fair settlement")),
        ),
    ),
)

SCENARIOS_INDEX: dict[str, int] = {scenario.id: index for index, scenario in enumerate(SCENARIOS)}


LEVEL_ORDER = {"A1": 0, "A2": 1, "B1": 2, "B2": 3, "C1": 4}


def normalize_level(level: str) -> str:
    text = (level or "A2").upper()
    for code in LEVEL_ORDER:
        if code in text:
            return code
    if "BEGIN" in text:
        return "A1"
    if "INTER" in text:
        return "B1"
    if "ADV" in text:
        return "B2"
    return "A2"


def select_band(scenario: Scenario, level: str) -> DifficultyBand:
    requested = LEVEL_ORDER[normalize_level(level)]
    return min(scenario.bands, key=lambda band: abs(LEVEL_ORDER[band.level] - requested))


def list_scenarios(level: str | None = None) -> list[dict[str, object]]:
    return [scenario.to_dict(level) for scenario in SCENARIOS]


def get_scenario(scenario_id: str, level: str | None = None) -> dict[str, object] | None:
    scenario = next((item for item in SCENARIOS if item.id == scenario_id), None)
    return scenario.to_dict(level) if scenario else None


def list_categories() -> list[str]:
    """全部背景设定分类（保持首次出现顺序）。"""
    seen: list[str] = []
    for scenario in SCENARIOS:
        if scenario.category not in seen:
            seen.append(scenario.category)
    return seen


def list_roles() -> list[str]:
    """全部角色描述（NPC 角色）。"""
    seen: list[str] = []
    for scenario in SCENARIOS:
        if scenario.npc_role not in seen:
            seen.append(scenario.npc_role)
    return seen


# 难度分级：小白/中级/大神 对应的 CEFR 等级区间
TIER_LEVELS: dict[str, tuple[str, ...]] = {
    "beginner": ("A1", "A2"),
    "intermediate": ("B1", "B2"),
    "advanced": ("C1",),
}


def tier_for_level(level: str) -> str:
    """把用户水平表述映射到 小白/中级/大神。"""
    text = (level or "").upper()
    if any(key in text for key in ("BEGIN", "小白", "初级", "入门", "A1", "A2")):
        return "beginner"
    if any(key in text for key in ("INTER", "中级", "IELTS", "CET-6", "CET6", "六级", "四级")):
        return "intermediate"
    if any(key in text for key in ("ADV", "大神", "高级", "精通", "C1", "专八")):
        return "advanced"
    return "intermediate"


def learning_path(tier: str = "intermediate") -> dict[str, object]:
    """按 小白/中级/大神 生成学习路线：该难度带内的全部场景卡片，由易到难。"""
    tier = tier if tier in TIER_LEVELS else "intermediate"
    codes = TIER_LEVELS[tier]
    items = [scenario.to_dict(codes[0]) for scenario in SCENARIOS]
    # 路线内按难度升序（A1 < A2 < B1 ...），同难度保持定义顺序
    order = {code: index for index, code in enumerate(LEVEL_ORDER)}
    items.sort(key=lambda item: (order.get(item["difficulty"]["level"], 99), SCENARIOS_INDEX[item["id"]]))
    return {
        "tier": tier,
        "level": codes[0],
        "levels": list(codes),
        "path": items,
    }
