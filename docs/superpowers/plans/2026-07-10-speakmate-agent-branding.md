# SpeakMate Agent Branding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将项目对外品牌从 AI PM English Coach / English Coach 统一为 SpeakMate Agent，并把 GitHub README 改成中文产品介绍。

**Architecture:** 本次只修改文档、包元数据、运行时可见品牌文案和对应测试断言，不触碰 Agent 核心流程、数据库结构和历史设计文档。README 作为 GitHub 产品首页，前端与后端标题作为运行时品牌入口，测试负责锁定首屏品牌展示。

**Tech Stack:** Markdown, React, Vite, FastAPI, Vitest, npm package metadata。

---

### Task 1: Frontend Visible Branding

**Files:**
- Modify: `app/frontend/src/App.test.tsx`
- Modify: `app/frontend/src/components/AppShell.tsx`
- Modify: `app/frontend/src/components/Onboarding.tsx`
- Modify: `app/frontend/index.html`

- [ ] **Step 1: Write the failing test**

```tsx
expect(await screen.findByText("SpeakMate Agent")).toBeTruthy();
expect(screen.getByText("你的场景口语陪练")).toBeTruthy();
expect(screen.getByText("Set up your SpeakMate practice plan")).toBeTruthy();
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app/frontend && npm run test -- src/App.test.tsx`
Expected: FAIL because current UI still renders `English Coach`.

- [ ] **Step 3: Write minimal implementation**

```tsx
<div className="brand-mark">SM</div>
<div className="brand-title">SpeakMate Agent</div>
<div className="brand-subtitle">你的场景口语陪练</div>
```

```tsx
<p className="hero-kicker">Personal Speaking Coach</p>
<h1>SpeakMate Agent</h1>
<h1>Set up your SpeakMate practice plan</h1>
```

```html
<title>SpeakMate Agent</title>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app/frontend && npm run test -- src/App.test.tsx`
Expected: PASS.

### Task 2: Package And Backend Branding

**Files:**
- Modify: `app/frontend/package.json`
- Modify: `app/frontend/package-lock.json`
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/app/llm.py`
- Modify: `app/backend/app/__init__.py`

- [ ] **Step 1: Update metadata and backend display names**

```json
"name": "speakmate-agent-frontend"
```

```python
app = FastAPI(title="SpeakMate Agent")
```

```python
"X-Title": "SpeakMate Agent"
```

- [ ] **Step 2: Run verification**

Run: `cd app/frontend && npm run build`
Expected: PASS.

Run: `cd app/backend && python -m pytest app/backend/tests/ -v`
Expected: PASS.

### Task 3: Chinese README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace English README with Chinese product page**

```markdown
# SpeakMate Agent

SpeakMate Agent 是一个面向英语口语练习的本地优先 Agent 产品。
```

- [ ] **Step 2: Include core sections**

```markdown
## 产品简介
## 核心能力
## Agent 系统
## 本地运行
## 测试
## LLM 配置
```

- [ ] **Step 3: Verify old public brand text is removed**

Run: `rg "AI PM English Coach|ai-pm-english-coach|English Coach|Local English Agent" README.md app/frontend/src app/frontend/index.html app/backend/app`
Expected: no matches except intentional historical test data if any remains outside public branding.
