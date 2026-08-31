# SpeakMate — 英语口语陪练 AI Agent(提交版 v2)

SpeakMate 是一个面向英语口语练习的 AI 陪练 Agent:按场景对话、实时语法纠错、难度随水平自适应。使用本地优先架构(SQLite + 离线语音识别),内置 6 个手工场景、24 条语法规则、RAG 语法知识库与 8 个 Agent。

> 本目录为**课程/比赛提交版 v2**,按提交要求组织:除完整可运行项目外,额外提供「测试用例 + 测试结果」「数据文件 + 清洗说明」两个资料文件夹与 8 个说明文档。

## 功能速览

- **场景口语陪练**:机场、酒店、餐厅、面试、就医、购物 6 个场景,每个含背景设定、NPC 角色与难度分级(按词汇量与句型复杂度分 A1–C1 五档)
- **实时语法纠错**:24 条确定性规则(主谓一致、时态搭配等)先匹配 → LLM 深度分析 → RAG 检索对应级别语法知识并给出规则出处 → 同类错误合并、按频率排序
- **每轮错误报告**:每轮对话结束输出该轮错误汇总,可查会话级学习报告
- **难度自适应**:动态难度调节子 Agent 按答题正确率(≥80% 升档 / <60% 降档)调整词汇与句型
- **长期记忆**:追踪常犯错误类型,生成针对性练习,学习闭环自动复盘与调整计划
- **语音闭环**:录音 → 离线 ASR 识别 → 纠错 → TTS 语音回复(14 种陪练音色)

## 技术栈

- 后端:FastAPI + SQLite + sherpa-onnx(离线 ASR)+ edge-tts(TTS)+ 多 Agent 编排
- 前端:React 18 + Vite + TypeScript(已预编译至 `app/frontend/dist`)

## 目录结构

```
speaking practice 提交版v2/
├── 📁 测试用例 + 测试结果/
│   ├── backend_tests/            后端 pytest 测试用例(14 个测试文件)
│   ├── frontend_App.test.tsx     前端 vitest 测试用例
│   └── 测试结果/
│       ├── backend_pytest_results.xml   后端测试结果(JUnit XML)
│       └── frontend_vitest_results.json 前端测试结果(vitest JSON)
├── 📁 数据文件 + 清洗说明/
│   ├── scenarios.json / .csv            6 场景 × 5 难度档数据
│   ├── grammar_rules.json / .csv        24 条语法纠错规则
│   ├── grammar_knowledge_rag.json/.csv  RAG 语法知识库 24 条
│   └── 数据清洗说明.md                   数据来源、清洗过程与字段说明
├── 📄 .env.example             环境变量配置示例
├── 📄 README.md                项目说明(本文档)
├── 📄 REQUIREMENTS.md          需求文档
├── 📄 DESIGN.md                设计文档
├── 📄 ANALYSIS.md              分析文档
├── 📄 DEPLOY.md                部署文档
└── 📄 SUMMARY.md               总结文档
```

> 完整可运行代码(后端 `app/backend` + 前端 `app/frontend` 及预编译产物)见源项目 `C:\Users\却绫\Desktop\speaking practice 提交版`,本提交版为其规范化整理版。

## 快速启动(详见 DEPLOY.md)

```bash
pip install -r requirements.txt
cp .env.example .env        # 填入 LLM API Key(可留空,运行内置演示模式)
cd app/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 **http://localhost:8000** 即可使用(页面与 API 同端口)。

## 测试

```bash
cd app/backend && python -m pytest          # 后端 126 个用例
cd app/frontend && npm install && npm test  # 前端 vitest 用例
```

测试用例与最新测试结果见「测试用例 + 测试结果」文件夹。

## 测试账号

支持**游客直接进入**(首页点击"游客体验"),也可注册手机号账号使用。

## 文档导航

| 文档 | 内容 |
|------|------|
| [REQUIREMENTS.md](REQUIREMENTS.md) | 项目需求(功能/非功能需求、验收标准) |
| [DESIGN.md](DESIGN.md) | 系统设计(架构、模块划分、数据设计) |
| [ANALYSIS.md](ANALYSIS.md) | 分析文档(技术选型、方案权衡、需求覆盖分析) |
| [DEPLOY.md](DEPLOY.md) | 部署文档(环境、安装、启动、常见问题) |
| [SUMMARY.md](SUMMARY.md) | 总结文档(成果、指标、创新点、反思) |
