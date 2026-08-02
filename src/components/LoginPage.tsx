import { FormEvent, useState } from "react";
import { authGuest, authLogin, authRegister, storeAuth } from "../api";
import { PrimaryButton } from "./ui";

type Props = {
  onAuthed: () => void;
};

type Mode = "login" | "register";

export function LoginPage({ onAuthed }: Props) {
  const [mode, setMode] = useState<Mode>("login");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (mode === "register" && password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }
    setIsSubmitting(true);
    try {
      const result = mode === "login"
        ? await authLogin(phone, password)
        : await authRegister(phone, password);
      storeAuth(result);
      onAuthed();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "操作失败，请稍后再试");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleGuest() {
    setError("");
    setIsSubmitting(true);
    try {
      const result = await authGuest();
      storeAuth(result);
      onAuthed();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "游客登录失败，请稍后再试");
    } finally {
      setIsSubmitting(false);
    }
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError("");
  }

  return (
    <main className="onboarding-page">
      <div className="onboarding-card auth-card">
        <section className="hero-panel">
          <p className="hero-kicker">账号</p>
          <h1>SpeakMate 场景口语陪练</h1>
          <p className="muted">登录后继续你的练习，所有数据保存在本地。</p>
        </section>

        <form className="setup-form" onSubmit={handleSubmit} aria-label="登录注册表单">
          <div className="auth-tabs" role="tablist" aria-label="登录或注册">
            <button
              className={mode === "login" ? "auth-tab auth-tab-active" : "auth-tab"}
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              onClick={() => switchMode("login")}
            >
              登录
            </button>
            <button
              className={mode === "register" ? "auth-tab auth-tab-active" : "auth-tab"}
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              onClick={() => switchMode("register")}
            >
              注册
            </button>
          </div>

          <label className="field">
            <span>用户名 / 手机号</span>
            <input
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="3-20 位字母、数字或下划线"
              autoComplete="username"
              required
            />
          </label>
          <label className="field">
            <span>密码</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="至少 6 位"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />
          </label>
          {mode === "register" ? (
            <label className="field">
              <span>确认密码</span>
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="再次输入密码"
                autoComplete="new-password"
                required
              />
            </label>
          ) : null}

          {error ? <p className="error-message" role="alert">{error}</p> : null}

          <PrimaryButton type="submit" disabled={isSubmitting || !phone || !password}>
            {isSubmitting ? "处理中…" : mode === "login" ? "登录" : "注册并登录"}
          </PrimaryButton>

          <button
            className="auth-guest-button"
            type="button"
            disabled={isSubmitting}
            onClick={() => void handleGuest()}
          >
            以游客身份进入
          </button>
        </form>
      </div>
    </main>
  );
}
