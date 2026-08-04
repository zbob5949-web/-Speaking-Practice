import type { ReactNode } from "react";

export type AppView = "today" | "scenes" | "practice" | "growth" | "me" | "settings";

type Props = {
  activeView: AppView;
  children: ReactNode;
  onNavigate: (view: AppView) => void;
  onLogout?: () => void;
};

const navItems: Array<{ view: AppView; label: string }> = [
  { view: "today", label: "今日" },
  { view: "scenes", label: "场景" },
  { view: "growth", label: "成长" },
  { view: "me", label: "我的" },
  { view: "settings", label: "设置" }
];

export function AppShell({ activeView, children, onNavigate, onLogout }: Props) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">S</div>
          <div>
            <div className="brand-title">SpeakMate</div>
            <div className="brand-subtitle">场景口语陪练</div>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="主导航">
          {navItems.map((item) => (
            <button
              key={item.view}
              className={item.view === activeView ? "nav-item nav-item-active" : "nav-item"}
              onClick={() => onNavigate(item.view)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-indicator" aria-hidden="true" />
          <span>本地学习空间</span>
          {onLogout ? (
            <button className="logout-button" type="button" onClick={onLogout} aria-label="登出">
              登出
            </button>
          ) : null}
        </div>
      </aside>
      <div className="app-main">{children}</div>
      <nav className="mobile-nav" aria-label="移动端导航">
        {navItems.map((item) => (
          <a
            key={item.view}
            className={item.view === activeView ? "mobile-nav-item mobile-nav-item-active" : "mobile-nav-item"}
            href={"#" + item.view}
            onClick={(event) => {
              event.preventDefault();
              onNavigate(item.view);
            }}
          >
            <span className={"mobile-nav-glyph mobile-nav-glyph-" + item.view} aria-hidden="true" />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>
    </div>
  );
}
