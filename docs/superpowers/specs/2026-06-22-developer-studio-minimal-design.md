# Developer Studio 最小接入设计

## 背景

当前产品已经存在一个半成品 `DeveloperStudio` 页面，内部包含 `Prompt Management` 和 `Product Flowchart` 两个子 tab。后端也已经有 `prompts` 表、`/api/prompts` 查询接口和 `/api/prompts/{name}` 更新接口。各 Agent 在运行时会通过 `repo.get_prompt(...)` 获取 Prompt，因此编辑保存后的 Prompt 可以在下一次计划生成、对话回复或反馈生成时生效。

## 目标

用最小改动把开发者调试能力接入产品页面，方便快速查看、编辑 Prompt，并用流程图理解产品页面、用户动线和后端逻辑连接。

## 范围

- 在主侧边栏增加 `Studio` 入口，复用现有 `studio` view 和 `DeveloperStudio` 组件。
- 在 `Prompt Management` tab 中列出所有 Prompt，支持选择、编辑、保存和清晰的状态反馈。
- 在 `Product Flowchart` tab 中展示覆盖主要页面、用户行为、API、Agent、数据库的 Mermaid 流程图。
- 补齐页面样式、加载状态、空状态、保存成功/失败提示和未保存变更提示。
- 后端在更新不存在的 Prompt 时返回明确错误，避免前端误判保存成功。

## 不做范围

- 不做 Prompt 版本管理、Diff、审计日志或灰度配置。
- 不做流程图自动从代码生成。
- 不做复杂权限系统。
- 不重构 Agent Prompt 架构。

## 前端设计

`AppShell` 将 `Studio` 作为一个普通导航项展示。`App.tsx` 已经支持 `studio` view，因此入口接入只需要补齐导航配置。

`DeveloperStudio` 保持两个子 tab：

- `Prompt Management`：左侧 Prompt 列表，右侧编辑器；保存按钮仅在内容变化时可用；保存中禁用按钮；保存完成后同步本地状态并显示提示。
- `Product Flowchart`：渲染一张更完整的 Mermaid 图，覆盖 Onboarding、Today、Plan、Practice、Review、Memory、Settings、Studio，以及 FastAPI、Prompt API、Agents、SQLite 的连接。

## 后端设计

保留现有 `prompts` 表作为运行时 Prompt 来源。`CoachRepository.update_prompt` 返回是否更新成功；`PUT /api/prompts/{name}` 在 Prompt 不存在时返回 404。这样前端可以区分“保存失败”和“Prompt 名不存在”。

## 数据流

Prompt 编辑链路：

用户进入 `Studio` -> 前端调用 `GET /api/prompts` -> 用户编辑内容 -> 前端调用 `PUT /api/prompts/{name}` -> 后端写入 SQLite `prompts` 表 -> 下一次 Agent 运行时通过 `repo.get_prompt(...)` 读取最新内容。

运行链路：

用户 Onboarding 生成计划 -> `GoalAgent` 使用计划 Prompt -> 用户进入 Practice -> `ConversationAgent` 和 `InlineFeedbackAgent` 使用对话与反馈 Prompt -> 练习结束进入 Review -> 结果写入记忆相关数据表。

## 测试策略

- 后端增加 Prompt API 测试：默认 Prompt 可查询，更新后再次查询能看到新内容，更新不存在 Prompt 返回 404。
- 前端增加导航测试：已有学习状态下可以从侧边栏进入 `Studio`，并看到 Prompt 管理与流程图入口。
- 运行现有前端与后端测试，确认最小接入不破坏主练习流程。
