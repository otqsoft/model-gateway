import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

export function Card({ className, hover = false, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "bg-obs-card border border-obs-border rounded-xl shadow-card",
        hover && "card-hover",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  subtitle?: ReactNode;
  className?: string;
}

export function CardHeader({ title, icon, action, subtitle, className }: CardHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 px-5 py-4 border-b border-obs-border",
        className
      )}
    >
      <div className="flex items-center gap-3 min-w-0">
        {icon && (
          <div className="w-9 h-9 rounded-lg bg-obs-cardHi border border-obs-border flex items-center justify-center text-cyan shrink-0">
            {icon}
          </div>
        )}
        <div className="min-w-0">
          <div className="font-display font-semibold text-ink text-sm tracking-wide truncate">
            {title}
          </div>
          {subtitle && (
            <div className="text-xs text-ink-dim mt-0.5 truncate">{subtitle}</div>
          )}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
