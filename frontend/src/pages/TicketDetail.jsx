import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import {
  useTicket, useUpdateTicket, useComments, useAddComment, useActivity, useAgents,
} from "../lib/tickets";
import { Badge, Spinner, ErrorBox, EmptyState } from "../components/ui";

const STATUS = ["open", "in_progress", "resolved", "closed"];
const PRIORITY = ["low", "medium", "high", "critical"];

function Initial({ name }) {
  return (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ink/90 text-[11px] font-semibold text-paper">
      {name?.[0]?.toUpperCase() || "?"}
    </span>
  );
}

export default function TicketDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAgent = user?.role === "agent";
  const { data: ticket, isLoading, isError } = useTicket(id);
  const update = useUpdateTicket(id);
  const { data: comments } = useComments(id);
  const addComment = useAddComment(id);
  const { data: activity } = useActivity(id);
  const { data: agents } = useAgents(isAgent);
  const [body, setBody] = useState("");

  if (isLoading) return <div className="flex justify-center p-16"><Spinner /></div>;
  if (isError) return <ErrorBox message="Failed to load ticket" />;

  const submitComment = async (e) => {
    e.preventDefault();
    if (!body.trim()) return;
    await addComment.mutateAsync(body);
    setBody("");
  };

  return (
    <div className="animate-rise">
      <Link
        to={isAgent ? "/agent" : "/dashboard"}
        className="mb-5 inline-flex items-center gap-1.5 text-sm text-ink-muted transition hover:text-ink"
      >
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m15 18-6-6 6-6" />
        </svg>
        Back to tickets
      </Link>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="space-y-6 md:col-span-2">
          {/* Header */}
          <div className="card p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge value={ticket.status} />
              <Badge value={ticket.priority} />
              <span className="text-xs capitalize text-ink-muted">· {ticket.category.replace("_", " ")}</span>
            </div>
            <h1 className="mt-3 font-display text-2xl leading-snug tracking-tight text-ink">{ticket.title}</h1>
            <p className="mt-3 whitespace-pre-wrap leading-relaxed text-ink-soft">{ticket.description}</p>
            <div className="mt-5 flex items-center gap-2 border-t border-line pt-4 text-xs text-ink-muted">
              <Initial name={ticket.created_by.full_name} />
              <span>Opened by <span className="text-ink-soft">{ticket.created_by.full_name}</span></span>
              <span className="text-ink-faint">·</span>
              <span>{new Date(ticket.created_at).toLocaleString()}</span>
            </div>
          </div>

          {/* AI suggested response — the focal, dark card (agents only) */}
          {isAgent && ticket.suggested_response && (
            <div className="relative overflow-hidden rounded-2xl bg-ink p-6 text-paper shadow-pop">
              <div
                aria-hidden
                className="absolute inset-0 opacity-[0.06]"
                style={{ backgroundImage: "radial-gradient(circle at 85% 15%, #fff 0, transparent 40%)" }}
              />
              <div className="relative">
                <p className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-paper/60">
                  <span className="rounded-full bg-paper px-1.5 py-0.5 text-[10px] font-semibold text-ink">AI</span>
                  Suggested response
                </p>
                <p className="leading-relaxed text-paper/90">{ticket.suggested_response}</p>
              </div>
            </div>
          )}

          {/* Comments */}
          <div className="card p-6">
            <h2 className="mb-4 font-display text-lg tracking-tight text-ink">Comments</h2>
            <div className="space-y-4">
              {comments?.length ? comments.map((c) => (
                <div key={c.id} className="flex gap-3">
                  <Initial name={c.author.full_name} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm leading-relaxed text-ink-soft">{c.body}</p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {c.author.full_name} · {new Date(c.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              )) : <EmptyState>No comments yet.</EmptyState>}
            </div>
            <form onSubmit={submitComment} className="mt-5 flex gap-2 border-t border-line pt-4">
              <input className="field" placeholder="Add a comment…"
                     value={body} onChange={(e) => setBody(e.target.value)} />
              <button disabled={addComment.isPending} className="btn-primary shrink-0">Send</button>
            </form>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {isAgent && (
            <div className="card space-y-4 p-6">
              <h2 className="font-display text-lg tracking-tight text-ink">Manage</h2>
              <div className="space-y-1.5">
                <label className="label">Status</label>
                <select className="field" value={ticket.status}
                        onChange={(e) => update.mutate({ status: e.target.value })}>
                  {STATUS.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="label">Priority</label>
                <select className="field" value={ticket.priority}
                        onChange={(e) => update.mutate({ priority: e.target.value })}>
                  {PRIORITY.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="label">Assignee</label>
                <select className="field" value={ticket.assigned_to?.id || ""}
                        onChange={(e) => update.mutate({ assigned_to_id: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">Unassigned</option>
                  {agents?.map((a) => <option key={a.id} value={a.id}>{a.full_name}</option>)}
                </select>
              </div>
              {update.isError && <ErrorBox message="Update failed" />}
            </div>
          )}

          {/* Activity timeline */}
          <div className="card p-6">
            <h2 className="mb-4 font-display text-lg tracking-tight text-ink">Activity</h2>
            {activity?.length ? (
              <ol className="relative space-y-4 border-l border-line pl-5">
                {activity.map((e) => (
                  <li key={e.id} className="relative">
                    <span className="absolute -left-[1.43rem] top-1.5 h-2 w-2 rounded-full bg-ink/30 ring-4 ring-surface" />
                    <p className="text-sm text-ink-soft">
                      <span className="font-medium capitalize text-ink">{e.event_type.replace("_", " ")}</span>
                      {e.old_value && <> from <span className="italic">{e.old_value}</span></>}
                      {e.new_value && <> to <span className="italic">{e.new_value}</span></>}
                      {e.actor && <span className="text-ink-muted"> · {e.actor.full_name}</span>}
                    </p>
                    <p className="mt-0.5 text-xs text-ink-faint">{new Date(e.created_at).toLocaleString()}</p>
                  </li>
                ))}
              </ol>
            ) : <EmptyState>No activity.</EmptyState>}
          </div>
        </div>
      </div>
    </div>
  );
}
