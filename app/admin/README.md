# SpeakMate 管理后台前端

React 18 + Vite + TypeScript 构建的管理后台，界面为浅灰底 + 白卡 + 荧光绿强调，
包含概览、用户管理、练习会话、提示词、趋势、学习报告与 15 张通用数据表。

## 目录

```text
SpeakMate管理员前端/
├── admin/          源码
│   ├── src/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── admin-dist/     已构建的生产产物（可直接部署）
└── README.md
```

## 直接部署

把 `admin-dist/` 放到后端项目：

```text
app/frontend/admin-dist/
```

后端 `app/backend/app/main.py` 已挂载：

```python
ADMIN_DIST = ... / "app" / "frontend" / "admin-dist"
app.mount("/admin-ui", StaticFiles(directory=ADMIN_DIST, html=True))
```

启动后端后访问：

```text
http://localhost:8000/admin-ui/
```

`http://localhost:8000/admin` 会自动跳转到 `/admin-ui/`。

管理员账号使用后端脚本创建：

```bash
python tools/create_admin.py <手机号> <密码> --super
```

登录请求走现有 `POST /api/auth/login`，管理接口走 `/api/admin/*`，
与学员端共用同一后端和 SQLite 数据库。

## 自行构建

```bash
cd admin
npm install
npm run build
```

构建产物输出到上一级的 `admin-dist/`。

注意：`vite.config.ts` 里的 `base` 是 `/admin-ui/`。
如果要部署到其他路径，需要同步修改 `base` 与后端挂载路径。

## 技术说明

- 所有接口同源，不需要配置 CORS 或 API 域名
- 登录 token 存于 `localStorage` 的 `speakmate-admin-token`
- 管理端权限由后端根据 `users.role` / `users.is_super_admin` 判定
- 数据表字段由 `/api/admin/tables` 的列元信息动态渲染
- 列表刷新采用“保留旧数据 + 工具栏轻量加载”，状态开关为乐观更新
