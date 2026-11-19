import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
import { installDragScroll } from "./dragScroll";

// 隐藏滚动条后仍要能用滚轮 / 按住左键拖动来滚动
installDragScroll();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
