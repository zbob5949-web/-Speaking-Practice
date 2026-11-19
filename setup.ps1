# SpeakMate 队友一键环境配置（Windows PowerShell）
# 用法：右键本文件 → “使用 PowerShell 运行”，或在项目根目录执行：
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$PIP_MIRROR  = "https://pypi.tuna.tsinghua.edu.cn/simple"
$SHERPA_VER  = "1.13.4"
$HF_BASE     = "https://hf-mirror.com/csukuangfj/sherpa-onnx-whisper-tiny.en/resolve/main"
$MODEL_DIR   = Join-Path $Root "data\asr_model\sherpa-onnx-whisper-tiny.en"

function Step($n, $t) { Write-Host "`n[$n/5] $t" -ForegroundColor Cyan }
function OK($m)   { Write-Host "      OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "      !!  $m" -ForegroundColor Yellow }

Write-Host "=============================================="
Write-Host "   SpeakMate 一键环境配置"
Write-Host "=============================================="

# ---------- 1. 检查 Python ----------
Step 1 "检查 Python 版本（需 3.11+）"
$ErrorActionPreference = "Continue"
$pyVer = & python -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null
$ErrorActionPreference = "Stop"
if (-not $pyVer) {
    throw "未找到 python。请安装 Python 3.11+（安装时勾选 Add python.exe to PATH），重开终端后重试。"
}
$major, $minor = $pyVer.Split(".")
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 11)) {
    throw "当前 Python 版本是 $pyVer，需要 3.11 或更高。"
}
OK "Python $pyVer"

# ---------- 2. 创建虚拟环境 ----------
Step 2 "创建虚拟环境 .venv"
if (Test-Path ".venv\Scripts\python.exe") {
    OK ".venv 已存在，复用"
} else {
    & python -m venv .venv
    if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "虚拟环境创建失败" }
    OK ".venv 创建完成"
}
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"

# ---------- 3. 安装依赖（清华镜像加速） ----------
Step 3 "安装 Python 依赖（走清华镜像加速）"
& $venvPy -m pip install --upgrade pip -i $PIP_MIRROR --quiet
# 显式钉住 sherpa-onnx 版本：最新 2.x 与本项目 1.13 的 API 不兼容
& $venvPy -m pip install -r requirements.txt "sherpa-onnx==$SHERPA_VER" -i $PIP_MIRROR
if ($LASTEXITCODE -ne 0) { throw "依赖安装失败，请检查网络后重试" }
OK "依赖安装完成（sherpa-onnx 固定为 $SHERPA_VER）"

# ---------- 4. 生成 .env ----------
Step 4 "生成 .env 配置"
if (Test-Path ".env") {
    OK ".env 已存在，保留你原有的配置"
} else {
    Copy-Item ".env.example" ".env"
    Warn "已从 .env.example 生成 .env —— 不填 API Key 也能跑（内置演示模式）"
    Warn "要启用真实对话，用记事本打开 .env 填入 LLM_API_KEY"
}

# ---------- 5. 下载离线语音识别模型 ----------
Step 5 "下载离线 ASR 模型（约 100MB，hf-mirror 国内镜像）"
if (-not (Test-Path $MODEL_DIR)) { New-Item -ItemType Directory -Path $MODEL_DIR -Force | Out-Null }

$files = @(
    @{ name = "tiny.en-encoder.int8.onnx";  size = 12937772 },
    @{ name = "tiny.en-decoder.int8.onnx";  size = 89853865 },
    @{ name = "tiny.en-tokens.txt";         size = 835554   }
)
foreach ($f in $files) {
    $dest = Join-Path $MODEL_DIR $f.name
    $have = 0
    if (Test-Path $dest) { $have = (Get-Item $dest).Length }
    if ($have -eq $f.size) { OK "$($f.name) 已存在，跳过"; continue }
    Write-Host "      下载 $($f.name) ..." -ForegroundColor Gray
    # -C - 断点续传，网络中断可重复运行本脚本继续
    & curl.exe -L --fail --retry 3 --retry-delay 2 -C - -o "$dest" "$HF_BASE/$($f.name)"
    if ($LASTEXITCODE -ne 0) {
        Warn "下载 $($f.name) 失败 —— 语音功能将不可用，打字对话不受影响"
        Warn "可重跑本脚本续传，或手动从 $HF_BASE 下载"
    } elseif ((Get-Item $dest).Length -ne $f.size) {
        Warn "$($f.name) 大小不符，请重跑本脚本续传"
    } else {
        OK "$($f.name)"
    }
}

# ---------- 完成 ----------
Write-Host "`n==============================================" -ForegroundColor Green
Write-Host "   配置完成！启动命令：" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "   .\.venv\Scripts\python.exe run_backend.py" -ForegroundColor White
Write-Host ""
Write-Host "   然后浏览器打开 http://localhost:8000" -ForegroundColor White
Write-Host ""
