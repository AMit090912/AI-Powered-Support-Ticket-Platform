import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const initial = user?.full_name?.[0]?.toUpperCase() || "?";

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-paper/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink font-display text-base leading-none text-paper">
              S
            </span>
            <span className="font-display text-lg tracking-tight text-ink">Support Desk</span>
          </Link>

          {user && (
            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2.5 rounded-full border border-line bg-surface py-1 pl-1 pr-3 shadow-soft sm:flex">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-ink/90 text-[11px] font-semibold text-paper">
                  {initial}
                </span>
                <span className="text-sm text-ink-soft">{user.full_name}</span>
                <span className="rounded-full bg-paper px-2 py-0.5 text-[10px] uppercase tracking-wider text-ink-muted">
                  {user.role}
                </span>
              </div>
              <button onClick={() => { logout(); nav("/login"); }} className="btn-ghost">
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
    </div>
  );
}
