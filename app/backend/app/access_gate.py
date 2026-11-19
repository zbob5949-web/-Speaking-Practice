"""站点访问口令门禁（可选开启）。

用途：把整个站点（前端页面 + 全部 /api/*）挡在一个口令页后面，防止公网链接
被陌生人拿到后直接消耗 LLM API 额度。

设计要点：
- 口令由环境变量 ACCESS_PASSWORD 配置；**未配置时门禁完全关闭**，
  不影响本地开发、pytest 与既有部署（对现有行为零侵入）。
- 校验通过后下发 HttpOnly Cookie（值为 HMAC 签名令牌，不含口令明文），
  后续请求凭 Cookie 放行。**前端无需任何改动**：浏览器会自动带上 Cookie，
  与前端已有的 Authorization: Bearer JWT 互不干扰。
- 刻意不使用 HTTP Basic Auth：前端已占用 Authorization 头传 JWT，两者会冲突。
- 口令错误按 IP 计数限速，防暴力猜解。
- 修改 ACCESS_PASSWORD 或 JWT_SECRET 后，旧 Cookie 立即全部失效
  （令牌由二者的 HMAC 派生）。
"""
import hashlib
import hmac
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

# 登出端点直接放行（由 handle_gate_request 处理）。
# 注意不要包含 "/_gate"：POST 由 handle_gate_request 拦截，
# GET 需落到下方 render_login_page()，若在此放行会变成 404。
GATE_PATHS = {"/_gate/logout"}

# 免口令路径：健康检查（不含敏感信息，便于存活探测 / uptime 监控）
GATE_EXEMPT_PATHS = {"/api/health"}

# 暴力猜解防护：10 分钟内同一 IP 最多 10 次口令错误，超限锁定 10 分钟
_FAIL_WINDOW = 600
_FAIL_LIMIT = 10
_failures: dict[str, list[float]] = {}

_settings_cache: dict[str, str] = {}


def _load_env() -> None:
    """读取项目根 .env（与 config.load_settings 同源，保持行为一致）。"""
    if not _settings_cache:
        project_root = Path(__file__).resolve().parents[3]
        load_dotenv(project_root / ".env", override=False)
        import os

        _settings_cache["password"] = os.getenv("ACCESS_PASSWORD", "") or ""
        _settings_cache["jwt_secret"] = (
            os.getenv("JWT_SECRET", "speakmate-jwt-secret-change-me") or ""
        )


def reload_env() -> None:
    """清空缓存以便测试或改口令后即时生效。"""
    _settings_cache.clear()
    _failures.clear()


def password() -> str:
    _load_env()
    return _settings_cache["password"]


def is_enabled() -> bool:
    """未配置 ACCESS_PASSWORD 时门禁关闭。"""
    return bool(password())


def _secret() -> bytes:
    """由 JWT_SECRET 与访问口令共同派生，任一变更即使旧令牌失效。"""
    _load_env()
    material = f"{_settings_cache['jwt_secret']}|{_settings_cache['password']}"
    return hashlib.sha256(material.encode("utf-8")).digest()


def make_token() -> str:
    """生成 Cookie 令牌（常量签名值，不含口令明文）。"""
    return hmac.new(_secret(), b"speakmate-gate:v1", hashlib.sha256).hexdigest()


def verify_token(token: str | None) -> bool:
    if not token:
        return False
    return hmac.compare_digest(token, make_token())


