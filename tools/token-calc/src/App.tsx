import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import Calculator from "@/pages/Calculator";
import Models from "@/pages/Models";
import HistoryPage from "@/pages/History";

export default function App() {
  return (
    <Router basename="/token-lab">
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
