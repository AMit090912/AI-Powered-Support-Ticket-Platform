const STATUS = ["", "open", "in_progress", "resolved", "closed"];
const PRIORITY = ["", "low", "medium", "high", "critical"];
const CATEGORY = ["", "billing", "technical", "account_access", "feature_request", "general"];

export default function Filters({ value, onChange, agents = [] }) {
  const set = (k) => (e) => onChange({ ...value, [k]: e.target.value, page: 1 });
  return (
    <div className="mb-5 flex flex-wrap items-center gap-2.5">
      <div className="relative min-w-[220px] flex-1">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint"
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          className="field pl-9"
          placeholder="Search title or description…"
          value={value.q || ""}
          onChange={set("q")}
        />
      </div>
      <select className="field w-auto" value={value.status || ""} onChange={set("status")}>
        {STATUS.map((s) => (
          <option key={s} value={s}>{s ? s.replace("_", " ") : "All statuses"}</option>
        ))}
      </select>
      <select className="field w-auto" value={value.priority || ""} onChange={set("priority")}>
        {PRIORITY.map((s) => (
          <option key={s} value={s}>{s || "All priorities"}</option>
        ))}
      </select>
      <select className="field w-auto" value={value.category || ""} onChange={set("category")}>
        {CATEGORY.map((s) => (
          <option key={s} value={s}>{s ? s.replace("_", " ") : "All categories"}</option>
        ))}
      </select>
      <select className="field w-auto" value={value.assignee_id || ""} onChange={set("assignee_id")}>
        <option value="">All assignees</option>
        {agents.map((a) => (
          <option key={a.id} value={a.id}>{a.full_name}</option>
        ))}
      </select>
    </div>
  );
}
