import type { ReactNode } from "react";

export type AppView = "home" | "today" | "scenes" | "practice" | "growth" | "me" | "settings";

type Props = {
  activeView: AppView;
  children: ReactNode;
  onNavigate: (view: AppView) => void;
  onLogout?: () => void;
  /** 返回上一页（有历史时才显示） */
  onBack?: () => void;
  canBack?: boolean;
};

function IconHome() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4v-5H9v5H5a1 1 0 0 1-1-1z" />
    </svg>
  );
}

function IconScenes() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3 21 8l-9 5-9-5z" />
      <path d="M3 12.5 12 17l9-4.5" />
      <path d="M3 17 12 21l9-4" />
    </svg>
  );
}

function IconMe() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="8.5" r="3.5" />
      <path d="M5 20c0-3.6 3.1-6 7-6s7 2.4 7 6" />
    </svg>
  );
}

const navItems: Array<{ view: AppView; label: string; icon: ReactNode }> = [
  { view: "home", label: "首页", icon: <IconHome /> },
  { view: "scenes", label: "场景", icon: <IconScenes /> },
  { view: "me", label: "我的", icon: <IconMe /> },
];

/** 练习 / 成长 / 设置 不占 tab：tab 高亮回落到归属页 */
function navActiveView(view: AppView): AppView {
  if (view === "home") return "home";
  if (view === "today" || view === "practice" || view === "growth") return "home";
  if (view === "settings") return "me";
  return view;
}

export function AppShell({ activeView, children, onNavigate, onLogout, onBack, canBack }: Props) {
  const current = navActiveView(activeView);
  // 导航只在主页面出现；点任一导航键进入对应界面后隐去（靠返回键回主页）
  const showNav = activeView === "home";
  // 返回键：除首页外都显示（统一回首页）
  const showBack = activeView !== "home";
  return (
    <div className={showNav ? "app-shell" : "app-shell app-shell-nonav"}>
      {showBack && onBack ? (
        <button
          type="button"
          className={
            activeView === "today" || activeView === "practice"
              ? "app-back-btn app-back-btn-chat"
              : "app-back-btn"
          }
          onClick={onBack}
          aria-label="返回上一页"
          title="返回"
        >
          <span aria-hidden="true">←</span>
        </button>
      ) : null}
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
              className={item.view === current ? "nav-item nav-item-active" : "nav-item"}
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
      <nav className={showNav ? "mobile-nav" : "mobile-nav mobile-nav-hidden"} aria-label="移动端导航">
        {navItems.map((item) => (
          <a
            key={item.view}
            className={item.view === current ? "mobile-nav-item mobile-nav-item-active" : "mobile-nav-item"}
            href={"#" + item.view}
            aria-label={item.label}
            aria-current={item.view === current ? "page" : undefined}
            onClick={(event) => {
              event.preventDefault();
              onNavigate(item.view);
            }}
          >
            <span className="mobile-nav-icon" aria-hidden="true">{item.icon}</span>
          </a>
        ))}
      </nav>
    </div>
  );
}
