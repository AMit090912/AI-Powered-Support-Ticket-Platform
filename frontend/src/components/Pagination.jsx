export default function Pagination({ page, pageSize, total, onPage }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="mt-5 flex items-center justify-between text-sm text-ink-muted">
      <span className="tabular-nums">
        {total} ticket{total === 1 ? "" : "s"}
      </span>
      <div className="flex items-center gap-2">
        <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="btn-ghost">
          Prev
        </button>
        <span className="px-1 tabular-nums">
          Page {page} / {pages}
        </span>
        <button disabled={page >= pages} onClick={() => onPage(page + 1)} className="btn-ghost">
          Next
        </button>
      </div>
    </div>
  );
}
