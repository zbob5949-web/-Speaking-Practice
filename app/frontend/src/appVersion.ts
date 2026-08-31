/** App 当前版本（构建时通过 VITE_APP_VERSION_CODE / VITE_APP_VERSION_NAME 注入） */
export const APP_VERSION_CODE = Number(import.meta.env.VITE_APP_VERSION_CODE ?? 1);
export const APP_VERSION_NAME = String(import.meta.env.VITE_APP_VERSION_NAME ?? "1.0");
