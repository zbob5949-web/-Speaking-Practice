import { useEffect, useState } from "react";
import { getAccount, saveAccount, type Account } from "../api";

const DEFAULT_AVATARS: Record<string, string> = { fox: "🦊", cat: "🐱", panda: "🐼", rabbit: "🐰", koala: "🐨", penguin: "🐧" };

export function AccountCard() {
  const [account, setAccount] = useState<Account | null>(null);
  const [username, setUsername] = useState("");
  const [avatar, setAvatar] = useState("fox");
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [editing, setEditing] = useState<"username" | "avatar" | null>(null);
  function edit(field: "username" | "avatar") {
    if (!account || saving) return;
    setUsername(account.username); setAvatar(account.avatar); setStatus(""); setEditing(field);
  }
  function cancel() {
    if (account) { setUsername(account.username); setAvatar(account.avatar); }
    setEditing(null); setStatus("");
  }
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setStatus("");
    getAccount().then(value => {
      if (cancelled) return;
      setAccount(value); setUsername(value.username); setAvatar(value.avatar);
    }).catch(error => { if (!cancelled) setStatus(error instanceof Error ? error.message : "账号信息加载失败，请重试"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [reload]);
  async function save() {
    setSaving(true); setStatus("");
    try {
      const value = await saveAccount(username.trim(), avatar);
      setAccount(value); setUsername(value.username); setAvatar(value.avatar); setEditing(null); setStatus("已保存");
    } catch (error) { setStatus(error instanceof Error ? error.message : "保存失败"); }
    finally { setSaving(false); }
  }
  return <section className="profile-card account-card" aria-label="个人资料">
    <h2>个人资料</h2>
    <div className="account-summary">
      <button type="button" className="account-avatar-preview" aria-label="更改头像" aria-expanded={editing === "avatar"} disabled={!account || loading || saving} onClick={() => edit("avatar")}>{(account?.avatars ?? DEFAULT_AVATARS)[account?.avatar ?? "fox"] ?? DEFAULT_AVATARS.fox}</button>
      <button type="button" className="account-username-display" aria-label="更改用户名" aria-expanded={editing === "username"} disabled={!account || loading || saving} onClick={() => edit("username")}>{account?.username ?? (loading ? "加载中…" : "账号资料未加载")}</button>
    </div>
    {loading ? <p role="status">正在加载账号资料…</p> : null}
    {!loading && !account ? <button type="button" className="settings-logout-button" onClick={() => setReload(value => value + 1)}>重新加载账号资料</button> : null}
    {editing ? <form className="account-editor" onSubmit={event => { event.preventDefault(); void save(); }}>
      {editing === "username" ? <label className="account-name">用户名<input autoFocus value={username} maxLength={24} disabled={saving} onChange={event => setUsername(event.target.value)} /></label> :
        <div className="avatar-options" role="radiogroup" aria-label="选择头像">
          {Object.entries(account?.avatars ?? DEFAULT_AVATARS).map(([id, emoji]) => <button key={id} type="button" role="radio" aria-label={`头像 ${emoji}`} aria-checked={avatar === id} disabled={saving} onClick={() => setAvatar(id)}>{emoji}</button>)}
        </div>}
      <div className="account-editor-actions">
        <button type="submit" className="settings-logout-button" disabled={saving || !username.trim()}>{saving ? "保存中…" : "保存资料"}</button>
        <button type="button" className="settings-logout-button" disabled={saving} onClick={cancel}>取消</button>
      </div>
    </form> : null}
    {account?.is_guest ? <p className="muted">游客资料仅保留在本次游客身份中。</p> : null}
    <p role="status">{status}</p>
  </section>;
}
