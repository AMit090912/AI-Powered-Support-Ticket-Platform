import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ErrorBox } from "../components/ui";
import AuthLayout from "../components/AuthLayout";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "customer" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const user = await register(form);
      nav(user.role === "agent" ? "/agent" : "/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally { setLoading(false); }
  };

  return (
    <AuthLayout>
      <div className="mb-8 flex items-center gap-2.5 md:hidden">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink font-display text-paper">S</span>
        <span className="font-display text-lg tracking-tight">Support Desk</span>
      </div>

      <h1 className="font-display text-3xl tracking-tight text-ink">Create your account</h1>
      <p className="mt-1.5 text-sm text-ink-muted">Start creating and resolving tickets in minutes.</p>

      <form onSubmit={submit} className="mt-7 space-y-4">
        {error && <ErrorBox message={error} />}
        <div className="space-y-1.5">
          <label className="label">Full name</label>
          <input className="field" placeholder="Jane Cooper"
                 value={form.full_name} onChange={set("full_name")} required />
        </div>
        <div className="space-y-1.5">
          <label className="label">Email</label>
          <input className="field" type="email" placeholder="you@company.com"
                 value={form.email} onChange={set("email")} required />
        </div>
        <div className="space-y-1.5">
          <label className="label">Password</label>
          <input className="field" type="password" placeholder="At least 6 characters"
                 value={form.password} onChange={set("password")} required minLength={6} />
        </div>
        <div className="space-y-1.5">
          <label className="label">I am a</label>
          <select className="field" value={form.role} onChange={set("role")}>
            <option value="customer">Customer — I want to raise tickets</option>
            <option value="agent">Support Agent — I resolve tickets</option>
          </select>
        </div>
        <button disabled={loading} className="btn-primary w-full">
          {loading ? "Creating…" : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-sm text-ink-muted">
        Have an account?{" "}
        <Link to="/login" className="font-medium text-ink decoration-ink/30 underline underline-offset-4 hover:decoration-ink">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
