import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import Calculator from "@/pages/Calculator";
import Models from "@/pages/Models";
import HistoryPage from "@/pages/History";

export default function App() {
  return (
    <Router>
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
