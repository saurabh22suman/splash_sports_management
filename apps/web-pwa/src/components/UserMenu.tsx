import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@splashh/api-client";
import { useLogout } from "@/features/auth/useLogout";

function useClickOutside(ref: React.RefObject<HTMLElement>, onClose: () => void) {
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [ref, onClose]);
}

function useEscapeKey(onClose: () => void) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);
}

export function UserMenu() {
  const userId = useAuthStore((s) => s.userId);
  const initials = (userId ?? "?").slice(0, 1).toUpperCase();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false));
  useEscapeKey(() => setOpen(false));
  const logout = useLogout();

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="Open account menu"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 p-2 rounded hover:bg-slate-100"
      >
        <span
          aria-hidden
          className="w-7 h-7 rounded-full bg-gradient-to-br from-sky-500 to-cyan-500 text-white text-xs font-semibold flex items-center justify-center"
        >
          {initials}
        </span>
        <span className="text-sm text-slate-700">Account</span>
      </button>
      {open && (
        <div
          role="menu"
          className="absolute bottom-full left-0 mb-1 w-44 bg-white rounded-lg shadow-xl border border-slate-200 py-1"
        >
          <button
            role="menuitem"
            type="button"
            onClick={() => {
              setOpen(false);
              logout.mutate();
            }}
            className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50"
          >
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
