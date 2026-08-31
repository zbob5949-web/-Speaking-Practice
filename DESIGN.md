# DESIGN — 设计文档

项目:SpeakMate 英语口语陪练 AI Agent(提交版 v2)

## 1. 总体架构

三层架构:React 前端 → FastAPI 后端(路由 → 服务 → Agent/引擎)→ SQLite 存储。

```
┌─────────────────────────── 前端 (React + Vite + TS) ──────────────────────────┐
│  登录/引导 → 今日/场景库 → 练习页(PracticeRoom) → 成长/我的/设置              │
│  语音录音 → 消息气泡(含纠错感叹号) → 实时纠错侧栏 → 每轮报告                   │
└───────────────┬────────────────────────────────────────────────────────────────┘
                │ HTTP / SSE (http://localhost:8000/api/*)
┌───────────────▼────────────────────────────────────────────────────────────────┐
│                            后端 (FastAPI)                                      │
│  routers/ 14 组 API ──► services/ 业务层                                        │
│     语音闭环: asr.py(离线识别) → enhanced_turn.py(增强回合) → tts.py            │
│     语法引擎: grammar_rules.py(24规则) → grammar_service.py(LLM深度分析)        │
│               → grammar_rag.py(级别知识库检索+出处) → error_aggregation.py      │
│     学习闭环: learning_loop.py(复盘→记忆→计划调整)                              │
│     Agent层:  agents.py(8个Agent) / difficulty_agent.py(难度调节)               │
│     存储:     SQLite (coach.sqlite: 用户/计划/会话/纠错/记忆/复盘)               │
└────────────────────────────────────────────────────────────────────────────────┘
```

## 2. 模块划分

### 2.1 后端(`app/backend/app/`)

| 模块 | 职责 |
|------|------|
| `main.py` | 应用入口:挂载中间件、14 组路由、前端静态资源(单端口发布) |
| `routers/` | 14 组 API:auth / profiles / today / scenarios / sessions / reviews / voice / asr / tts / translate / favorites / language_support / prompts / health |
| `services/` | 业务层:sessions(回合/计划)、enhanced_turn(增强回合 + 每轮报告)、learning_loop(学习闭环)、voice、translate、profiles、auth_service |
| `agents.py` | 8 个 LLM Agent:GoalAgent(目标→计划)、CoachOrchestratorAgent(教练编排)、ConversationAgent(场景对话)、InlineFeedbackAgent(行内反馈)、LanguageSupportAgent(母语支持)、DailyReviewAgent(每日复盘)、MemoryAgent(长期记忆)、PlanAdaptationAgent(计划调整)、ScenarioDesignAgent(场景设计) |
| `grammar_rules.py` | 24 条确定性语法规则 + 正则匹配实现 |
| `grammar_service.py` | 纠错主流程:规则匹配 → LLM 深度分析 → 去重合并 |
| `grammar_rag.py` | 分级语法知识库(24 条)+ level-aware 检索器(可替换为向量库) |
| `error_aggregation.py` | 同类错误合并、按频率/严重度排序 |
| `difficulty_agent.py` | 动态难度调节(≥0.8 升档 / <0.6 降档) |
| `asr.py` / `tts.py` / `tts_voices.py` | 离线语音识别(sherpa-onnx)与语音合成(edge-tts,14 音色) |
| `scenarios.py` | 6 个场景 + DifficultyBand 难度分级数据 |
| `db.py` / `repositories.py` | SQLite 初始化与数据访问层 |
| `models.py` / `contracts.py` | Pydantic 模型与契约 |
| `security.py` | JWT 签发/校验、密码哈希、鉴权依赖 |

### 2.2 前端(`app/frontend/src/`)

| 模块 | 职责 |
|------|------|
| `App.tsx` / `main.tsx` | 应用入口与路由 |
| `api.ts` | API 客户端(含 SSE 流式解析) |
| `components/PracticeRoom.tsx` | 核心练习页:对话、实时纠错侧栏、每轮报告卡片 |
| `components/LoginPage.tsx` / `Onboarding.tsx` | 登录/游客 + 首次引导 |
| `components/PlanPage.tsx` / `ScenarioPicker.tsx` | 学习计划与场景选择 |
| `components/GrowthPage.tsx` / `ProfilePage.tsx` / `SettingsPage.tsx` | 成长报告 / 个人信息 / 设置(音色切换等) |
| `components/VoiceRecorder.tsx` | 语音录制 |
| `types.ts` | 共享类型定义(含 ErrorReport) |

## 3. 关键流程设计

### 3.1 语法纠错流水线(先规则后 LLM)

```
学员输入句子
   │
   ▼
grammar_rules.py  (24 条确定性规则,正则匹配,离线可用)
   │  命中 → 生成规则纠错卡片(confidence≈0.94)
   ▼
grammar_service.py (LLM 深度分析:语义级错误、规则漏网之鱼)
   │
   ▼
grammar_rag.py (按学员 level + rule_id 检索知识条目,附规则出处)
   │
   ▼
error_aggregation.py (同类合并、按频率/严重度排序)
   │
   ▼
输出纠错卡片 + 每轮错误报告
```

### 3.2 学习闭环(长期记忆)

```
每轮对话 → 正确率统计 → DailyReviewAgent 复盘
        → MemoryAgent 提取常犯错误类型(长期记忆)
        → PlanAdaptationAgent 调整学习计划
        → 生成针对性练习(下一轮)
```

### 3.3 语音闭环

```
麦克风录音 → VoiceRecorder → /api/voice/turn
  → asr.py(sherpa-onnx 离线识别)
  → enhanced_turn.py(纠错 + 场景对话)
  → tts.py(edge-tts 合成语音,14 种音色可选)
  → 前端播放语音回复
```

### 3.4 难度自适应

动态难度调节子 Agent 依据最近正确率:≥80% 升一档、<60% 降一档;升/降档时同步调整 `vocabulary_range` 与 `sentence_complexity`(来自场景的 DifficultyBand)。

## 4. 数据设计(SQLite)

主要表(首次启动自动创建,`coach.sqlite`):

| 表 | 内容 |
|----|------|
| `users` / `profiles` | 用户与学习档案(目标、时长、水平) |
| `plans` / `plan_days` | 分阶段学习计划 |
| `sessions` / `messages` | 练习会话与消息 |
| `feedback` / `session_feedback` | 纠错反馈与每轮/会话级报告 |
| `memories` / `reviews` | 长期记忆与每日复盘 |
| `adjustments` | 计划调整记录 |

数据文件的结构化导出(JSON/CSV)见「数据文件 + 清洗说明」文件夹。

## 5. 接口设计(部分)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` / `/api/auth/login` | 注册/登录(JWT) |
| POST | `/api/profiles/onboarding` | 首次引导 |
| GET | `/api/scenarios` | 场景列表 |
| POST | `/api/sessions/turn` | 文字对话回合(SSE 流式) |
| POST | `/api/voice/turn` | 语音回合(ASR + 对话 + TTS) |
| GET | `/api/sessions/{id}/learning-report` | 会话学习报告 |
| GET | `/api/growth/summary` | 成长总览(复盘/记忆/调整) |
| GET | `/docs` | Swagger 在线 API 文档 |

## 6. 安全设计

- JWT 无状态鉴权,密码 bcrypt 哈希;`security.py` 提供依赖注入。
- 游客模式限流(60 请求/分钟),防滥用。
- 密钥仅存 `.env`(不入库、不入提交包),提供 `.env.example` 模板。
- SQLite 数据默认本地存储,无第三方闭源 SDK。
