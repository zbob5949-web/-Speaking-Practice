import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  adminGet,
  adminLogin,
  adminSend,
  clearAdminPhone,
  clearAdminToken,
  getAdminPhone,
  getToken,
  setAdminPhone,
  setAdminToken,
  type AdminUser,
  type DashboardData,
  type Paged,
  type PromptItem,
  type ReportsData,
  type Row,
  type SessionDetail,
  type SessionRow,
  type TableColumn,
  type TableMeta,
  type TrendsData,
} from "./api";
import "./styles.css";

type Section = "dashboard" | "users" | "sessions" | "prompts" | "trends" | "reports" | "table";
type Notify = (message: string, kind?: "ok" | "error") => void;

const NAV_ITEMS: Array<{ key: Exclude<Section, "table">; label: string; icon: string }> = [
  { key: "dashboard", label: "概览", icon: "◫" },
  { key: "users", label: "用户管理", icon: "◉" },
  { key: "sessions", label: "练习会话", icon: "▤" },
  { key: "prompts", label: "提示词配置", icon: "✎" },
  { key: "trends", label: "趋势分析", icon: "↗" },
  { key: "reports", label: "学习报告", icon: "▥" },
];

const SCENARIO_ZH: Record<string, string> = {
  "airport-check-in": "机场值机",
  "hotel-check-in": "酒店入住",
  "restaurant-order": "餐厅点餐",
  "job-interview": "面试沟通",
  "doctor-visit": "就医问诊",
  "shopping-return": "购物退换",
  free_talk: "自由对话",
};

function formatTime(value: unknown): string {
  if (!value) return "—";
  return String(value).replace("T", " ").slice(0, 19);
}

function formatDate(value: unknown): string {
  if (!value) return "—";
  return String(value).replace("T", " ").slice(0, 10);
}

function badgeTone(value: string): string {
  const text = value.toLowerCase();
  if (["active", "done", "applied", "completed", "success", "admin", "是", "normal"].includes(text)) return "ok";
  if (["pending", "in_progress", "medium", "review", "draft"].includes(text)) return "warn";
  if (["failed", "expired", "disabled", "inactive", "high", "major", "否"].includes(text)) return "bad";
  return "info";
}

function scenarioName(id?: string | null): string {
  if (!id) return "—";
  return SCENARIO_ZH[id] ?? id;
}

function TableCell({ value, column }: { value: unknown; column: TableColumn }) {
  if (value === null || value === undefined || value === "") {
    return <span className="muted">—</span>;
  }
  if (typeof value === "object") {
    const text = JSON.stringify(value);
    return (
      <span className="cell-json" title={text}>
        {text}
      </span>
    );
  }
  const text = String(value);
  if (column.kind === "select") {
    return <span className={`badge badge-${badgeTone(text)}`}>{text}</span>;
  }
  if (text.length > 90) {
    return (
      <span className="cell-clamp" title={text}>
        {text}
      </span>
    );
  }
  return <span>{text}</span>;
}

// ==========================================================================
// 登录
// ==========================================================================

function AdminLogin({ onLogin }: { onLogin: (token: string, phone: string) => void }) {
  const [phone, setPhone] = useState("18800000000");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!phone.trim() || !password.trim()) {
      setError("请输入管理员手机号和密码");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await adminLogin(phone.trim(), password);
      onLogin(result.access_token, phone.trim());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-brand">
        <div className="login-logo">S</div>
        <p className="login-kicker">SPEAKMATE</p>
        <h1>管理后台</h1>
        <p className="login-desc">用户、练习会话、纠错数据与通用数据表的统一管理入口。</p>
        <div className="login-foot">英语口语陪练 · 运营管理</div>
      </div>
      <div className="login-panel">
        <form className="login-form" onSubmit={handleSubmit}>
          <p className="login-form-kicker">管理员登录</p>
          <h2>欢迎回来</h2>
          <label className="field">
            <span>手机号</span>
            <input
              autoComplete="username"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="管理员手机号"
            />
          </label>
          <label className="field">
            <span>密码</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="至少 6 位"
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button type="submit" className="btn btn-primary login-submit" disabled={loading}>
            {loading ? "登录中…" : "登录管理后台"}
          </button>
          <p className="login-hint">
            管理员账号由后端脚本创建：
            <code>python tools/create_admin.py &lt;手机号&gt; &lt;密码&gt; --super</code>
          </p>
        </form>
      </div>
    </div>
  );
}

// ==========================================================================
// 主框架
// ==========================================================================

