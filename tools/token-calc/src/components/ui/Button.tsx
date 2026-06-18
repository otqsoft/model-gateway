import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  icon?: ReactNode;
}

export function Button({
  variant = "secondary",
  size = "md",
  icon,
  className,
  children,
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed select-none";
  const sizes = {
    sm: "text-xs px-3 py-1.5 h-8",
    md: "text-sm px-4 py-2 h-10",
    lg: "text-base px-5 py-2.5 h-12",
  };
  const variants = {
    primary:
      "bg-cyan text-obs-bg font-semibold hover:bg-cyan-glow hover:shadow-glow active:scale-[0.98]",
    secondary:
      "bg-obs-cardHi text-ink border border-obs-border hover:border-obs-borderHi hover:bg-obs-card active:scale-[0.98]",
    ghost: "text-ink-muted hover:text-ink hover:bg-obs-cardHi",
    danger:
      "bg-warn/10 text-warn border border-warn/30 hover:bg-warn/20 hover:border-warn/50",
  };

  return (
    <button
      className={cn(base, sizes[size], variants[variant], className)}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
