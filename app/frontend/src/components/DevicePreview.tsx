import { useEffect, useState, type ReactNode } from "react";

type Device = "desktop" | "phone";

const STORAGE_KEY = "speakmate-preview-device";
const SHORTCUT = "m";

function isFrameMode(): boolean {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).has("frame");
}

/**
 * 开发/验收用的「电脑 ⇄ 手机」布局切换器。
 *
 * 手机模式用 iframe 承载同一个应用（iframe 视口宽度 = 390px），
 * 这样 styles.css 里的 @media (max-width: 600px) 会真实命中，
 * 看到的就是真机上的那套布局，而不是缩放出来的假预览。
 *
 * - 地址栏带 ?frame=1 时直接渲染 children（iframe 内部不再套一层）
 * - 快捷键：Ctrl/Cmd + Shift + M
 * - 偏好持久化到 localStorage
 */
export function DevicePreview({ children }: { children: ReactNode }) {
  const frameMode = isFrameMode();
  const [device, setDevice] = useState<Device>(() => {
    if (typeof window === "undefined") return "desktop";
    return localStorage.getItem(STORAGE_KEY) === "phone" ? "phone" : "desktop";
  });

  useEffect(() => {
    if (frameMode) return;
    localStorage.setItem(STORAGE_KEY, device);
  }, [device, frameMode]);

  useEffect(() => {
    if (frameMode) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === SHORTCUT) {
        event.preventDefault();
        setDevice((current) => (current === "phone" ? "desktop" : "phone"));
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [frameMode]);

  if (frameMode) {
    return <>{children}</>;
  }

  const isPhone = device === "phone";
  const frameSrc = `${window.location.pathname}?frame=1${window.location.hash}`;

  return (
    <>
      {isPhone ? (
        <div className="device-stage">
          <div className="device-shell">
            <span className="device-notch" aria-hidden="true" />
            <iframe className="device-screen" src={frameSrc} title="手机布局预览" />
          </div>
          <p className="device-caption">手机布局预览 · 390 × 844</p>
        </div>
      ) : (
        children
      )}
      <button
        type="button"
        className={isPhone ? "device-toggle device-toggle-on" : "device-toggle"}
        onClick={() => setDevice(isPhone ? "desktop" : "phone")}
        title="切换电脑 / 手机布局（Ctrl+Shift+M）"
        aria-label={isPhone ? "切换到电脑布局" : "切换到手机布局"}
      >
        <span className="device-toggle-icon" aria-hidden="true">{isPhone ? "💻" : "📱"}</span>
        <span className="device-toggle-text">{isPhone ? "电脑布局" : "手机布局"}</span>
      </button>
    </>
  );
}
