# DEPLOY — 部署文档

项目:SpeakMate 英语口语陪练 AI Agent(提交版 v2)

## 1. 环境要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | ≥ 3.11 | 后端运行环境 |
| 外网 | 可用 | 调用 LLM API(OpenRouter/DeepSeek);不配置则运行内置 fake 演示模式 |
| Node.js | ≥ 18(可选) | 仅重新构建前端时需要;本提交版已预编译 `app/frontend/dist` |

语音识别模型(sherpa-onnx whisper-tiny.en,约 100MB,3 个文件)需自行下载(见 3.3 节);未下载时仅语音功能不可用,打字对话、纠错、报告等功能不受影响。

## 2. 快速部署(单端口,推荐)

```bash
# 1. 进入源项目根目录(完整代码在此)
cd "speaking practice 提交版"

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量(可选)
cp .env.example .env     # Windows: copy .env.example .env

# 4. 启动(必须在 app/backend 目录下)
cd app/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动成功后浏览器打开 **http://localhost:8000**(页面与 API 同端口)。

> 提交版 v2 的「测试用例 + 测试结果」「数据文件 + 清洗说明」为资料目录,不参与运行;运行时只需源项目的 `app/`、`requirements.txt`、`.env.example`。

## 3. 配置说明

复制 `.env.example` 为 `.env` 后按需修改(**真实密钥只放 .env,不随提交包分发**):

| 变量 | 默认 | 说明 |
|------|------|------|
| `COACH_DB_PATH` | `./data/coach.sqlite` | SQLite 路径(相对启动目录),首次启动自动建库建表 |
| `LLM_PROVIDER` | `fake` | `openrouter` / `deepseek` / `fake`(fake 为无 Key 演示模式) |
| `LLM_API_KEY` | 空 | LLM API 密钥 |
| `LLM_BASE_URL` | 空 | 如 `https://openrouter.ai/api/v1` |
| `PLANNER_MODEL` | `fake-local-coach` | 计划/复盘/记忆类 Agent 使用的模型 |
| `CHAT_MODEL` | `fake-local-coach` | 对话/纠错类 Agent 使用的模型 |
| `TTS_VOICE` | `en-US-JennyNeural` | 默认陪练音色(可在设置页切换) |

### 3.1 下载语音识别模型(可选,启用语音对话)

```powershell
cd data
mkdir asr_model\sherpa-onnx-whisper-tiny.en
cd asr_model\sherpa-onnx-whisper-tiny.en
curl -L -O https://hf-mirror.com/csukuangfj/sherpa-onnx-whisper-tiny.en/resolve/main/tiny.en-encoder.int8.onnx
curl -L -O https://hf-mirror.com/csukuangfj/sherpa-onnx-whisper-tiny.en/resolve/main/tiny.en-decoder.int8.onnx
curl -L -O https://hf-mirror.com/csukuangfj/sherpa-onnx-whisper-tiny.en/resolve/main/tiny.en-tokens.txt
```

国内推荐 hf-mirror 镜像;GitHub 官方源兜底:`https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-tiny.en.tar.bz2`(解压后整体放入 `data/asr_model/`)。

验证目录结构:

```
data/asr_model/sherpa-onnx-whisper-tiny.en/
  ├── tiny.en-encoder.int8.onnx
  ├── tiny.en-decoder.int8.onnx
  └── tiny.en-tokens.txt
```

启动日志出现 `ASR 模型就绪` 即生效。

## 4. 开发模式(前后端分离)

```bash
# 终端 1:后端(8000)
cd app/backend && python -m uvicorn app.main:app --reload --port 8000

# 终端 2:前端(5173,已配置 CORS 允许)
cd app/frontend && npm install && npm run dev
```

前端默认请求 `http://localhost:8000`(见 `src/api.ts` 的 `API_BASE`),可用 `VITE_API_BASE` 环境变量覆盖。

## 5. 重新构建前端(可选)

```bash
cd app/frontend
npm install
npm run build        # 产物输出到 dist/,单端口模式自动生效
npm test             # 前端 vitest 用例
```

## 6. 运行测试

```bash
cd app/backend
python -m pytest                 # 后端 126 个用例
python e2e_simulation.py         # 端到端全流程模拟(真实后端 + 学生 LLM)
```

最新测试结果见「测试用例 + 测试结果 / 测试结果」。

## 7. 访问地址

| 地址 | 内容 |
|------|------|
| http://localhost:8000 | 应用主界面(登录 / 游客体验) |
| http://localhost:8000/docs | API 文档(Swagger,14 组路由) |

测试账号:支持游客直接体验(登录页点"游客"进入),也可注册手机号账号。

## 8. 核心功能演示路径

1. **首次引导**:登录后填写学习目标 / 每天时长 / 当前水平,生成分阶段学习计划
2. **场景练习**:在"今日练习"或场景库选择场景,点击卡片开始对话
3. **实时纠错**:输入英语句子 → 右侧纠错面板列出同类合并后的纠错卡;消息气泡右下角出现红色「!」表示该条有错误
4. **每轮报告**:每轮对话结束自动生成该轮错误报告
5. **语音闭环**:点击麦克风说话 → 离线识别 → 教练语音回复(14 种音色)
6. **难度自适应**:正确率 ≥80% 升档,<60% 降档
7. **成长与记忆**:"成长"页查看复盘、长期记忆与针对性练习

推荐测试话术(餐厅场景):`I want to order a pizza and I am very hunger.`(故意包含主谓/拼写类错误,观察纠错与感叹号)

## 9. 常见问题

**Q1:启动报错 `ModuleNotFoundError: sherpa_onnx`?**
依赖未装全,执行 `pip install -r requirements.txt`;若 sherpa-onnx 安装失败可先启动(语音功能降级),对话功能不受影响。

**Q2:不配置 LLM Key 能跑吗?**
能。`LLM_PROVIDER=fake` 时使用内置演示逻辑,可完整体验场景对话、规则纠错、报告、记忆等流程。

**Q3:页面打开但接口 404?**
确认在 `app/backend` 目录下启动(数据库与静态路径按启动目录解析)。

**Q4:语音识别不准 / 加载慢?**
首次加载 ASR 模型需数秒;若提示模型缺失,先按 3.3 节下载(国内镜像 hf-mirror 更快)。

**Q5:数据存哪里?**
SQLite:`app/backend/data/coach.sqlite`(默认)。如需重置,删除该文件后重启即可自动重建。

## 10. 安全说明

- 提交包不含任何真实密钥:`.env` 不随包分发,仅提供 `.env.example` 模板。
- 默认 `JWT_SECRET` 为占位值,生产部署请在 `.env` 中设置强随机密钥。
- 依赖仅开源组件(FastAPI / sherpa-onnx / edge-tts 等),无第三方闭源 SDK。
