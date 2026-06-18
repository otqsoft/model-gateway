import type { ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  size?: "md" | "lg";
}

export function Modal({ open, onClose, title, children, footer, size = "md" }: ModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-obs-bg/80 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className={cn(
          "relative bg-obs-panel border border-obs-border rounded-2xl shadow-card w-full max-h-[90vh] flex flex-col",
          size === "lg" ? "max-w-3xl" : "max-w-lg"
        )}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-obs-border">
          <h3 className="font-display font-semibold text-ink text-base">{title}</h3>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-ink-dim hover:text-ink hover:bg-obs-cardHi transition-colors"
          >
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-obs-border">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
