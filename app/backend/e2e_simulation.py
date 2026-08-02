"""端到端"模拟真人"产品全功能测试程序。

做什么：
  - 启动一个真实的 uvicorn 后端进程（使用独立的临时数据库，不污染真实数据）。
  - 复用项目 .env 里的 OpenRouter 配置，所有 Agent 打真实大模型。
  - 用 httpx 走真实 HTTP，按真人使用动线依次调用全部产品端点。
  - 由一个独立的"学生 LLM"扮演学习者：读懂 NPC 上一句 + 今日材料包后，动态生成英文回复。
  - 逐项输出通过/失败、耗时与内容样例，最后给出汇总报告。

用法：
    cd app/backend
    python e2e_simulation.py                # 完整跑真实大模型
    python e2e_simulation.py --turns 4      # 指定练习对话轮数
    python e2e_simulation.py --fake         # 强制用 FakeLLMProvider（不花 token，仅验证动线）

退出码：全部通过为 0，有失败为 1。
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from contextlib import closing
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parents[1]


# --------------------------------------------------------------------------- #
# 输出与报告
# --------------------------------------------------------------------------- #
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    END = "\033[0m"


class Reporter:
    def __init__(self) -> None:
        self.results: list[dict] = []

    def record(self, name: str, ok: bool, elapsed: float, detail: str = "") -> None:
        self.results.append({"name": name, "ok": ok, "elapsed": elapsed, "detail": detail})
        icon = f"{Colors.GREEN}PASS{Colors.END}" if ok else f"{Colors.RED}FAIL{Colors.END}"
        line = f"  [{icon}] {name}  {Colors.GRAY}({elapsed:.2f}s){Colors.END}"
        print(line)
        if detail:
            snippet = detail if len(detail) < 400 else detail[:400] + " …"
            color = Colors.GRAY if ok else Colors.RED
            print(f"        {color}{snippet}{Colors.END}")

    def section(self, title: str) -> None:
        print(f"\n{Colors.BOLD}{Colors.CYAN}== {title} =={Colors.END}")

    def summary(self) -> bool:
        passed = sum(1 for r in self.results if r["ok"])
        failed = len(self.results) - passed
        total_time = sum(r["elapsed"] for r in self.results)
        print(f"\n{Colors.BOLD}==================== 汇总 ===================={Colors.END}")
        print(f"  用例总数: {len(self.results)}   "
              f"{Colors.GREEN}通过: {passed}{Colors.END}   "
              f"{Colors.RED if failed else Colors.GRAY}失败: {failed}{Colors.END}   "
              f"{Colors.GRAY}总耗时: {total_time:.1f}s{Colors.END}")
        if failed:
            print(f"\n  {Colors.RED}失败用例:{Colors.END}")
            for r in self.results:
                if not r["ok"]:
                    print(f"    - {r['name']}: {r['detail'][:200]}")
        else:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}全部功能通过 ✅{Colors.END}")
        return failed == 0


# --------------------------------------------------------------------------- #
# 学生 LLM：扮演真人学习者
# --------------------------------------------------------------------------- #
class SimulatedStudent:
    """用一个独立 LLM 扮演学习者，根据 NPC 台词和今日材料包动态生成回复。"""

    def __init__(self, use_fake: bool) -> None:
        # 延迟 import，避免污染后端进程
        sys.path.insert(0, str(BACKEND_DIR))
        from app.config import load_settings
        from app.llm import create_llm_provider, FakeLLMProvider

        if use_fake:
            self.llm = FakeLLMProvider()
            self.is_fake = True
            return

        settings = load_settings()
        self.llm = create_llm_provider(
            provider_name=settings.llm_provider,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.chat_model,
        )
        self.is_fake = isinstance(self.llm, FakeLLMProvider)

    def say(self, npc_text: str, brief: dict | None, history: list[str], goal: str) -> str:
        if self.is_fake:
            return "Could you help me understand the next step, please?"

        target_expressions = []
        for item in (brief or {}).get("target_expressions", [])[:4]:
            if isinstance(item, dict):
                target_expressions.append(item.get("expression", ""))
            elif isinstance(item, str):
                target_expressions.append(item)

        system_prompt = (
            "You are an English learner practicing speaking with an AI tutor (NPC). "
            "You are NOT a perfect speaker: you are earnest but make occasional small, "
            "natural mistakes (article/preposition/tense) like a real intermediate learner. "
            "Reply with ONE short spoken turn (1-3 sentences) that directly responds to the NPC. "
            "Try to use the target expressions naturally when relevant. "
            "Output ONLY the spoken line, no quotes, no explanations."
        )
        user_prompt = (
            f"Your learning goal: {goal}\n"
            f"Target expressions to practice: {', '.join(e for e in target_expressions if e) or 'none'}\n"
            f"Recent conversation:\n" + "\n".join(history[-6:]) + "\n\n"
            f"NPC just said: {npc_text}\n\n"
            "Your reply:"
        )
        try:
            reply = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception:
            reply = ""
        reply = (reply or "").strip().strip('"').strip()
        # reasoning 模型可能返回空 content —— 兜底一句，保证动线不断
        return reply or "Sorry, could you say that again more slowly?"


# --------------------------------------------------------------------------- #
# 后端进程管理
# --------------------------------------------------------------------------- #
def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_backend(port: int, use_fake: bool) -> tuple[subprocess.Popen, Path]:
    """启动隔离后端进程；返回 (进程, 临时 db 路径)。"""
    tmp_db = Path(tempfile.mkdtemp(prefix="e2e_coach_")) / "coach.sqlite"
    env = os.environ.copy()
    # 隔离数据库，绝不碰真实库
    env["COACH_DB_PATH"] = str(tmp_db)
    if use_fake:
        env["LLM_PROVIDER"] = "fake"
    else:
        # 显式加载项目 .env 的真实配置到子进程
        from dotenv import dotenv_values
        for k, v in dotenv_values(PROJECT_ROOT / ".env").items():
            if k != "COACH_DB_PATH" and v is not None:
                env[k] = v

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc, tmp_db


def wait_for_health(base_url: str, proc: subprocess.Popen, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            raise RuntimeError(f"后端进程提前退出:\n{out}")
        try:
            r = httpx.get(f"{base_url}/api/health", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("后端健康检查超时")


# --------------------------------------------------------------------------- #
# 端到端动线
# --------------------------------------------------------------------------- #
def run_simulation(base_url: str, student: SimulatedStudent, reporter: Reporter, n_turns: int, db_path: Path) -> None:
    client = httpx.Client(base_url=base_url, timeout=120.0)

    def step(name: str, fn):
        start = time.time()
        try:
            detail = fn()
            reporter.record(name, True, time.time() - start, detail or "")
            return True
        except Exception as e:
            tb = traceback.format_exc(limit=3)
            reporter.record(name, False, time.time() - start, f"{e}\n{tb}")
            return None

    state: dict = {}

    # --- 1. 健康检查 ---
    reporter.section("1. 基础可用性")
    step("健康检查 GET /api/health",
         lambda: _expect(client.get("/api/health"), lambda d: d["status"] == "ok" and "status=ok"))

    # --- 2. Onboarding：生成学习计划 ---
    reporter.section("2. 用户初始设计 → 生成计划")

    def do_onboarding():
        payload = {
            "learning_goal": "在跨境电商工作中用英语与海外供应商谈判和沟通",
            "total_days": 3,
            "daily_minutes": 15,
            "current_level": "Intermediate",
        }
        data = _expect(client.post("/api/onboarding", json=payload), lambda d: d)
        state["profile_id"] = data["profile"]["id"]
        state["plan"] = data["plan"]
        days = data["plan"]
        assert len(days) == 3, f"应生成 3 天计划，实际 {len(days)}"
        d0 = days[0]
        # 验证 rich plan 字段真实存在
        for key in ("skill_focus", "communicative_task", "target_functions", "success_criteria", "brief_seed"):
            assert key in d0, f"计划缺少 rich 字段 {key}"
        return (f"生成 {len(days)} 天 | Day1 topic='{d0['topic']}' "
                f"skill_focus='{d0.get('skill_focus')}' "
                f"target_functions={d0.get('target_functions')}")

    if not step("提交学习目标生成计划 POST /api/onboarding", do_onboarding):
        client.close()
        return

    step("查询当前学习状态 GET /api/current",
         lambda: _expect(client.get(f"/api/current?profile_id={state['profile_id']}"),
                         lambda d: f"计划 {len(d['plan'])} 天，profile={d['profile']['id']}"))

    step("查询所有档案 GET /api/profiles",
         lambda: _expect(client.get("/api/profiles"),
                         lambda d: f"共 {len(d['profiles'])} 个档案"))

    # --- 3. 开始练习：生成 lesson pack ---
    reporter.section("3. 开始练习 → 生成学习材料包")

    def start_practice():
        plan_day = state["plan"][0]
        data = _expect(client.post("/api/sessions/start", json={"plan_day_id": plan_day["id"]}),
                       lambda d: d)
        state["session_id"] = data["session"]["id"]
        brief = data.get("practice_brief") or {}
        state["brief"] = brief
        state["turns_text"] = [f"NPC: {t['text']}" for t in data["turns"]]
        # 验证 lesson pack 真实丰富
        n_expr = len(brief.get("target_expressions", []))
        n_steps = len(brief.get("task_steps", []))
        assert brief.get("npc_role"), "lesson pack 缺少 npc_role"
        return (f"session={state['session_id']} | npc_role='{brief.get('npc_role')}' "
                f"task_steps={n_steps} target_expressions={n_expr} "
                f"lesson_focus='{brief.get('lesson_focus')}'")

    if not step("开始练习会话 POST /api/sessions/start", start_practice):
        client.close()
        return

    # --- 4. 多轮流式对话：模拟真人 ---
    reporter.section(f"4. 模拟真人多轮对话（流式，{n_turns} 轮）")
    npc_last = state["turns_text"][-1].replace("NPC: ", "") if state["turns_text"] else "Let's begin."

    for i in range(1, n_turns + 1):
        student_line = student.say(npc_last, state.get("brief"), state["turns_text"], state["plan"][0]["objective"])

        def do_turn(line=student_line):
            reply_chunks: list[str] = []
            meta = _stream_turn(base_url, state["session_id"], line, reply_chunks)
            reply = "".join(reply_chunks).strip()
            assert reply, "NPC 流式回复为空"
            state["turns_text"].append(f"Learner: {line}")
            state["turns_text"].append(f"NPC: {reply}")
            state["_npc_last"] = reply
            state.setdefault("user_turn_ids", [])
            if meta and meta.get("user_turn"):
                state["user_turn_ids"].append(meta["user_turn"]["id"])
            fb = (meta or {}).get("inline_feedback", [])
            hints = (meta or {}).get("hints", [])
            return (f"学生: \"{line[:50]}\"\n        NPC: \"{reply[:60]}\" "
                    f"| 即时反馈 {len(fb)} 条 | 提示 {len(hints)} 条")

        step(f"第 {i} 轮对话 POST /api/sessions/turn/stream", do_turn)
        npc_last = state.get("_npc_last", npc_last)

    # --- 5. 非流式对话端点（也要覆盖） ---
    def do_sync_turn():
        line = student.say(npc_last, state.get("brief"), state["turns_text"], state["plan"][0]["objective"])
        data = _expect(client.post("/api/sessions/turn", json={"session_id": state["session_id"], "text": line}),
                       lambda d: d)
        assert data["assistant_turn"]["text"], "非流式 NPC 回复为空"
        state.setdefault("user_turn_ids", []).append(data["user_turn"]["id"])
        return f"学生: \"{line[:40]}\" | NPC 回复 {len(data['assistant_turn']['text'])} 字符"

    step("非流式对话 POST /api/sessions/turn", do_sync_turn)

    # --- 6. 语言支持：划词翻译/释义 ---
    reporter.section("5. 学习辅助功能")

    for mode, text in [("translate", "negotiate a better price"),
                       ("explain", "lead time"),
                       ("define", "wholesale"),
                       ("expression", "谈价格")]:
        step(f"语言支持[{mode}] POST /api/language-support",
             lambda m=mode, t=text: _expect(
                 client.post("/api/language-support", json={"mode": m, "text": t, "context": "跨境电商谈判"}),
                 lambda d: f"{m}: {json.dumps(d, ensure_ascii=False)[:120]}"))

    # --- 7. TTS ---
    def do_tts():
        r = client.post("/api/tts", json={"text": "Hello, let's practice negotiation."})
        assert r.status_code == 200, f"TTS 状态码 {r.status_code}"
        assert len(r.content) > 1000, f"TTS 音频过小 {len(r.content)} 字节"
        return f"生成音频 {len(r.content)} 字节 (audio/wav)"

    step("语音合成 POST /api/tts", do_tts)

    # --- 8. 编辑对话：删除一轮问答 ---
    def do_delete_pair():
        ids = state.get("user_turn_ids", [])
        if not ids:
            return "无可删除的问答对（跳过）"
        target = ids[-1]
        data = _expect(client.delete(f"/api/sessions/{state['session_id']}/turn-pairs/{target}"),
                       lambda d: d)
        return f"删除问答对 user_turn={target}，剩余 {len(data['turns'])} 条对话"

    step("删除一轮问答 DELETE /api/sessions/{id}/turn-pairs/{uid}", do_delete_pair)

    # --- 9. 每日复盘闭环：DailyReview → Memory → PlanAdaptation → 再生成 brief ---
    reporter.section("6. 每日复盘多 Agent 闭环")

    def backdate_sessions():
        # 复盘按设计只处理"过去日期"的会话；测试会话都在今天，
        # 故把本次会话的 started_at 回拨到昨天，才能真正触发复盘闭环。
        import sqlite3
        with sqlite3.connect(str(db_path)) as conn:
            n = conn.execute(
                "UPDATE daily_sessions SET started_at = datetime('now', '-1 day') "
                "WHERE id = ?", (state["session_id"],)
            ).rowcount
            conn.commit()
        return f"已将 session={state['session_id']} 回拨到昨天（影响 {n} 行），以触发到期复盘"

    step("回拨会话日期以触发复盘（测试夹具）", backdate_sessions)

    def do_daily_review():
        data = _expect(client.post("/api/daily-review/run-due"), lambda d: d)
        processed = data.get("processed_days", 0)
        assert processed >= 1, f"预期至少处理 1 天复盘，实际 {processed}（多 Agent 闭环未触发）"
        return f"处理 {processed} 天复盘 (status={data.get('status')})"

    step("触发到期复盘 POST /api/daily-review/run-due", do_daily_review)

    # --- 10. 成长总结：验证复盘产物落库 ---
    reporter.section("7. 成长中心")

    def do_growth():
        data = _expect(client.get(f"/api/growth/summary?profile_id={state['profile_id']}"), lambda d: d)
        # 真实模型下复盘应产出 review；Memory / PlanAdaptation 视模型输出而定，故只强校验 review
        if not student.is_fake:
            assert data.get("latest_review"), "复盘闭环未产出 latest_review"
        return (f"latest_review={'有' if data.get('latest_review') else '无'} | "
                f"recent_reviews={len(data.get('recent_reviews', []))} | "
                f"active_memory={len(data.get('active_memory', []))} | "
                f"active_adjustments={len(data.get('active_adjustments', []))}")

    step("成长总结 GET /api/growth/summary", do_growth)

    # --- 11. Prompt 管理：读 + 改 + 校验落库 ---
    reporter.section("8. Prompt 管理（Studio）")

    def do_prompt_rw():
        data = _expect(client.get("/api/prompts"), lambda d: d)
        prompts = data["prompts"]
        assert prompts, "prompt 列表为空"
        name = prompts[0]["name"]
        original = prompts[0]["content"]
        marker = original + "\n<!-- e2e-test-marker -->"
        r = client.put(f"/api/prompts/{name}", json={"content": marker})
        assert r.status_code == 200, f"更新 prompt 失败 {r.status_code}"
        after = _expect(client.get("/api/prompts"), lambda d: d)["prompts"]
        updated = next(p for p in after if p["name"] == name)
        assert updated["content"] == marker, "prompt 更新未落库"
        # 复原
        client.put(f"/api/prompts/{name}", json={"content": original})
        return f"读到 {len(prompts)} 个 prompt；覆盖 '{name}' 成功并已复原"

    step("Prompt 读写 GET/PUT /api/prompts", do_prompt_rw)

    # --- 12. 档案管理：删除测试档案，清理数据 ---
    reporter.section("9. 档案管理")

    def do_delete_profile():
        r = client.delete(f"/api/profiles/{state['profile_id']}")
        assert r.status_code == 200, f"删除档案失败 {r.status_code}"
        return f"删除测试档案 profile={state['profile_id']}"

    step("删除档案 DELETE /api/profiles/{id}", do_delete_profile)

    client.close()


# --------------------------------------------------------------------------- #
# 辅助
# --------------------------------------------------------------------------- #
def _expect(response: httpx.Response, extract):
    if response.status_code != 200:
        raise AssertionError(f"HTTP {response.status_code}: {response.text[:200]}")
    data = response.json()
    result = extract(data)
    if result is False:
        raise AssertionError(f"响应校验失败: {json.dumps(data, ensure_ascii=False)[:200]}")
    return result if isinstance(result, str) else data


def _stream_turn(base_url: str, session_id: int, text: str, chunks: list[str]) -> dict | None:
    """消费 SSE 流，收集文本块并返回 meta。"""
    meta: dict | None = None
    with httpx.stream("POST", f"{base_url}/api/sessions/turn/stream",
                      json={"session_id": session_id, "text": text}, timeout=120.0) as r:
        if r.status_code != 200:
            raise AssertionError(f"流式 HTTP {r.status_code}")
        buffer = ""
        for raw in r.iter_lines():
            line = raw if isinstance(raw, str) else raw.decode()
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            if data.get("type") == "text":
                chunks.append(data["content"])
            elif data.get("type") == "meta":
                meta = data
    return meta


# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description="模拟真人的产品全功能端到端测试")
    parser.add_argument("--turns", type=int, default=3, help="练习对话轮数（默认 3）")
    parser.add_argument("--fake", action="store_true", help="强制使用 FakeLLMProvider（不花 token）")
    args = parser.parse_args()

    reporter = Reporter()
    print(f"{Colors.BOLD}SpeakMate 端到端模拟真人全功能测试{Colors.END}")
    mode = "FakeLLM（离线动线）" if args.fake else "真实 OpenRouter"
    print(f"{Colors.GRAY}模式: {mode} | 练习轮数: {args.turns}{Colors.END}")

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    print(f"{Colors.GRAY}启动隔离后端 (端口 {port}, 临时数据库)…{Colors.END}")
    proc, tmp_db = start_backend(port, args.fake)

    try:
        wait_for_health(base_url, proc)
        print(f"{Colors.GREEN}后端就绪。{Colors.END}")

        student = SimulatedStudent(use_fake=args.fake)
        if not args.fake and student.is_fake:
            print(f"{Colors.YELLOW}警告: .env 未配置有效 OpenRouter，学生与后端将回退到 Fake 模式。{Colors.END}")

        run_simulation(base_url, student, reporter, args.turns, tmp_db)
    except Exception as e:
        print(f"{Colors.RED}测试运行异常: {e}{Colors.END}")
        traceback.print_exc()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        try:
            if tmp_db.exists():
                tmp_db.unlink()
        except Exception:
            pass

    ok = reporter.summary()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