export default function AdminApp() {
  const [token, setTokenState] = useState(getToken());
  const [phone, setPhoneState] = useState(getAdminPhone());
  const [section, setSection] = useState<Section>("table");
  const [tableName, setTableName] = useState("user_profile");
  const [tables, setTables] = useState<TableMeta[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [booting, setBooting] = useState(Boolean(getToken()));
  const [toast, setToast] = useState<{ message: string; kind: "ok" | "error" } | null>(null);
  const toastTimer = useRef<number | null>(null);

  const notify: Notify = (message, kind = "ok") => {
    setToast({ message, kind });
    if (toastTimer.current !== null) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 3200);
  };

  useEffect(() => {
    function onUnauthorized() {
      setTokenState("");
      setBooting(false);
    }
    window.addEventListener("admin:unauthorized", onUnauthorized);
    return () => window.removeEventListener("admin:unauthorized", onUnauthorized);
  }, []);

  useEffect(() => {
    if (!token) {
      setBooting(false);
      return;
    }
    let cancelled = false;
    setBooting(true);
    adminGet<{ items: TableMeta[]; total: number }>("/api/admin/tables")
      .then(async (data) => {
        if (cancelled) return;
        setTables(data.items);
        // 先让页面出来，表数量在后台补齐，避免登录后长时间停在加载态
        setBooting(false);
        const entries = await Promise.all(
          data.items.map(async (item) => {
            try {
              const page = await adminGet<Paged<Row>>(`/api/admin/tables/${item.table}?page=1&page_size=1`);
              return [item.table, page.total] as const;
            } catch {
              return [item.table, 0] as const;
            }
          }),
        );
        if (!cancelled) {
          setCounts(Object.fromEntries(entries));
        }
      })
      .catch((reason) => {
        if (!cancelled) {
          notify(reason instanceof Error ? reason.message : "加载管理数据失败", "error");
          setBooting(false);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (tables.length > 0 && !tables.some((item) => item.table === tableName)) {
      setTableName(tables[0].table);
    }
  }, [tables, tableName]);

  const activeTable = useMemo(
    () => tables.find((item) => item.table === tableName) ?? tables[0] ?? null,
    [tables, tableName],
  );

  function handleLogin(nextToken: string, nextPhone: string) {
    setAdminToken(nextToken);
    setAdminPhone(nextPhone);
    setTokenState(nextToken);
    setPhoneState(nextPhone);
    setSection("table");
  }

  function handleLogout() {
    clearAdminToken();
    clearAdminPhone();
    setTokenState("");
    setPhoneState("");
    setTables([]);
    setCounts({});
  }

  if (!token) {
    return <AdminLogin onLogin={handleLogin} />;
  }

  const title =
    section === "table"
      ? activeTable?.label ?? "数据表"
      : NAV_ITEMS.find((item) => item.key === section)?.label ?? "";

  let content: ReactNode;
  if (booting) {
    content = (
      <div className="admin-loading">
        <span className="spinner" />
        正在加载管理数据…
      </div>
    );
  } else if (section === "table" && activeTable) {
    content = (
      <TableManager
        key={activeTable.table}
        table={activeTable.table}
        meta={activeTable}
        notify={notify}
        onTotal={(table, total) => setCounts((current) => ({ ...current, [table]: total }))}
      />
    );
  } else if (section === "table") {
    content = <div className="empty-state">还没有加载到可管理的数据表。</div>;
  } else if (section === "dashboard") {
    content = <DashboardPage notify={notify} />;
  } else if (section === "users") {
    content = <UsersPage notify={notify} />;
  } else if (section === "sessions") {
    content = <SessionsPage notify={notify} />;
  } else if (section === "prompts") {
    content = <PromptsPage notify={notify} />;
  } else if (section === "trends") {
    content = <TrendsPage notify={notify} />;
  } else {
    content = <ReportsPage notify={notify} />;
  }

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <div className="admin-brand-mark">S</div>
          <div>
            <strong>SpeakMate</strong>
            <span>管理后台</span>
          </div>
        </div>

        <div className="admin-nav-scroll">
          <p className="admin-nav-label">工作台</p>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={section === item.key ? "admin-nav-item active" : "admin-nav-item"}
              onClick={() => setSection(item.key)}
            >
              <span className="admin-nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span>{item.label}</span>
            </button>
          ))}

          <p className="admin-nav-label admin-nav-label-tables">
            数据表
            <span>{tables.length}</span>
          </p>
          {tables.map((item) => (
            <button
              key={item.table}
              type="button"
              className={
                section === "table" && tableName === item.table
                  ? "admin-nav-table active"
                  : "admin-nav-table"
              }
              onClick={() => {
                setTableName(item.table);
                setSection("table");
              }}
            >
              <span className="admin-nav-table-main">
                <span>{item.label}</span>
                <small>{item.table}</small>
              </span>
              <span className="admin-nav-count">{counts[item.table] ?? "—"}</span>
            </button>
          ))}
        </div>

        <div className="admin-sidebar-foot">
          <span className="admin-status-dot" />
          <div>
            <strong>{phone || "管理员"}</strong>
            <span>已登录管理后台</span>
          </div>
          <button type="button" onClick={handleLogout} title="退出登录">
            退出
          </button>
        </div>
      </aside>

      <main className="admin-main">
        <header className="admin-topbar">
          <div>
            <p className="admin-breadcrumb">管理后台 / {section === "table" ? "数据表" : "工作台"}</p>
            <h1>{title}</h1>
          </div>
          <div className="admin-topbar-right">
            <span className="admin-topbar-user">{phone || "admin"}</span>
            <button type="button" className="btn btn-ghost" onClick={handleLogout}>
              退出登录
            </button>
          </div>
        </header>
        <div className="admin-content">{content}</div>
      </main>

      {toast ? <div className={`admin-toast admin-toast-${toast.kind}`}>{toast.message}</div> : null}
    </div>
  );
}

// ==========================================================================
// 通用数据表管理（仿照截图的核心页面）
// ==========================================================================

