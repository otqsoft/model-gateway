import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import Calculator from "@/pages/Calculator";
import Models from "@/pages/Models";
import HistoryPage from "@/pages/History";

// 从当前 URL 提取部署目录作为 basename，如 /token-lab
const getBasename = () => {
  const path = window.location.pathname;
  const parts = path.split("/");
  // 路径格式: /{部署目录}/{路由路径}，取第一段非空部分
  return parts.length > 1 ? `/${parts[1]}` : "/";
};

export default function App() {
  return (
    <Router basename={getBasename()}>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Calculator />} />
          <Route path="/models" element={<Models />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </AppLayout>
    </Router>
  );
}