def client_ip(request) -> str:
    """取真实客户端 IP：优先反代头（Cloudflare Tunnel 会带 X-Forwarded-For）。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _too_many_failures(ip: str) -> int | None:
    """超限返回需等待秒数，否则 None。"""
    hits = [t for t in _failures.get(ip, []) if time.time() - t < _FAIL_WINDOW]
    _failures[ip] = hits
    if len(hits) >= _FAIL_LIMIT:
        return int(_FAIL_WINDOW - (time.time() - min(hits))) + 1
    return None


def record_failure(ip: str) -> None:
    _failures.setdefault(ip, []).append(time.time())


def clear_failures(ip: str) -> None:
    _failures.pop(ip, None)


def set_cookie(response: Response, request) -> None:
    """写入 HttpOnly Cookie；HTTPS 下附加 Secure。"""
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    response.set_cookie(
        key="sm_gate",
        value=make_token(),
        max_age=7 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=(scheme == "https"),
        path="/",
    )


LOGIN_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>SpeakMate · 访问验证</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Microsoft YaHei", sans-serif;
    background: linear-gradient(160deg, #f5f7fb 0%, #e8edf7 100%);
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    padding: 24px; color: #1f2937;
  }}
  .card {{
    width: 100%; max-width: 380px; background: #fff; border-radius: 18px;
    padding: 34px 28px; box-shadow: 0 12px 40px rgba(31, 41, 55, .10);
  }}
  h1 {{ font-size: 19px; font-weight: 650; margin-bottom: 6px; }}
  p.sub {{ font-size: 13px; color: #6b7280; line-height: 1.6; margin-bottom: 22px; }}
  label {{ display: block; font-size: 13px; font-weight: 550; margin-bottom: 8px; }}
  input {{
    width: 100%; padding: 12px 14px; font-size: 15px; border: 1.5px solid #e5e7eb;
    border-radius: 10px; outline: none; transition: border-color .15s;
  }}
  input:focus {{ border-color: #4f7cff; }}
  button {{
    width: 100%; margin-top: 18px; padding: 12px; font-size: 15px; font-weight: 600;
    color: #fff; background: #4f7cff; border: 0; border-radius: 10px; cursor: pointer;
    transition: background .15s;
  }}
  button:hover {{ background: #3f68e0; }}
  .err {{
    margin-top: 14px; padding: 10px 12px; font-size: 13px; line-height: 1.5;
    color: #b42318; background: #fef3f2; border: 1px solid #fecdc9; border-radius: 9px;
  }}
  .foot {{ margin-top: 20px; font-size: 12px; color: #9ca3af; text-align: center; }}
</style>
</head>
<body>
  <form class="card" method="post" action="/_gate">
    <h1>SpeakMate 口语陪练</h1>
    <p class="sub">本站为内测演示环境，请输入访问口令。</p>
    <label for="password">访问口令</label>
    <input id="password" name="password" type="password" autocomplete="current-password"
           autofocus required maxlength="128">
    <button type="submit">进入</button>
    {error_block}
    <div class="foot">口令由项目管理员提供</div>
  </form>
</body>
</html>
"""


def render_login_page(error: str | None = None) -> HTMLResponse:
    block = f'<div class="err">{error}</div>' if error else ""
    return HTMLResponse(LOGIN_PAGE.format(error_block=block), status_code=401 if error else 200)


async def handle_gate_request(request):
    """处理 /_gate 登录与 /_gate/logout 登出；非门禁路径返回 None。"""
    path = request.url.path

    if path == "/_gate/logout":
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("sm_gate", path="/")
        return response

    if path != "/_gate" or request.method != "POST":
        return None

    ip = client_ip(request)
    wait = _too_many_failures(ip)
    if wait is not None:
        return render_login_page(f"尝试次数过多，请 {wait} 秒后再试。")

    try:
        form = await request.form()
    except Exception:
        return render_login_page("请求格式有误，请重试。")

    submitted = str(form.get("password") or "")
    if hmac.compare_digest(submitted, password()):
        clear_failures(ip)
        response = RedirectResponse(url="/", status_code=303)
        set_cookie(response, request)
        return response

    record_failure(ip)
    return render_login_page("口令不正确，请重新输入。")


async def gate_middleware(request, call_next):
    """门禁中间件：未通过校验的请求一律拦在站点之外。"""
    if not is_enabled():
        return await call_next(request)

    path = request.url.path

    # CORS 预检与门禁自身端点放行
    if request.method == "OPTIONS" or path in GATE_PATHS or path in GATE_EXEMPT_PATHS:
        return await call_next(request)

    if path == "/_gate" and request.method != "POST":
        return render_login_page()

    if verify_token(request.cookies.get("sm_gate")):
        return await call_next(request)

    # 未通过：API 返回 JSON，页面返回口令页
    if path.startswith("/api"):
        return JSONResponse(
            status_code=401,
            content={"detail": "需要站点访问口令，请先在浏览器中完成验证"},
        )
    return render_login_page()
