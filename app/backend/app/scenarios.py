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


# 各场景「可直接套用的表达」：点击场景卡片进入课程简报时展示，
# 由 _scenario_brief 填充到 practice brief 的 target_expressions（不依赖 LLM，保证可靠）。
SCENARIO_EXPRESSIONS: dict[str, list[dict[str, str]]] = {
    "airport-check-in": [
        {"expression": "I'd like to check in for my flight, please.", "meaning_zh": "我想办理值机。", "example": "I'd like to check in for my flight to Shanghai, please.", "when_to_use": "走到柜台开口的第一句话"},
        {"expression": "Could you please help me with...?", "meaning_zh": "你能帮我……吗？", "example": "Could you please help me with my baggage?", "when_to_use": "需要协助时礼貌请求"},
        {"expression": "Is there a window seat available?", "meaning_zh": "还有靠窗的座位吗？", "example": "Is there a window seat available on this flight?", "when_to_use": "选座时询问"},
        {"expression": "How much baggage is included in my ticket?", "meaning_zh": "我的机票包含多少行李额？", "example": "How much baggage is included in my ticket?", "when_to_use": "确认行李额度"},
        {"expression": "What time does boarding start?", "meaning_zh": "什么时候开始登机？", "example": "What time does boarding start for this flight?", "when_to_use": "确认登机时间"},
    ],
    "hotel-check-in": [
        {"expression": "I have a reservation under the name...", "meaning_zh": "我用……的名字预订了房间。", "example": "I have a reservation under the name Wang.", "when_to_use": "办理入住时报预订信息"},
        {"expression": "My flight was delayed, so I arrived late.", "meaning_zh": "我的航班延误了，所以来晚了。", "example": "My flight was delayed, so I arrived late tonight.", "when_to_use": "解释晚到原因"},
        {"expression": "Could I get a room with a view, please?", "meaning_zh": "可以给我一间景观房吗？", "example": "Could I get a room with a view, please?", "when_to_use": "提出房间偏好"},
        {"expression": "What time is breakfast served?", "meaning_zh": "早餐几点供应？", "example": "What time is breakfast served in the morning?", "when_to_use": "询问早餐时间"},
        {"expression": "There's a problem with my room. The... doesn't work.", "meaning_zh": "我的房间有问题，……坏了。", "example": "There's a problem with my room. The air conditioner doesn't work.", "when_to_use": "反馈房间问题"},
    ],
    "restaurant-order": [
        {"expression": "Could I see the menu, please?", "meaning_zh": "请给我看一下菜单。", "example": "Could I see the menu, please?", "when_to_use": "入座后点餐前"},
        {"expression": "I'd like to order...", "meaning_zh": "我想点……", "example": "I'd like to order the grilled chicken, please.", "when_to_use": "点餐时说明要什么"},
        {"expression": "Does this dish contain any...?", "meaning_zh": "这道菜里含有……吗？", "example": "Does this dish contain any nuts or peanuts?", "when_to_use": "确认食材（过敏/忌口）"},
        {"expression": "Could you recommend something?", "meaning_zh": "你能推荐一下吗？", "example": "Could you recommend something popular here?", "when_to_use": "不知道点什么时请服务员推荐"},
        {"expression": "Could we have the bill, please?", "meaning_zh": "请给我们结账。", "example": "Could we have the bill, please?", "when_to_use": "用餐结束要求买单"},
    ],
    "job-interview": [
        {"expression": "Let me give you an example from my last job.", "meaning_zh": "让我举一个上份工作中的例子。", "example": "Let me give you an example from my last job.", "when_to_use": "用实例支撑回答时"},
        {"expression": "My greatest strength is...", "meaning_zh": "我最大的优势是……", "example": "My greatest strength is staying calm under pressure.", "when_to_use": "被问到优势时"},
        {"expression": "I handled this by...", "meaning_zh": "我是通过……处理这件事的。", "example": "I handled this by breaking the task into smaller steps.", "when_to_use": "讲述处理问题的过程"},
        {"expression": "What I learned from that experience was...", "meaning_zh": "我从那段经历中学到的是……", "example": "What I learned from that experience was to communicate early.", "when_to_use": "总结反思时"},
        {"expression": "Could you tell me more about the team?", "meaning_zh": "能多介绍一下团队吗？", "example": "Could you tell me more about the team I'd be working with?", "when_to_use": "面试最后主动提问"},
    ],
    "doctor-visit": [
        {"expression": "I've been feeling... for a few days.", "meaning_zh": "我这几天一直觉得……", "example": "I've been feeling tired and dizzy for a few days.", "when_to_use": "描述症状开始时间"},
        {"expression": "The pain is in my...", "meaning_zh": "疼痛在……部位。", "example": "The pain is in my lower back.", "when_to_use": "指明疼痛位置"},
        {"expression": "It started when...", "meaning_zh": "症状是从……开始的。", "example": "It started when I ran a marathon last weekend.", "when_to_use": "说明诱因"},
        {"expression": "On a scale of one to ten, it's about a...", "meaning_zh": "如果疼痛分 1 到 10 级，大概是……级。", "example": "On a scale of one to ten, it's about a six.", "when_to_use": "量化疼痛程度"},
        {"expression": "How often should I take this medicine?", "meaning_zh": "这药应该多久吃一次？", "example": "How often should I take this medicine?", "when_to_use": "确认服药方法"},
    ],
    "shopping-return": [
        {"expression": "I'd like to return this item.", "meaning_zh": "我想退掉这件商品。", "example": "I'd like to return this item. It doesn't fit.", "when_to_use": "开门见山说明来意"},
        {"expression": "I bought this here yesterday.", "meaning_zh": "这是我昨天在这里买的。", "example": "I bought this here yesterday and I have the receipt.", "when_to_use": "出示购买凭证"},
        {"expression": "There's a problem with it. It's...", "meaning_zh": "它有问题，……", "example": "There's a problem with it. It's damaged at the seam.", "when_to_use": "说明商品问题"},
        {"expression": "Could I exchange it for a different size?", "meaning_zh": "可以换一个尺码吗？", "example": "Could I exchange it for a different size?", "when_to_use": "提出换货"},
        {"expression": "What's your return policy?", "meaning_zh": "你们的退换货政策是什么？", "example": "What's your return policy for sale items?", "when_to_use": "确认退换政策"},
    ],
}


