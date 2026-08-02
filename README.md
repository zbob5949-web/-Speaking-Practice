# SpeakMate Agent

SpeakMate Agent 是一个面向英语口语练习的本地优先 Agent 产品。它帮助用户解决“想练口语但不知道练什么”“说错了不知道哪里有问题”“缺少长期监督和反馈”的问题，用场景练习、即时纠错、自然引导和长期记忆，提供接近私人外教的定制化陪练体验。

## 产品简介

SpeakMate Agent 会根据用户的学习目标、当前水平和每日练习时长生成练习计划。每次练习前，它会准备紧凑的学习材料；练习中，它扮演真实场景里的 NPC 推动用户开口；练习后，它会沉淀复盘、长期记忆和下一次练习重点。

产品当前采用本地优先架构，学习计划、练习记录、反馈、复盘和长期记忆默认存储在本地 SQLite 中，方便快速迭代和个人使用。

## 核心能力

- **目标驱动计划**：输入学习目标、水平和时长后，自动生成分阶段口语练习路径。
- **场景口语陪练**：通过酒店、机场、购物、面试等真实任务，让用户在上下文中开口表达。
- **即时结构化反馈**：把纠错展示为“原句片段 / 建议改成 / 中文解释 / 下次直接说”，降低阅读负担。
- **自然引导练习**：不把目标表达静态堆给用户，而是在对话 guidance 中引导用户自然使用。
- **语言支援**：选中英文词句后可直接查看中文解释，不打断角色扮演。
- **长期学习闭环**：练后复盘会沉淀用户弱点、学习信号和下一次练习建议。

## Agent 系统

- **GoalAgent**：根据用户目标生成阶段化学习计划。
- **ScenarioDesignAgent**：为下一次练习生成 lesson pack 和具体场景任务单。
- **ConversationAgent**：只扮演场景 NPC，推动用户完成口语任务。
- **InlineFeedbackAgent**：输出结构化即时反馈，并忽略语音转文字带来的大小写、标点噪声。
- **LanguageSupportAgent**：提供划词解释、句子翻译和表达辅助。
- **DailyReviewAgent**：汇总当天练习，生成学习复盘。
- **MemoryAgent**：提取长期稳定的用户弱点和学习特征。
- **PlanAdaptationAgent**：根据复盘和记忆微调后续练习计划。

## 项目结构

```text
app/
  backend/   FastAPI 后端、Agent 编排、SQLite 数据访问
  frontend/  React + Vite 前端、练习页、Growth 页、Settings 页
docs/        产品设计、实施计划和架构说明
```

## 本地运行

启动后端：

```bash
cd app/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动前端：

```bash
cd app/frontend
npm install
npm run dev
```

打开终端中显示的 Vite 本地地址即可使用。

## 测试

后端测试：

```bash
cd app/backend
python -m pytest -v
```

前端测试与构建：

```bash
cd app/frontend
npm test
npm run build
```

## LLM 配置

默认实现支持本地 fake provider，便于在没有真实模型 Key 的情况下进行确定性测试。接入真实 LLM 时，可通过环境变量配置：

```bash
export LLM_PROVIDER=openrouter
export LLM_API_KEY=your_api_key
export LLM_BASE_URL=https://openrouter.ai/api/v1
export LLM_MODEL=deepseek/deepseek-chat-v3-0324:free
```

请只把真实 API Key 放在本地 `.env` 中，不要提交到 GitHub。
