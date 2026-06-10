import { useState } from "react";
import { useTickets, useAgents } from "../lib/tickets";
import api from "../lib/api";
import { useQuery } from "@tanstack/react-query";
import TicketTable from "../components/TicketTable";
import Filters from "../components/Filters";
import Pagination from "../components/Pagination";
import { Spinner, ErrorBox } from "../components/ui";

function Stat({ value, label }) {
  return (
    <div className="card px-5 py-4">
      <div className="font-display text-3xl tracking-tight text-ink tabular-nums">{value}</div>
      <div className="mt-0.5 text-xs uppercase tracking-wider text-ink-muted">{label}</div>
    </div>
  );
}

function AnalyticsBar() {
  const { data } = useQuery({
    queryKey: ["analytics"],
    queryFn: async () => (await api.get("/analytics/summary")).data,
  });
  if (!data) return null;
  return (
    <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Stat value={data.open} label="Open" />
      <Stat value={data.in_progress} label="In progress" />
      <Stat value={data.resolved} label="Resolved" />
      <Stat value={data.avg_resolution_hours ?? "—"} label="Avg hrs to resolve" />
    </div>
  );
}

export default function AgentDashboard() {
  const [filters, setFilters] = useState({ page: 1 });
  const params = { ...filters, page_size: 10 };
  Object.keys(params).forEach((k) => params[k] === "" && delete params[k]);
  const { data, isLoading, isError } = useTickets(params);
  const { data: agents } = useAgents(true);

  return (
    <div className="animate-rise">
      <div className="mb-6">
        <h1 className="font-display text-3xl tracking-tight text-ink">All tickets</h1>
        <p className="mt-1 text-sm text-ink-muted">Triage, assign, and resolve incoming support requests.</p>
      </div>

      <AnalyticsBar />
      <Filters value={filters} onChange={setFilters} agents={agents || []} />

      {isLoading ? (
        <div className="flex justify-center p-16"><Spinner /></div>
      ) : isError ? (
        <ErrorBox message="Failed to load tickets" />
      ) : (
        <>
          <TicketTable tickets={data.items} />
          <Pagination
            page={filters.page || 1}
            pageSize={data.page_size}
            total={data.total}
            onPage={(p) => setFilters({ ...filters, page: p })}
          />
        </>
      )}
    </div>
  );
}
