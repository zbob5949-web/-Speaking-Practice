import { useEffect, useState } from "react";
import { PageHeader } from "./ui";
import { getSelectedVoice, getTTSVoices, setSelectedVoice } from "../api";
import type { TTSVoice } from "../api";

export function SettingsPage() {
  const [bilingualEnabled, setBilingualEnabled] = useState(
    () => localStorage.getItem("speakmate-bilingual") !== "off"
  );
  const [voices, setVoices] = useState<TTSVoice[]>([]);
  const [defaultVoice, setDefaultVoice] = useState("");
  const [selectedVoice, setSelected] = useState<string | null>(() => getSelectedVoice());
  const [voiceError, setVoiceError] = useState("");

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

  function chooseVoice(voiceId: string) {
    setSelected(voiceId);
    setSelectedVoice(voiceId);
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
            <p className="muted">选择 AI 回复朗读时的声音，当前音色为默认选项。</p>
            {voiceError ? <p className="voice-error">{voiceError}</p> : null}
            {voices.length > 0 ? (
              <div className="voice-option-grid" role="radiogroup" aria-label="陪练老师音色">
                {voices.map((voice) => (
                  <button
                    key={voice.id}
                    type="button"
                    role="radio"
                    aria-checked={selectedVoice === voice.id}
                    className={selectedVoice === voice.id ? "voice-option voice-option-active" : "voice-option"}
                    onClick={() => chooseVoice(voice.id)}
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

          <section className="profile-card" aria-label="关于">
            <div className="profile-card-header">
              <p className="section-label">关于</p>
              <h2>SpeakMate</h2>
            </div>
            <p className="muted">场景口语陪练 · 按场景对话、实时语法纠错、难度随水平自适应。</p>
          </section>
        </div>
      </section>
    </main>
  );
}
