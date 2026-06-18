import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({ title, subtitle, actions, className }: PageHeaderProps) {
  return (
    <header
      className={cn(
        "px-6 md:px-10 pt-8 pb-6 border-b border-obs-border/60",
        className
      )}
    >
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.2em] text-cyan/70 mb-2">
            <span className="w-6 h-px bg-cyan/50" />
            <span>TokenLab Observatory</span>
          </div>
          <h1 className="font-display font-bold text-2xl md:text-3xl text-ink tracking-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-2 text-sm text-ink-muted max-w-2xl">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
}
