#!/usr/bin/env bash
# SpeakMate 一键部署：Ubuntu 22.04/24.04，以 root 执行
# 用法： bash deploy.sh [LLM_API_KEY]
set -euo pipefail

APP=/opt/speakmate
SVC=speakmate
KEY="${1:-}"

echo "==> 1/6 系统依赖"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx curl >/dev/null

echo "==> 2/6 运行账号"
id -u speakmate >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin speakmate
mkdir -p "$APP"
chown -R speakmate:speakmate "$APP"

echo "==> 3/6 Python 依赖"
cd "$APP"
[ -d .venv ] || sudo -u speakmate python3 -m venv .venv
sudo -u speakmate .venv/bin/pip install -q -U pip
sudo -u speakmate .venv/bin/pip install -q fastapi "uvicorn[standard]" python-multipart pydantic python-dotenv edge-tts PyJWT bcrypt numpy langchain-core
# 语音识别依赖：体积较大，装失败只影响语音，文字功能不受影响
sudo -u speakmate .venv/bin/pip install -q sherpa-onnx miniaudio \
  || echo "    ⚠ sherpa-onnx 安装失败，语音识别不可用，其余功能正常"

echo "==> 4/6 生成 .env"
if [ ! -f "$APP/.env" ]; then
  cat > "$APP/.env" <<EOF
COACH_DB_PATH=$APP/app/backend/data/coach.sqlite
LLM_PROVIDER=deepseek
LLM_API_KEY=$KEY
LLM_BASE_URL=https://api.deepseek.com
PLANNER_MODEL=deepseek-reasoner
CHAT_MODEL=deepseek-chat
JWT_SECRET=$(openssl rand -hex 32)
JWT_EXPIRE_HOURS=24
ACCESS_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-16)
EOF
  chown speakmate:speakmate "$APP/.env"
  chmod 600 "$APP/.env"
  echo "    ★ 站点口令: $(grep ACCESS_PASSWORD "$APP/.env" | cut -d= -f2)"
else
  echo "    .env 已存在，保留不覆盖"
fi

echo "==> 5/6 systemd 常驻"
cat > /etc/systemd/system/$SVC.service <<EOF
[Unit]
Description=SpeakMate
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=speakmate
Group=speakmate
WorkingDirectory=$APP/app/backend
EnvironmentFile=$APP/.env
ExecStart=$APP/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SVC

[Install]
WantedBy=multi-user.target
EOF

mkdir -p "$APP/app/backend/data"
chown -R speakmate:speakmate "$APP/app/backend/data"
systemctl daemon-reload
systemctl enable --now $SVC

echo "==> 6/6 Nginx 反代"
cat > /etc/nginx/sites-available/$SVC <<'EOF'
server {
    listen 80;
    client_max_body_size 25m;
    server_tokens off;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host            $host;
        proxy_set_header X-Real-IP       $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}
EOF
ln -sf /etc/nginx/sites-available/$SVC /etc/nginx/sites-enabled/$SVC
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

sleep 3
echo "==> 健康检查"
curl -s http://127.0.0.1:8000/api/health && echo

echo "==> 语音模型检查"
if find "$APP/data/asr_model" -name '*.onnx' -print -quit 2>/dev/null | grep -q .; then
  echo "    已找到 ASR 模型，语音识别可用"
else
  echo "    ⚠ 未找到 ASR 模型，语音识别暂不可用。把模型传上来后重启即可："
  echo "      scp -r 本地/data/asr_model/sherpa-onnx-whisper-tiny root@本机:$APP/data/asr_model/"
  echo "      chown -R speakmate:speakmate $APP/data/asr_model && systemctl restart $SVC"
fi

echo
echo "部署完成。浏览器打开 http://$(curl -s -4 ifconfig.me || echo 服务器IP)/"
echo "页面空白说明前端产物缺失：ls $APP/app/frontend/dist/index.html"
