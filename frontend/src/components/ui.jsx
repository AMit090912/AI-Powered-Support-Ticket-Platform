export function Spinner() {
  return <div className="h-6 w-6 animate-spin rounded-full border-2 border-ink/15 border-t-ink/70" />;
}

export function ErrorBox({ message }) {
  return (
    <div className="rounded-lg border border-[#E4CCC3] bg-[#F6EBE6] px-3.5 py-2.5 text-sm text-[#8C4A3C]">
      {message}
    </div>
  );
}

export function EmptyState({ children }) {
  return <div className="py-14 text-center text-sm text-ink-muted">{children}</div>;
}

// Desaturated, warm-leaning status/priority palette — calm, never neon.
const COLORS = {
  open: "bg-[#E9EEF1] text-[#3C5662]",
  in_progress: "bg-[#F2ECDD] text-[#7A6220]",
  resolved: "bg-[#E7EEE7] text-[#3F5F46]",
  closed: "bg-[#EBE7DF] text-[#6E665B]",
  low: "bg-[#ECEAE3] text-[#6E665B]",
  medium: "bg-[#E9EEF1] text-[#3C5662]",
  high: "bg-[#F4E9DC] text-[#8A5A2B]",
  critical: "bg-[#F1E0DA] text-[#8C4A3C]",
};

export function Badge({ value }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
        COLORS[value] || "bg-[#ECEAE3] text-ink-soft"
      }`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {value?.replace("_", " ")}
    </span>
  );
}
