import { Link } from "react-router-dom";
import { Badge, EmptyState } from "./ui";

export default function TicketTable({ tickets }) {
  if (!tickets.length)
    return (
      <div className="card">
        <EmptyState>No tickets found.</EmptyState>
      </div>
    );

  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[11px] uppercase tracking-wider text-ink-muted">
            <th className="px-5 py-3 font-medium">Ticket</th>
            <th className="px-3 py-3 font-medium">Status</th>
            <th className="px-3 py-3 font-medium">Priority</th>
            <th className="px-3 py-3 font-medium">Category</th>
            <th className="px-5 py-3 font-medium">Assignee</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line/70">
          {tickets.map((t) => (
            <tr key={t.id} className="group transition-colors hover:bg-paper/70">
              <td className="px-5 py-4">
                <Link to={`/tickets/${t.id}`} className="flex items-baseline gap-2 font-medium text-ink">
                  <span className="text-xs tabular-nums text-ink-faint">#{t.id}</span>
                  <span className="decoration-ink/25 underline-offset-4 group-hover:underline">{t.title}</span>
                </Link>
              </td>
              <td className="px-3 py-4"><Badge value={t.status} /></td>
              <td className="px-3 py-4"><Badge value={t.priority} /></td>
              <td className="px-3 py-4 capitalize text-ink-muted">{t.category.replace("_", " ")}</td>
              <td className="px-5 py-4 text-ink-soft">
                {t.assigned_to?.full_name || <span className="text-ink-faint">Unassigned</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
