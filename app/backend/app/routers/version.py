"""App 版本检查：供 APK 内「检查更新」使用。"""
import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

# version.json 位于 /opt/speakmate/app/version.json（backend 目录的上一级）
VERSION_FILE = Path(__file__).resolve().parents[3] / "version.json"


@router.get("/api/app/version")
def get_app_version() -> dict[str, object]:
    if VERSION_FILE.exists():
        try:
            return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version_code": 1, "version_name": "1.0", "apk_url": "", "changelog": ""}