# 各场景开场白（按难度三档）：
# 18 张卡片 = 6 场景 × 3 档，每张开场白内容与复杂度都不同，
# 避免所有卡片都以同一条模板开场、对话雷同。
SCENARIO_OPENERS: dict[str, dict[str, str]] = {
    "airport-check-in": {
        "beginner": (
            "Welcome to check-in. May I see your passport and flight ticket, please? "
            "What is your name?"
        ),
        "intermediate": (
            "Good afternoon! I see you have an international flight today. "
            "Could you show me your passport and ticket? "
            "And would you prefer a window seat or an aisle seat this time?"
        ),
        "advanced": (
            "Good afternoon, and welcome! Before we proceed, could you hand me your passport and booking reference? "
            "I also noticed your itinerary has a tight connection in Singapore — "
            "would you like me to check whether we can move you to an earlier flight, or would you prefer to keep this one?"
        ),
    },
    "hotel-check-in": {
        "beginner": (
            "Hello! Welcome to our hotel. Do you have a reservation? What is your name, please?"
        ),
        "intermediate": (
            "Good evening, and welcome to the Grand Hotel! "
            "May I have your name to look up your reservation? "
            "And could you tell me what time you arrived today?"
        ),
        "advanced": (
            "Good evening, and welcome to the Grand Hotel — I hope your journey went smoothly. "
            "May I take your name to pull up your reservation? "
            "I see we received a note about a late arrival; was there any delay with your flight, "
            "and is there anything about the room we can prepare for you in advance?"
        ),
    },
    "restaurant-order": {
        "beginner": (
            "Hello! Welcome to our restaurant. Here is the menu. "
            "What would you like to eat or drink today?"
        ),
        "intermediate": (
            "Good evening! Let me get you a menu. "
            "Our grilled salmon and the mushroom risotto are quite popular tonight. "
            "Do you have any preferences — or any allergies I should know about?"
        ),
        "advanced": (
            "Good evening, and welcome! Tonight our chef is featuring a slow-braised short rib and a "
            "seasonal truffle pasta. If you tell me what you're in the mood for — light, rich, spicy — "
            "I can point you to the best options, and I'd also like to check whether there are any "
            "allergies or dietary restrictions I should keep in mind."
        ),
    },
    "job-interview": {
        "beginner": (
            "Hello. Please sit down. Tell me about yourself. What do you do now?"
        ),
        "intermediate": (
            "Nice to meet you. Let's start with a quick overview — "
            "could you walk me through your current role and one project you're proud of?"
        ),
        "advanced": (
            "Great to meet you. Before we dive into specifics, I'd like to hear how you frame your own career — "
            "tell me about the most challenging decision you've made in your current role, "
            "what made it difficult, and what you learned from the outcome."
        ),
    },
    "doctor-visit": {
        "beginner": (
            "Hello. Please sit down. What is wrong? Where do you feel pain?"
        ),
        "intermediate": (
            "Hello, I'm Dr. Lee. So what brings you in today? "
            "Can you tell me where exactly you're feeling discomfort and how long it's been going on?"
        ),
        "advanced": (
            "Good morning, I'm Dr. Lee. Let's start from the beginning — "
            "when did you first notice these symptoms, and have they been getting steadily worse? "
            "I'd also like to know whether anything you've tried so far has given you any relief at all."
        ),
    },
    "shopping-return": {
        "beginner": (
            "Hello! Welcome. Can I help you? Do you want to return something?"
        ),
        "intermediate": (
            "Hi there, how can I help you today? "
            "If you'd like to return or exchange something, do you have the receipt with you?"
        ),
        "advanced": (
            "Hello, welcome in! What can we do for you today? "
            "If you're here about an item, I'd be happy to look into it — "
            "do you happen to have the receipt or your order confirmation handy, "
            "and could you tell me what issue you've run into?"
        ),
    },
}


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
