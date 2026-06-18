import { useEffect, type ReactNode } from "react";
import { MobileNav, Sidebar } from "./Sidebar";
import { useModelStore } from "@/store/useModelStore";
import { useHistoryStore } from "@/store/useHistoryStore";
import { useSettingsStore } from "@/store/useSettingsStore";

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const initModels = useModelStore((s) => s.init);
  const initHistory = useHistoryStore((s) => s.init);
  const initSettings = useSettingsStore((s) => s.init);

  useEffect(() => {
    initModels();
    initHistory();
    initSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-full min-h-0">
      <Sidebar />
      <main className="flex-1 min-w-0 overflow-y-auto pb-20 md:pb-0">
        {children}
      </main>
      <MobileNav />
    </div>
  );
}