function TableManager({
  table,
  meta,
  notify,
  onTotal,
}: {
  table: string;
  meta: TableMeta;
  notify: Notify;
  onTotal: (table: string, total: number) => void;
}) {
  const [page, setPage] = useState(1);
  const [keywordInput, setKeywordInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [data, setData] = useState<Paged<Row> | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [editor, setEditor] = useState<{ mode: "create" | "edit"; row?: Row } | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const searchableColumns = meta.columns.filter((column) => column.searchable);

  useEffect(() => {
    let cancelled = false;
    setRefreshing(true);
    if (!data) setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (keyword) params.set("keyword", keyword);
    adminGet<Paged<Row>>(`/api/admin/tables/${table}?${params.toString()}`)
      .then((result) => {
        if (cancelled) return;
        setData(result);
        onTotal(table, result.total);
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
          setRefreshing(false);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [table, page, keyword, refreshKey]);

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setKeyword(keywordInput.trim());
  }

  async function handleDelete(row: Row) {
    const id = Number(row.id);
    if (!window.confirm(`确定删除「${meta.label}」#${id} 吗？此操作不可撤销。`)) return;
    setDeletingId(id);
    try {
      await adminSend(`/api/admin/tables/${table}/${id}`, "DELETE");
      notify("删除成功");
      setRefreshKey((key) => key + 1);
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "删除失败", "error");
    } finally {
      setDeletingId(null);
    }
  }

  const totalPages = data?.pages ?? 1;

  return (
    <section className="admin-page">
      <div className="page-head">
        <div>
          <p className="page-kicker">数据表 · {table}</p>
          <h2>{meta.label}</h2>
          <p className="page-desc">
            共 <strong>{data?.total ?? 0}</strong> 条记录，字段由后端白名单动态提供。
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setEditor({ mode: "create" })}>
          ＋ 新增记录
        </button>
      </div>

      <div className="table-toolbar">
        <form className="search-box" onSubmit={submitSearch}>
          <span className="search-icon" aria-hidden="true">
            ⌕
          </span>
          <input
            value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
            placeholder={
              searchableColumns.length > 0
                ? `按${searchableColumns.map((column) => column.label).slice(0, 3).join(" / ")}搜索`
                : "搜索关键词"
            }
          />
          <button type="submit" className="btn btn-soft">
            查询
          </button>
          {keyword ? (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setKeywordInput("");
                setKeyword("");
                setPage(1);
              }}
            >
              清除
            </button>
          ) : null}
        </form>
        <span className="table-toolbar-hint">
          {refreshing ? (
            <span className="inline-loading">
              <span className="spinner" />
              更新中…
            </span>
          ) : (
            "按 rowid 倒序 · 每页 20 条"
          )}
        </span>
      </div>

      <div className="admin-card table-card">
        <div className="table-scroll">
          <table className="admin-table">
            <thead>
              <tr>
                {meta.columns.map((column) => (
                  <th key={column.name}>
                    <span>{column.label}</span>
                    <small>{column.name}</small>
                  </th>
                ))}
                <th className="actions-col">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && !data ? (
                <tr>
                  <td colSpan={meta.columns.length + 1} className="table-state">
                    <span className="spinner" /> 正在加载…
                  </td>
                </tr>
              ) : !data ? (
                <tr>
                  <td colSpan={meta.columns.length + 1} className={error ? "table-state table-state-error" : "table-state"}>
                    {error || "暂无记录"}
                  </td>
                </tr>
              ) : data.items.length === 0 ? (
                <tr>
                  <td colSpan={meta.columns.length + 1} className="table-state">
                    暂无记录
                  </td>
                </tr>
              ) : (
                data.items.map((row) => (
                  <tr key={String(row.id)}>
                    {meta.columns.map((column) => (
                      <td key={column.name}>
                        <TableCell value={row[column.name]} column={column} />
                      </td>
                    ))}
                    <td className="actions-col">
                      <button
                        type="button"
                        className="row-action"
                        onClick={() => setEditor({ mode: "edit", row })}
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        className="row-action row-action-danger"
                        disabled={deletingId === Number(row.id)}
                        onClick={() => void handleDelete(row)}
                      >
                        {deletingId === Number(row.id) ? "删除中…" : "删除"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="table-pagination">
          <span>
            第 <strong>{data?.page ?? page}</strong> / {Math.max(totalPages, 1)} 页 · 共{" "}
            <strong>{data?.total ?? 0}</strong> 条
          </span>
          <div>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              上一页
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={page >= totalPages}
              onClick={() => setPage((current) => current + 1)}
            >
              下一页
            </button>
          </div>
        </div>
      </div>

      {editor ? (
        <RecordModal
          table={table}
          meta={meta}
          mode={editor.mode}
          row={editor.row}
          onClose={() => setEditor(null)}
          onSaved={(message) => {
            setEditor(null);
            notify(message);
            setRefreshKey((key) => key + 1);
          }}
        />
      ) : null}
    </section>
  );
}

function RecordModal({
  table,
  meta,
  mode,
  row,
  onClose,
  onSaved,
}: {
  table: string;
  meta: TableMeta;
  mode: "create" | "edit";
  row?: Row;
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const fields = meta.columns.filter((column) => !column.readonly);
  const [values, setValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const field of fields) {
      const raw = row?.[field.name];
      if (raw === null || raw === undefined) {
        initial[field.name] = field.kind === "select" && field.options.length > 0 ? field.options[0] : "";
      } else if (typeof raw === "object") {
        initial[field.name] = JSON.stringify(raw, null, 2);
      } else {
        initial[field.name] = String(raw);
      }
    }
    return initial;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function setValue(name: string, value: string) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {};
      for (const field of fields) {
        const raw = (values[field.name] ?? "").trim();
        if (!raw) {
          if (field.required) throw new Error(`${field.label} 不能为空`);
          continue;
        }
        if (field.kind === "json") {
          try {
            JSON.parse(raw);
          } catch {
            throw new Error(`${field.label} 必须是合法 JSON`);
          }
          payload[field.name] = raw;
        } else if (field.kind === "int") {
          const number = Number(raw);
          if (!Number.isFinite(number)) throw new Error(`${field.label} 必须是整数`);
          payload[field.name] = number;
        } else {
          payload[field.name] = raw;
        }
      }

      if (mode === "create") {
        await adminSend(`/api/admin/tables/${table}`, "POST", { values: payload });
        onSaved("创建成功");
      } else {
        await adminSend(`/api/admin/tables/${table}/${Number(row?.id)}`, "PUT", { values: payload });
        onSaved("更新成功");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-mask" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-card modal-card-wide">
        <header className="modal-head">
          <div>
            <p className="page-kicker">{meta.label}</p>
            <h2>{mode === "create" ? "新增记录" : `编辑 #${row?.id ?? ""}`}</h2>
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>
        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="form-grid">
            {fields.map((field) => (
              <label
                key={field.name}
                className={
                  field.kind === "json" || field.textarea
                    ? "field field-full"
                    : "field"
                }
              >
                <span>
                  {field.label}
                  {field.required ? <em>*</em> : null}
                  <small>{field.name}</small>
                </span>
                {field.kind === "select" && field.options.length > 0 ? (
                  <select value={values[field.name] ?? ""} onChange={(event) => setValue(field.name, event.target.value)}>
                    <option value="">（不设置）</option>
                    {field.options.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                ) : field.kind === "json" || field.textarea ? (
                  <textarea
                    rows={field.kind === "json" ? 7 : 4}
                    value={values[field.name] ?? ""}
                    onChange={(event) => setValue(field.name, event.target.value)}
                  />
                ) : (
                  <input
                    type={field.kind === "int" ? "number" : "text"}
                    value={values[field.name] ?? ""}
                    onChange={(event) => setValue(field.name, event.target.value)}
                    placeholder={field.kind}
                  />
                )}
              </label>
            ))}
          </div>
          {error ? <p className="form-error">{error}</p> : null}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              取消
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "保存中…" : "保存"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ==========================================================================
// 概览
// ==========================================================================

function DashboardPage({ notify }: { notify: Notify }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    adminGet<DashboardData>("/api/admin/dashboard/overview")
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <div className="admin-loading"><span className="spinner" />正在加载概览…</div>;
  if (error || !data) {
    return <div className="empty-state">{error || "暂无数据"}</div>;
  }

  const stats = [
    { label: "用户总数", value: data.users.total, hint: `今日新增 ${data.users.new_today} · 7 日登录 ${data.users.logged_in_7d}` },
    { label: "练习会话", value: data.sessions.total, hint: `完成 ${data.sessions.finished} · 今日 ${data.sessions.today}` },
    { label: "对话轮次", value: data.conversations.turns_total, hint: `今日 ${data.conversations.turns_today}` },
    { label: "纠错反馈", value: data.conversations.feedback_total, hint: `错题本 ${data.libraries.error_bank}` },
  ];

  const maxHot = Math.max(1, ...data.hot_scenarios.map((item) => item.count));

  return (
    <section className="admin-page">
      <div className="page-head">
        <div>
          <p className="page-kicker">Dashboard</p>
          <h2>运营概览</h2>
          <p className="page-desc">用户、练习、对话与学习库的核心数据。</p>
        </div>
        <span className="page-chip">平均分 {data.sessions.avg_score}</span>
      </div>

      <div className="stat-grid">
        {stats.map((stat) => (
          <article className="stat-card" key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
            <small>{stat.hint}</small>
          </article>
        ))}
      </div>

      <div className="dash-grid">
        <section className="admin-card panel">
          <div className="panel-head">
            <h3>热门场景</h3>
            <span>按会话数</span>
          </div>
          {data.hot_scenarios.length === 0 ? (
            <p className="empty-inline">还没有练习数据</p>
          ) : (
            <div className="bar-list">
              {data.hot_scenarios.map((item) => (
                <div className="bar-row" key={item.scenario_id}>
                  <span className="bar-label">{scenarioName(item.scenario_id)}</span>
                  <span className="bar-track">
                    <span style={{ width: `${(item.count / maxHot) * 100}%` }} />
                  </span>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="admin-card panel">
          <div className="panel-head">
            <h3>学习库</h3>
            <span>内容量</span>
          </div>
          <div className="mini-stat-grid">
            <div><strong>{data.libraries.error_bank}</strong><span>错题本</span></div>
            <div><strong>{data.libraries.expression_bank}</strong><span>表达库</span></div>
            <div><strong>{data.libraries.favorites}</strong><span>场景收藏</span></div>
            <div><strong>{data.users.admin}</strong><span>管理员</span></div>
          </div>
        </section>
      </div>

      <section className="admin-card panel">
        <div className="panel-head">
          <h3>最近练习会话</h3>
          <span>最新 8 条</span>
        </div>
        <div className="table-scroll">
          <table className="admin-table compact">
            <thead>
              <tr>
                <th>ID</th>
                <th>场景</th>
                <th>话题</th>
                <th>开始时间</th>
                <th>轮次</th>
                <th>得分</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_sessions.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{scenarioName(item.scenario_id)}</td>
                  <td>{item.topic ?? "—"}</td>
                  <td>{formatTime(item.started_at)}</td>
                  <td>{item.turn_count}</td>
                  <td>{item.overall_score ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

// ==========================================================================
// 用户管理
// ==========================================================================

function UsersPage({ notify }: { notify: Notify }) {
  const [data, setData] = useState<Paged<AdminUser> | null>(null);
  const [page, setPage] = useState(1);
  const [keywordInput, setKeywordInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [active, setActive] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRefreshing(true);
    if (!data) setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (keyword) params.set("keyword", keyword);
    if (active) params.set("is_active", active);
    adminGet<Paged<AdminUser>>(`/api/admin/users?${params.toString()}`)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
          setRefreshing(false);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, keyword, active, refreshKey]);

  async function toggleActive(user: AdminUser) {
    const nextActive = !user.is_active;
    // 先本地切换开关，避免等接口回来时表格整块闪一下
    setData((current) =>
      current
        ? {
            ...current,
            items: current.items.map((item) =>
              item.id === user.id ? { ...item, is_active: nextActive } : item,
            ),
          }
        : current,
    );
    try {
      await adminSend(`/api/admin/users/${user.id}`, "PUT", { is_active: nextActive });
      notify(`已${nextActive ? "启用" : "停用"} ${user.phone}`);
      setRefreshKey((key) => key + 1);
    } catch (reason) {
      setData((current) =>
        current
          ? {
              ...current,
              items: current.items.map((item) =>
                item.id === user.id ? { ...item, is_active: user.is_active } : item,
              ),
            }
          : current,
      );
      notify(reason instanceof Error ? reason.message : "操作失败", "error");
    }
  }

  async function resetPassword(user: AdminUser) {
    const password = window.prompt(`为 ${user.phone} 设置新密码（至少 6 位）`);
    if (!password) return;
    if (password.length < 6) {
      notify("密码至少 6 位", "error");
      return;
    }
    try {
      await adminSend(`/api/admin/users/${user.id}/password`, "PUT", { password });
      notify("密码已重置");
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "重置失败", "error");
    }
  }

  async function removeUser(user: AdminUser) {
    if (!window.confirm(`确定删除账号 ${user.phone} 吗？`)) return;
    try {
      await adminSend(`/api/admin/users/${user.id}`, "DELETE");
      notify("删除成功");
      setRefreshKey((key) => key + 1);
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "删除失败", "error");
    }
  }

  const totalPages = data?.pages ?? 1;

  function applyFilters() {
    setPage(1);
    setKeyword(keywordInput.trim());
    setRefreshKey((key) => key + 1);
  }

  return (
    <section className="admin-page">
      <div className="page-head">
        <div>
          <p className="page-kicker">Users</p>
          <h2>用户管理</h2>
          <p className="page-desc">管理账号启用状态、访问角色、超级管理员权限及登录信息。</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
          ＋ 新建账号
        </button>
      </div>

      <form
        className="user-toolbar"
        onSubmit={(event) => {
          event.preventDefault();
          applyFilters();
        }}
      >
        <input
          className="user-search"
          value={keywordInput}
          onChange={(event) => setKeywordInput(event.target.value)}
          placeholder="输入用户名或手机号搜索"
        />
        <select
          value={active}
          onChange={(event) => {
            setActive(event.target.value);
            setPage(1);
          }}
        >
          <option value="">账户状态</option>
          <option value="true">已启用</option>
          <option value="false">已停用</option>
        </select>
        <button type="submit" className="btn btn-dark">
          刷新
        </button>
        {refreshing ? (
          <span className="inline-loading">
            <span className="spinner" />
            更新中…
          </span>
        ) : null}
        {error && data ? <span className="inline-error">{error}</span> : null}
      </form>

      <div className="admin-card table-card">
        <div className="table-scroll">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>用户名/手机号</th>
                <th>角色</th>
                <th>权限</th>
                <th>状态</th>
                <th>最后登录时间</th>
                <th>登录 IP 地址</th>
                <th className="actions-col">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && !data ? (
                <tr><td colSpan={8} className="table-state"><span className="spinner" />加载中…</td></tr>
              ) : !data ? (
                <tr><td colSpan={8} className={error ? "table-state table-state-error" : "table-state"}>{error || "暂无用户"}</td></tr>
              ) : data.items.length === 0 ? (
                <tr><td colSpan={8} className="table-state">暂无用户</td></tr>
              ) : (
                data.items.map((user) => (
                  <tr key={user.id}>
                    <td className="id-cell">{user.id}</td>
                    <td><strong className="phone-cell">{({fox:"🦊", cat:"🐱", panda:"🐼", rabbit:"🐰", koala:"🐨", penguin:"🐧"} as Record<string,string>)[user.avatar] ?? "🦊"} {user.username}</strong><small>{user.phone}</small></td>
                    <td><span className="role-text">{user.role === "admin" ? "管理员" : "普通用户"}</span></td>
                    <td>
                      <span className={user.is_super_admin ? "permission-super" : "permission-normal"}>
                        {user.is_super_admin ? "超级管理员" : "普通账号"}
                      </span>
                    </td>
                    <td>
                      <div className="status-cell">
                        <button
                          type="button"
                          role="switch"
                          aria-checked={user.is_active}
                          aria-label={user.is_active ? "停用账号" : "启用账号"}
                          className={user.is_active ? "status-switch status-switch-on" : "status-switch"}
                          onClick={() => void toggleActive(user)}
                        >
                          <span className="status-knob" />
                        </button>
                        <span className={user.is_active ? "status-text status-text-on" : "status-text"}>
                          {user.is_active ? "已启用" : "已停用"}
                        </span>
                      </div>
                    </td>
                    <td><span className="last-login">{user.last_login ? formatTime(user.last_login) : "未登录"}</span></td>
                    <td><span className="ip-text">{user.last_login_ip || "暂无记录"}</span></td>
                    <td className="actions-col">
                      <button type="button" className="row-action row-action-muted" onClick={() => void toggleActive(user)}>
                        {user.is_active ? "停用" : "启用"}
                      </button>
                      <button type="button" className="row-action" onClick={() => setEditing(user)}>编辑</button>
                      <button type="button" className="row-action row-action-danger" onClick={() => void removeUser(user)}>删除</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="table-pagination">
          <span>第 <strong>{data?.page ?? page}</strong> / {Math.max(totalPages, 1)} 页 · 共 <strong>{data?.total ?? 0}</strong> 个账号</span>
          <div>
            <button type="button" className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>上一页</button>
            <button type="button" className="btn btn-ghost" disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>下一页</button>
          </div>
        </div>
      </div>

      {createOpen ? (
        <UserCreateModal
          onClose={() => setCreateOpen(false)}
          onSaved={() => {
            setCreateOpen(false);
            notify("账号创建成功");
            setRefreshKey((key) => key + 1);
          }}
        />
      ) : null}
      {editing ? (
        <UserEditModal
          user={editing}
          onClose={() => setEditing(null)}
          onResetPassword={() => void resetPassword(editing)}
          onSaved={() => {
            setEditing(null);
            notify("用户信息已更新");
            setRefreshKey((key) => key + 1);
          }}
        />
      ) : null}
    </section>
  );
}

function UserCreateModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await adminSend("/api/admin/users", "POST", { phone: phone.trim(), password, role });
      onSaved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "创建失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-mask" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-card">
        <header className="modal-head">
          <div><p className="page-kicker">Users</p><h2>新建账号</h2></div>
          <button type="button" className="modal-close" onClick={onClose}>×</button>
        </header>
        <form className="modal-form" onSubmit={submit}>
          <label className="field"><span>手机号</span><input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="至少 6 位" /></label>
          <label className="field"><span>密码</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="至少 6 位" /></label>
          <label className="field"><span>角色</span>
            <select value={role} onChange={(event) => setRole(event.target.value)}>
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "创建中…" : "创建账号"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function UserEditModal({
  user,
  onClose,
  onSaved,
  onResetPassword,
}: {
  user: AdminUser;
  onClose: () => void;
  onSaved: () => void;
  onResetPassword: () => void;
}) {
  const [role, setRole] = useState(user.role);
  const [isActive, setIsActive] = useState(user.is_active);
  const [isSuper, setIsSuper] = useState(user.is_super_admin);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await adminSend(`/api/admin/users/${user.id}`, "PUT", {
        role,
        is_active: isActive,
        is_super_admin: isSuper,
      });
      onSaved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-mask" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-card">
        <header className="modal-head">
          <div><p className="page-kicker">Users</p><h2>编辑 {user.phone}</h2></div>
          <button type="button" className="modal-close" onClick={onClose}>×</button>
        </header>
        <form className="modal-form" onSubmit={submit}>
          <label className="field"><span>角色</span>
            <select value={role} onChange={(event) => setRole(event.target.value)}>
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </label>
          <label className="check-row"><input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} /> 账号启用</label>
          <label className="check-row"><input type="checkbox" checked={isSuper} onChange={(event) => setIsSuper(event.target.checked)} /> 超级管理员</label>
          {error ? <p className="form-error">{error}</p> : null}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onResetPassword}>重置密码</button>
            <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "保存中…" : "保存"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ==========================================================================
// 练习会话
// ==========================================================================

function SessionsPage({ notify }: { notify: Notify }) {
  const [data, setData] = useState<Paged<SessionRow> | null>(null);
  const [page, setPage] = useState(1);
  const [keywordInput, setKeywordInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [finished, setFinished] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [detailId, setDetailId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRefreshing(true);
    if (!data) setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (keyword) params.set("keyword", keyword);
    if (finished) params.set("finished", finished);
    adminGet<Paged<SessionRow>>(`/api/admin/sessions?${params.toString()}`)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
          setRefreshing(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [page, keyword, finished, refreshKey]);

  async function removeSession(row: SessionRow) {
    if (!window.confirm(`确定删除会话 #${row.id} 及其全部轮次/纠错吗？`)) return;
    try {
      await adminSend(`/api/admin/sessions/${row.id}`, "DELETE");
      notify("会话已删除");
      setRefreshKey((key) => key + 1);
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "删除失败", "error");
    }
  }

  const totalPages = data?.pages ?? 1;

  return (
    <section className="admin-page">
      <div className="page-head">
        <div>
          <p className="page-kicker">Sessions</p>
          <h2>练习会话</h2>
          <p className="page-desc">每次场景练习的完整对话与纠错记录。</p>
        </div>
      </div>

      <div className="table-toolbar">
        <form
          className="search-box"
          onSubmit={(event) => { event.preventDefault(); setPage(1); setKeyword(keywordInput.trim()); }}
        >
          <span className="search-icon" aria-hidden="true">⌕</span>
          <input value={keywordInput} onChange={(event) => setKeywordInput(event.target.value)} placeholder="按话题搜索" />
          <button type="submit" className="btn btn-soft">查询</button>
        </form>
        <div className="filter-row">
          <select value={finished} onChange={(event) => { setFinished(event.target.value); setPage(1); }}>
            <option value="">全部状态</option>
            <option value="true">已完成</option>
            <option value="false">进行中</option>
          </select>
          {refreshing ? (
            <span className="inline-loading">
              <span className="spinner" />
              更新中…
            </span>
          ) : null}
        </div>
      </div>

      <div className="admin-card table-card">
        <div className="table-scroll">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>场景</th>
                <th>话题</th>
                <th>开始时间</th>
                <th>结束时间</th>
                <th>轮次</th>
                <th>纠错</th>
                <th>得分</th>
                <th className="actions-col">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && !data ? (
                <tr><td colSpan={9} className="table-state"><span className="spinner" />加载中…</td></tr>
              ) : !data ? (
                <tr><td colSpan={9} className={error ? "table-state table-state-error" : "table-state"}>{error || "暂无会话"}</td></tr>
              ) : data.items.length === 0 ? (
                <tr><td colSpan={9} className="table-state">暂无会话</td></tr>
              ) : (
                data.items.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{scenarioName(row.scenario_id)}</td>
                    <td>{row.topic ?? "—"}</td>
                    <td>{formatTime(row.started_at)}</td>
                    <td>{formatTime(row.ended_at)}</td>
                    <td>{row.turn_count ?? 0}</td>
                    <td>{row.feedback_count ?? 0}</td>
                    <td>{row.overall_score ?? "—"}</td>
                    <td className="actions-col">
                      <button type="button" className="row-action" onClick={() => setDetailId(row.id)}>详情</button>
                      <button type="button" className="row-action row-action-danger" onClick={() => void removeSession(row)}>删除</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="table-pagination">
          <span>第 <strong>{data?.page ?? page}</strong> / {Math.max(totalPages, 1)} 页 · 共 <strong>{data?.total ?? 0}</strong> 条</span>
          <div>
            <button type="button" className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>上一页</button>
            <button type="button" className="btn btn-ghost" disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>下一页</button>
          </div>
        </div>
      </div>

      {detailId !== null ? <SessionDetailModal id={detailId} onClose={() => setDetailId(null)} /> : null}
    </section>
  );
}

function SessionDetailModal({ id, onClose }: { id: number; onClose: () => void }) {
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    adminGet<SessionDetail>(`/api/admin/sessions/${id}`)
      .then(setDetail)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "加载失败"));
  }, [id]);

  return (
    <div className="modal-mask" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-card modal-card-wide">
        <header className="modal-head">
          <div><p className="page-kicker">Session #{id}</p><h2>{detail?.topic ?? "会话详情"}</h2></div>
          <button type="button" className="modal-close" onClick={onClose}>×</button>
        </header>
        {error ? <p className="form-error">{error}</p> : null}
        {!detail ? (
          <div className="admin-loading"><span className="spinner" />加载中…</div>
        ) : (
          <div className="session-detail">
            <div className="session-meta">
              <span>场景：{scenarioName(detail.scenario_id)}</span>
              <span>轮次：{detail.turn_count ?? detail.turns.length}</span>
              <span>纠错：{detail.feedback_count ?? detail.feedback.length}</span>
              <span>得分：{detail.overall_score ?? "—"}</span>
            </div>
            <h3>对话轮次</h3>
            <div className="turn-list">
              {detail.turns.map((turn) => (
                <div className={`turn-item turn-${turn.speaker}`} key={turn.id}>
                  <span className="turn-who">{turn.speaker === "user" ? "用户" : "AI"}</span>
                  <p>{turn.text}</p>
                </div>
              ))}
            </div>
            <h3>纠错记录</h3>
            {detail.feedback.length === 0 ? (
              <p className="empty-inline">暂无纠错</p>
            ) : (
              <div className="feedback-list">
                {detail.feedback.map((item) => (
                  <div className="feedback-item" key={item.id}>
                    <span className={`badge badge-${badgeTone(item.feedback_type)}`}>{item.feedback_type}</span>
                    <p>{item.feedback_text || item.reason_zh || "—"}</p>
                    {item.better_expression ? <small>更好表达：{item.better_expression}</small> : null}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// 提示词
// ==========================================================================

function PromptsPage({ notify }: { notify: Notify }) {
  const [items, setItems] = useState<PromptItem[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<{ name: string; content: string; isNew: boolean } | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setRefreshing(true);
    if (items.length === 0) setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (keyword) params.set("keyword", keyword);
    adminGet<{ items: PromptItem[]; total: number }>(`/api/admin/prompts?${params.toString()}`)
      .then((result) => {
        if (!cancelled) setItems(result.items);
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
          setRefreshing(false);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyword, refreshKey]);

  async function openEdit(name: string) {
    try {
      const detail = await adminGet<{ name: string; content: string }>(`/api/admin/prompts/${encodeURIComponent(name)}`);
      setEditing({ name: detail.name, content: detail.content, isNew: false });
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : "读取失败", "error");
    }
  }

  return (
    <section className="admin-page">
      <div className="page-head">
        <div><p className="page-kicker">Prompts</p><h2>提示词配置</h2><p className="page-desc">Agent 各阶段的系统提示词，可直接在后台调参。</p></div>
        <button type="button" className="btn btn-primary" onClick={() => setEditing({ name: "", content: "", isNew: true })}>＋ 新增提示词</button>
      </div>

      <div className="table-toolbar">
        <form className="search-box" onSubmit={(event) => { event.preventDefault(); setKeyword(keywordInput.trim()); }}>
          <span className="search-icon" aria-hidden="true">⌕</span>
          <input value={keywordInput} onChange={(event) => setKeywordInput(event.target.value)} placeholder="按名称搜索" />
          <button type="submit" className="btn btn-soft">查询</button>
          {refreshing ? (
            <span className="inline-loading">
              <span className="spinner" />
              更新中…
            </span>
          ) : null}
        </form>
      </div>

      <div className="admin-card table-card">
        <div className="table-scroll">
          <table className="admin-table">
            <thead><tr><th>名称</th><th>内容长度</th><th>更新时间</th><th className="actions-col">操作</th></tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} className="table-state"><span className="spinner" />加载中…</td></tr>
              ) : error && items.length === 0 ? (
                <tr><td colSpan={4} className="table-state table-state-error">{error}</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={4} className="table-state">暂无提示词</td></tr>
              ) : (
                items.map((item) => (
                  <tr key={item.name}>
                    <td><strong>{item.name}</strong></td>
                    <td>{item.content_length} 字</td>
                    <td>{formatTime(item.updated_at)}</td>
                    <td className="actions-col"><button type="button" className="row-action" onClick={() => void openEdit(item.name)}>编辑</button></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {editing ? (
        <PromptModal
          editing={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); notify("提示词已保存"); setRefreshKey((key) => key + 1); }}
        />
      ) : null}
    </section>
  );
}

function PromptModal({
  editing,
  onClose,
  onSaved,
}: {
  editing: { name: string; content: string; isNew: boolean };
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(editing.name);
  const [content, setContent] = useState(editing.content);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) { setError("名称不能为空"); return; }
    if (!content.trim()) { setError("内容不能为空"); return; }
    setSaving(true);
    setError("");
    try {
      await adminSend(`/api/admin/prompts/${encodeURIComponent(name.trim())}`, "PUT", { content });
      onSaved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-mask" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-card modal-card-wide">
        <header className="modal-head">
          <div><p className="page-kicker">Prompts</p><h2>{editing.isNew ? "新增提示词" : `编辑 ${editing.name}`}</h2></div>
          <button type="button" className="modal-close" onClick={onClose}>×</button>
        </header>
        <form className="modal-form" onSubmit={submit}>
          <label className="field"><span>名称</span><input value={name} onChange={(event) => setName(event.target.value)} disabled={!editing.isNew} /></label>
          <label className="field"><span>内容</span><textarea className="code-area" rows={18} value={content} onChange={(event) => setContent(event.target.value)} /></label>
          {error ? <p className="form-error">{error}</p> : null}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "保存中…" : "保存"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ==========================================================================
// 趋势
// ==========================================================================

function TrendsPage({ notify }: { notify: Notify }) {
  const [days, setDays] = useState(14);
  const [data, setData] = useState<TrendsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    adminGet<TrendsData>(`/api/admin/trends/daily?days=${days}`)
      .then((result) => { if (!cancelled) setData(result); })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "加载失败"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [days]);

  if (loading && !data) return <div className="admin-loading"><span className="spinner" />正在加载趋势…</div>;
  if (!data) {
    return <div className="empty-state">{error || "暂无数据"}</div>;
  }

  const max = Math.max(1, ...data.timeline.flatMap((point) => [point.sessions, point.turns]));

  return (
    <section className="admin-page">
      <div className="page-head">
        <div><p className="page-kicker">Trends</p><h2>趋势分析</h2><p className="page-desc">按日统计练习会话、对话轮次、纠错与新用户。</p></div>
        <div className="trend-controls">
          <select value={days} onChange={(event) => setDays(Number(event.target.value))} className="select-inline">
            <option value={7}>最近 7 天</option>
            <option value={14}>最近 14 天</option>
            <option value={30}>最近 30 天</option>
          </select>
          {loading ? (
            <span className="inline-loading">
              <span className="spinner" />
              更新中…
            </span>
          ) : null}
        </div>
      </div>

      <div className="stat-grid">
        <article className="stat-card"><span>近 7 天会话</span><strong>{data.summary.sessions_recent}</strong><small>{data.summary.sessions_change_pct === null ? "暂无环比" : `${data.summary.sessions_change_pct > 0 ? "↑" : "↓"} ${Math.abs(data.summary.sessions_change_pct)}%`}</small></article>
        <article className="stat-card"><span>近 7 天轮次</span><strong>{data.summary.turns_recent}</strong><small>{data.summary.turns_change_pct === null ? "暂无环比" : `${data.summary.turns_change_pct > 0 ? "↑" : "↓"} ${Math.abs(data.summary.turns_change_pct)}%`}</small></article>
        <article className="stat-card"><span>统计天数</span><strong>{data.days}</strong><small>每日聚合</small></article>
      </div>

      <section className="admin-card panel">
        <div className="panel-head"><h3>每日会话 / 轮次</h3><div className="legend"><span className="legend-sessions">会话</span><span className="legend-turns">轮次</span></div></div>
        <div className="trend-chart">
          {data.timeline.map((point) => (
            <div className="trend-col" key={point.date}>
              <div className="trend-bars">
                <span className="trend-session" style={{ height: `${(point.sessions / max) * 100}%` }} title={`${point.date} 会话 ${point.sessions}`} />
                <span className="trend-turn" style={{ height: `${(point.turns / max) * 100}%` }} title={`${point.date} 轮次 ${point.turns}`} />
              </div>
              <small>{point.date.slice(5)}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="admin-card panel">
        <div className="panel-head"><h3>明细</h3><span>按日</span></div>
        <div className="table-scroll">
          <table className="admin-table compact">
            <thead><tr><th>日期</th><th>会话</th><th>轮次</th><th>纠错</th><th>新用户</th><th>平均分</th></tr></thead>
            <tbody>
              {data.timeline.slice().reverse().map((point) => (
                <tr key={point.date}>
                  <td>{point.date}</td>
                  <td>{point.sessions}</td>
                  <td>{point.turns}</td>
                  <td>{point.feedback}</td>
                  <td>{point.new_users}</td>
                  <td>{point.avg_score ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

// ==========================================================================
// 学习报告
// ==========================================================================

function ReportsPage({ notify }: { notify: Notify }) {
  const [data, setData] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    adminGet<ReportsData>("/api/admin/reports/overview")
      .then((result) => { if (!cancelled) setData(result); })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "加载失败"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="admin-loading"><span className="spinner" />正在加载报告…</div>;
  if (error || !data) {
    return <div className="empty-state">{error || "暂无数据"}</div>;
  }

  const scoreItems = [
    { label: "优秀 ≥ 90", count: data.score_distribution.excellent },
    { label: "良好 75–89", count: data.score_distribution.good },
    { label: "及格 60–74", count: data.score_distribution.pass },
    { label: "待提升 < 60", count: data.score_distribution.poor },
  ];

  return (
    <section className="admin-page">
      <div className="page-head">
        <div><p className="page-kicker">Reports</p><h2>学习报告</h2><p className="page-desc">错误类型、场景热度、水平分布与复习覆盖。</p></div>
        <span className="page-chip">复习覆盖率 {data.review_coverage.review_rate}%</span>
      </div>

      <div className="report-grid">
        <BarList title="错误类型分布" items={data.error_type_distribution.map((item) => ({ label: item.error_type, count: item.count }))} />
        <BarList title="反馈类型分布" items={data.feedback_type_distribution.map((item) => ({ label: item.feedback_type, count: item.count }))} />
        <BarList title="严重程度" items={data.severity_distribution.map((item) => ({ label: item.severity, count: item.count }))} />
        <BarList title="热门场景" items={data.hot_scenarios.map((item) => ({ label: scenarioName(item.scenario_id), count: item.count, extra: item.avg_score !== null ? `均分 ${item.avg_score}` : undefined }))} />
        <BarList title="水平分布" items={data.level_distribution.map((item) => ({ label: item.level ?? "未知", count: item.count }))} />
        <BarList title="分数分档" items={scoreItems} />
      </div>

      <section className="admin-card panel">
        <div className="panel-head"><h3>复习覆盖</h3><span>错题本</span></div>
        <div className="coverage-row">
          <div><strong>{data.review_coverage.reviewed_errors}</strong><span>已复习</span></div>
          <div><strong>{data.review_coverage.total_errors}</strong><span>错题总数</span></div>
          <div><strong>{data.review_coverage.review_rate}%</strong><span>覆盖率</span></div>
        </div>
      </section>
    </section>
  );
}

function BarList({ title, items }: { title: string; items: Array<{ label: string; count: number; extra?: string }> }) {
  const max = Math.max(1, ...items.map((item) => item.count));
  return (
    <section className="admin-card panel">
      <div className="panel-head"><h3>{title}</h3><span>{items.length} 项</span></div>
      {items.length === 0 ? (
        <p className="empty-inline">暂无数据</p>
      ) : (
        <div className="bar-list">
          {items.map((item) => (
            <div className="bar-row" key={item.label}>
              <span className="bar-label" title={item.label}>{item.label}</span>
              <span className="bar-track"><span style={{ width: `${(item.count / max) * 100}%` }} /></span>
              <strong>{item.count}</strong>
              {item.extra ? <small>{item.extra}</small> : null}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
