import { useEffect, useRef, useState } from "react";
import { PageHeader } from "./ui";
import { getAppVersion, getSelectedVoice, getTTSVoices, setSelectedVoice, playTTS, stopActiveAudio } from "../api";
import type { TTSVoice } from "../api";
import { APP_VERSION_CODE, APP_VERSION_NAME } from "../appVersion";

export function SettingsPage({ onLogout }: { onLogout: () => void }) {
  const [updateStatus, setUpdateStatus] = useState("");

  const checkForUpdate = async () => {
    setUpdateStatus("检查中…");
    try {
      const info = await getAppVersion();
      if (info.version_code > APP_VERSION_CODE) {
        setUpdateStatus(`发现新版本 v${info.version_name}，正在打开下载页…`);
        try {
          const { Browser } = await import("@capacitor/browser");
          await Browser.open({ url: info.apk_url });
        } catch {
          window.open(info.apk_url, "_blank");
        }
      } else {
        setUpdateStatus(`已是最新版本 v${APP_VERSION_NAME}`);
      }
    } catch {
      setUpdateStatus("检查更新失败，请稍后再试");
    }
  };
  const [bilingualEnabled, setBilingualEnabled] = useState(
    () => localStorage.getItem("speakmate-bilingual") !== "off"
  );
  const [voices, setVoices] = useState<TTSVoice[]>([]);
  const [defaultVoice, setDefaultVoice] = useState("");
  const [selectedVoice, setSelected] = useState<string | null>(() => getSelectedVoice());
  const [voiceError, setVoiceError] = useState("");
  const [voicesOpen, setVoicesOpen] = useState(false);
  const [previewVoice, setPreviewVoice] = useState<string | null>(null);
  const previewRequest = useRef(0);
  useEffect(() => () => { previewRequest.current++; stopActiveAudio(); }, []);

  useEffect(() => {
    getTTSVoices()
      .then((result) => {
        setVoices(result.voices);
        setDefaultVoice(result.default_voice);
        // 未手动选择过音色时，以当前默认音色为选中项
        setSelected((current) => current || result.default_voice);
      })
      .catch(() => setVoiceError("音色列表加载失败，请确认后端已启动。"));
  }, []);

  function toggleBilingual() {
    const next = !bilingualEnabled;
    setBilingualEnabled(next);
    localStorage.setItem("speakmate-bilingual", next ? "on" : "off");
  }

  async function chooseVoice(voice: TTSVoice) {
    setSelected(voice.id);
    setSelectedVoice(voice.id);
    setVoiceError("");
    const request = ++previewRequest.current;
    setPreviewVoice(voice.id);
    try { await playTTS(`Hello, I am ${voice.name}.`, voice.id); }
    catch { if (request === previewRequest.current) setVoiceError("试听失败，请再次点击音色重试。"); }
    finally { if (request === previewRequest.current) setPreviewVoice(null); }
  }

  return (
    <main className="page">
      <PageHeader
        eyebrow="设置"
        title="设置"
        description="显示与朗读偏好、陪练老师音色，以及其他个性化选项。"
      />

      <section className="profile-layout settings-layout">
        <div className="profile-column profile-column-aside">
          <section className="profile-card" aria-label="设置">
            <div className="profile-card-header">
              <p className="section-label">设置</p>
              <h2>显示与朗读</h2>
            </div>
            <div className="profile-setting-row">
              <div>
                <strong>双语展示</strong>
                <span>对话中显示中文翻译</span>
              </div>
              <button
                className={bilingualEnabled ? "bilingual-toggle bilingual-toggle-active" : "bilingual-toggle"}
                type="button"
                aria-pressed={bilingualEnabled}
                onClick={toggleBilingual}
              >
                {bilingualEnabled ? "开" : "关"}
              </button>
            </div>
          </section>

          <section className="profile-card" aria-label="陪练老师">
            <div className="profile-card-header">
              <p className="section-label">陪练老师</p>
              <h2>音色</h2>
            </div>
            <button type="button" className="voice-picker-toggle" aria-expanded={voicesOpen} aria-controls="voice-options" onClick={() => setVoicesOpen(value => !value)}>
              <span>当前音色：{voices.find(voice => voice.id === selectedVoice)?.name ?? "加载中…"}</span>
              <span>{voicesOpen ? "收起音色 ▴" : "选择音色 ▾"}</span>
            </button>
            {voicesOpen ? <p className="muted">点击音色试听自我介绍，并设为陪练声音。</p> : null}
            {previewVoice ? <p className="muted" role="status">正在试听 {voices.find(voice => voice.id === previewVoice)?.name}…</p> : null}
            {voiceError ? <p className="voice-error">{voiceError}</p> : null}
            {voicesOpen && voices.length > 0 ? (
              <div id="voice-options" className="voice-option-grid" role="radiogroup" aria-label="陪练老师音色">
                {voices.map((voice) => (
                  <button
                    key={voice.id}
                    type="button"
                    role="radio"
                    aria-checked={selectedVoice === voice.id}
                    className={selectedVoice === voice.id ? "voice-option voice-option-active" : "voice-option"}
                    onClick={() => void chooseVoice(voice)}
                  >
                    <span className="voice-option-name">
                      {voice.name}
                      {voice.default && voice.id === defaultVoice ? <em className="voice-option-default">默认</em> : null}
                    </span>
                    <span className="voice-option-meta">{voice.gender} · {voice.accent} · {voice.description}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </section>

          <section className="profile-card" aria-label="账号">
            <h2>账号</h2>
            <button type="button" className="settings-logout-button" onClick={onLogout}>退出登录</button>
          </section>
          <section className="profile-card" aria-label="关于">
            <div className="profile-card-header">
              <p className="section-label">关于</p>
              <h2>SpeakMate</h2>
            </div>
            <p className="muted">场景口语陪练 · 按场景对话、实时语法纠错、难度随水平自适应。</p>
            <p className="muted">当前版本 v{APP_VERSION_NAME}</p>
            <div className="settings-update-row">
              <button type="button" className="settings-logout-button" onClick={() => void checkForUpdate()}>
                检查更新
              </button>
              {updateStatus ? <span className="muted settings-update-status">{updateStatus}</span> : null}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
