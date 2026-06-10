import { useState } from "react";
import { useTickets, useCreateTicket } from "../lib/tickets";
import TicketTable from "../components/TicketTable";
import Pagination from "../components/Pagination";
import { Spinner, ErrorBox } from "../components/ui";

export default function CustomerDashboard() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useTickets({ page, page_size: 10 });
  const create = useCreateTicket();
  const [form, setForm] = useState({ title: "", description: "" });
  const [open, setOpen] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    await create.mutateAsync(form);
    setForm({ title: "", description: "" });
    setOpen(false);
  };

  return (
    <div className="animate-rise">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl tracking-tight text-ink">My tickets</h1>
          <p className="mt-1 text-sm text-ink-muted">Track your support requests and their progress.</p>
        </div>
        <button onClick={() => setOpen(!open)} className={open ? "btn-ghost" : "btn-primary"}>
          {open ? "Cancel" : (
            <>
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M12 5v14M5 12h14" />
              </svg>
              New ticket
            </>
          )}
        </button>
      </div>

      {open && (
        <form onSubmit={submit} className="card mb-6 space-y-4 p-5">
          {create.isError && (
            <ErrorBox message={create.error?.response?.data?.detail || "Failed to create ticket"} />
          )}
          <div className="space-y-1.5">
            <label className="label">Title</label>
            <input className="field" placeholder="Brief summary of the issue" required
                   value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <label className="label">Description</label>
            <textarea className="field" placeholder="Describe what's happening…" rows={4} required
                      value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="flex items-center justify-between gap-3">
            <p className="flex items-center gap-1.5 text-xs text-ink-muted">
              <span className="rounded-full bg-ink px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-paper">AI</span>
              Category &amp; priority are assigned automatically.
            </p>
            <button disabled={create.isPending} className="btn-primary">
              {create.isPending ? "Submitting…" : "Submit ticket"}
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="flex justify-center p-16"><Spinner /></div>
      ) : isError ? (
        <ErrorBox message="Failed to load tickets" />
      ) : (
        <>
          <TicketTable tickets={data.items} />
          <Pagination page={page} pageSize={data.page_size} total={data.total} onPage={setPage} />
        </>
      )}
    </div>
  );
}
