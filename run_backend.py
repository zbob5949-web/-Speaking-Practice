"""PyCharm 一键启动后端（右键 → Run 'run_backend'）。

等价的命令行是：
    cd app/backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

之所以需要这个文件：后端没有 ``if __name__ == "__main__"`` 入口，
且 ``app`` 这个包必须从 ``app/backend`` 目录下才能被导入，
直接在 PyCharm 里 Run ``app/main.py`` 会因为工作目录不对而报
``ModuleNotFoundError: No module named 'app'``。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "app" / "backend"

# 让 `import app.xxx` 能解析到 app/backend/app
sys.path.insert(0, str(BACKEND))
# 数据与相对路径都以 app/backend 为基准（和线上启动方式保持一致）
os.chdir(BACKEND)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(BACKEND / "app")],
    )


if __name__ == "__main__":
    main()
