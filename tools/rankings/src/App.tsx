import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import ModelDetail from "@/pages/ModelDetail";
import { useThemeStore } from '@/store/useThemeStore';

// Base path for deployment (matches vite base config)
const BASE_PATH = import.meta.env.BASE_URL;

export default function App() {
  const { theme } = useThemeStore();

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.body.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  return (
    <Router basename={BASE_PATH}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/model/:id" element={<ModelDetail />} />
      </Routes>
    </Router>
  );
}
