import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ErrorBox } from "../components/ui";
import AuthLayout from "../components/AuthLayout";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const user = await login(email, password);
      nav(user.role === "agent" ? "/agent" : "/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally { setLoading(false); }
  };

  return (
    <AuthLayout>
      <div className="mb-8 flex items-center gap-2.5 md:hidden">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink font-display text-paper">S</span>
        <span className="font-display text-lg tracking-tight">Support Desk</span>
      </div>

      <h1 className="font-display text-3xl tracking-tight text-ink">Welcome back</h1>
      <p className="mt-1.5 text-sm text-ink-muted">Sign in to your account to continue.</p>

      <form onSubmit={submit} className="mt-7 space-y-4">
        {error && <ErrorBox message={error} />}
        <div className="space-y-1.5">
          <label className="label">Email</label>
          <input className="field" type="email" placeholder="you@company.com"
                 value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="space-y-1.5">
          <label className="label">Password</label>
          <input className="field" type="password" placeholder="••••••••"
                 value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button disabled={loading} className="btn-primary w-full">
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-sm text-ink-muted">
        No account?{" "}
        <Link to="/register" className="font-medium text-ink decoration-ink/30 underline underline-offset-4 hover:decoration-ink">
          Create one
        </Link>
      </p>
    </AuthLayout>
  );
}
