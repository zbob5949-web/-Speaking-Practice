from app.agents import ConversationAgent
from app.llm import FakeLLMProvider
from typing import Iterator
import json

class MockChatProvider(FakeLLMProvider):
    def __init__(self):
        super().__init__()
        self.last_system = ""
        self.last_user = ""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system = system_prompt
        self.last_user = user_prompt
        return json.dumps({
            "reply": "Reply",
            "hints": ["Hint 1", "Hint 2"]
        })

class MockJSONStreamProvider(FakeLLMProvider):
    def stream_complete(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        assert "reply" in system_prompt
        chunks = ['{"re', 'ply": "Hello", ', '"hints": ["H1"]}']
        for c in chunks:
            yield c

def test_conversation_agent_reply_stream():
    agent = ConversationAgent(MockJSONStreamProvider())
    generator = agent.reply_stream("Topic", "Obj", "Level", "Goal", [])
    
    chunks = []
    for item in generator:
        if isinstance(item, str):
            chunks.append(item)
        elif isinstance(item, list):
            hints = item
            
    assert "".join(chunks) == "Hello"
    assert hints == ["H1"]

class MockJSONConversationProvider(FakeLLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps({
            "reply": "Mock reply.",
            "hints": ["Hint 1", "Hint 2"]
        })

def test_conversation_agent_returns_dict():
    agent = ConversationAgent(MockJSONConversationProvider())
    result = agent.reply("Topic", "Obj", "Level", "Goal", [])
    assert isinstance(result, dict)
    assert result["reply"] == "Mock reply."
    assert len(result["hints"]) == 2
    assert result["hints"][0] == "Hint 1"


def test_dynamic_conversation_prompt():
    llm = MockChatProvider()
    agent = ConversationAgent(llm)
    
    # We pass 10 turns. We expect it not to strictly hard-truncate at 6 inside the agent blindly, 
    # or at least use the context properly.
    turns = [{"speaker": "user", "text": f"T{i}"} for i in range(10)]
    
    agent.reply(
        topic="Interviews", 
        objective="Practice answering.",
        user_level="Beginner",
        learning_goal="Job hunt",
        conversation=turns
    )
    
    assert "Beginner" in llm.last_system
    assert "Job hunt" in llm.last_system
    assert "Interviews" in llm.last_user
    assert "Practice answering." in llm.last_user


def test_conversation_prompt_uses_chinese_role_contract_and_prevents_user_substitution():
    llm = MockChatProvider()
    agent = ConversationAgent(llm)

    agent.reply(
        topic="Airport Security",
        objective="Practice giving short explanations and following instructions from security staff.",
        user_level="Beginner",
        learning_goal="Travel English",
        conversation=[
            {
                "speaker": "assistant",
                "text": "Today we will practice: Airport Security. You are at security and must explain what items you have.",
            },
            {"speaker": "user", "text": "So let's talk"},
        ],
    )

    assert "角色契约" in llm.last_system
    assert "你只扮演 NPC" in llm.last_system
    assert "用户是学习者" in llm.last_system
    assert "禁止替用户回答" in llm.last_system
    assert "不要说 I have、my bag、my passport" in llm.last_system
    assert "隐藏教学目标" in llm.last_user
    assert "Learner:" in llm.last_user
    assert "assistant:" not in llm.last_user
    assert "user:" not in llm.last_user
    assert "Today we will practice" not in llm.last_user


def test_conversation_prompt_defines_npc_role_boundary_in_chinese():
    llm = MockChatProvider()
    agent = ConversationAgent(llm)

    agent.reply(
        topic="Airport Security",
        objective="Practice explaining carried items and following security instructions.",
        user_level="Beginner",
        learning_goal="Travel English",
        conversation=[{"speaker": "user", "text": "So let's talk"}],
    )

    assert "角色边界" in llm.last_system
    assert "你只能扮演 NPC" in llm.last_system
    assert "不得替用户回答" in llm.last_system
    assert "用户是学习者" in llm.last_system
    assert "NPC 台词" in llm.last_system
    assert "隐藏练习目标" in llm.last_user
    assert "不要把目标复述给用户" in llm.last_user
