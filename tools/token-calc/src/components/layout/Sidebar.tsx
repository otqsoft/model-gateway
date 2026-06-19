import { NavLink } from "react-router-dom";
import { Calculator, Cpu, History, Telescope } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "计算工作台", icon: Calculator, desc: "Calculator" },
  { to: "/models", label: "模型管理", icon: Cpu, desc: "Models" },
  { to: "/history", label: "历史记录", icon: History, desc: "History" },
];

export function Sidebar() {
  return (
    <aside className="hidden md:flex flex-col w-60 shrink-0 border-r border-obs-border bg-obs-panel/60 backdrop-blur-sm">
      {/* Logo 区 */}
      <div className="px-5 py-6 border-b border-obs-border">
        <div className="flex items-center gap-3">
          <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-cyan/20 to-amber/10 border border-cyan/30 flex items-center justify-center shadow-glow">
            <Telescope size={20} className="text-cyan" />
            {/* <div className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-cyan animate-pulse-glow" /> */}
          </div>
          <div>
            <div className="font-display font-bold text-ink text-base leading-tight">
              TokenLab
            </div>
            <div className="text-[10px] text-ink-dim font-mono tracking-wider uppercase">
              v1.0 · Observatory
            </div>
          </div>
        </div>
      </div>

      {/* 导航 */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {/* <div className="px-3 pb-2 text-[10px] font-mono uppercase tracking-wider text-ink-dim">
          Navigation
        </div> */}
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "group flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 relative",
                  isActive
                    ? "bg-cyan/10 text-cyan border border-cyan/30"
                    : "text-ink-muted hover:text-ink hover:bg-obs-cardHi border border-transparent"
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-cyan rounded-r-full shadow-glow" />
                  )}
                  <Icon size={18} className="shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium leading-tight">{item.label}</div>
                    <div className="text-[10px] font-mono text-ink-dim group-hover:text-ink-muted">
                      {item.desc}
                    </div>
                  </div>
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* 底部状态 */}
      <div className="px-5 py-4 border-t border-obs-border">
        <div className="flex items-center gap-2 text-[10px] font-mono text-ink-dim">
          <span className="w-1.5 h-1.5 rounded-full bg-ok animate-pulse-glow" />
          <span>TokenLab Observatory</span>
        </div>
        <div className="mt-1 text-[10px] text-ink-dim/70">
          Token 计算器 · 出品：Q-Quick
        </div>
      </div>
    </aside>
  );
}

export function MobileNav() {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-obs-panel/95 backdrop-blur-md border-t border-obs-border flex">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex-1 flex flex-col items-center gap-1 py-2.5 text-[10px] font-mono transition-colors",
                isActive ? "text-cyan" : "text-ink-dim"
              )
            }
          >
            <Icon size={18} />
            <span>{item.desc}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
