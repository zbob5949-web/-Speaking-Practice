import ReactDOM from "react-dom/client";
import AdminApp from "./AdminApp";

const root = document.getElementById("root");
if (!root) throw new Error("缺少 #root 挂载点");

ReactDOM.createRoot(root).render(<AdminApp />);
