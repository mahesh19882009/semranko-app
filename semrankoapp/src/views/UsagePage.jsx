'use client'
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";
import { getLedgerHistoryApi } from "../features/pricing/pricingApi";
import { useSelector } from "react-redux";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Alert from "../components/ui/Alert";
import { useToast } from "../components/ui/Toast";
import { formatDateTime } from "../utils/date";
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';

const ACTION_DISPLAY = {
  "Added New Keyword to Tracker": "Added New Keyword to Tracker",
  "Automated Monday Weekly Update": "Automated Monday Weekly Update",
  "Keyword Research Lookup": "Keyword Research Lookup",
  "Competitor Domain Spy Check": "Competitor Domain Spy Check",
  "Created Extra Multi-Domain Project": "Created Extra Multi-Domain Project",
  "Exported Premium CSV Data Report": "Exported Premium CSV Data Report",
  "Purchased Credit Top-Up": "Purchased Credit Top-Up",
};

function formatCredits(displayAmount, color) {
  if (!displayAmount && displayAmount !== "0") return "—";
  const numeric = parseFloat(displayAmount);
  if (Number.isNaN(numeric)) return displayAmount;
  const prefix = numeric > 0 ? "+" : "";
  const tone = numeric > 0 ? "text-emerald-600" : numeric < 0 ? "text-red-600" : "text-slate-600";
  return (
    <span className={`font-semibold ${tone}`}>
      {prefix}{numeric.toLocaleString("en-US")} Credits
    </span>
  );
}

export default function UsagePage() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();
  const { addToast } = useToast();

  const pricingCurrent = useSelector((state) => state.pricing.current);
  const spendableCredits = pricingCurrent?.spendableCreditsRemaining ?? null;
  const lastCreditResetAt = pricingCurrent?.lastCreditResetAt ?? null;
  const nextCreditResetAt = pricingCurrent?.nextCreditResetAt ?? null;

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!authenticated) {
      navigate("/login");
      return;
    }
  }, [authenticated]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getLedgerHistoryApi(page, 20)
      .then((data) => {
        if (!cancelled) {
          setItems(data?.items || []);
          setTotal(data?.total || 0);
          setTotalPages(data?.total_pages || 1);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Failed to load credit ledger");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [page]);

  const renderTableBody = () => {
    if (loading) {
      return (
        <tbody className="divide-y divide-slate-100">
          {[1, 2, 3, 4, 5].map((i) => (
            <tr key={i}>
              <td className="px-6 py-4"><div className="h-4 w-32 animate-pulse rounded bg-slate-200" /></td>
              <td className="px-6 py-4"><div className="h-4 w-40 animate-pulse rounded bg-slate-200" /></td>
              <td className="px-6 py-4"><div className="h-4 w-48 animate-pulse rounded bg-slate-200" /></td>
              <td className="px-6 py-4 text-right"><div className="ml-auto h-4 w-20 animate-pulse rounded bg-slate-200" /></td>
            </tr>
          ))}
        </tbody>
      );
    }

    if (items.length === 0) {
      return (
        <tbody>
          <tr>
            <td colSpan={4} className="px-6 py-16 text-center">
              <div className="flex flex-col items-center gap-3">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-3xl">
                  📊
                </div>
                <p className="text-sm font-medium text-slate-600">No transactions recorded yet.</p>
                <p className="text-xs text-slate-400">
                  Start using Semranko tools to see your credit activity here.
                </p>
              </div>
            </td>
          </tr>
        </tbody>
      );
    }

    return (
      <tbody className="divide-y divide-slate-100">
        {items.map((item) => (
          <tr key={item.ledger_id} className="hover:bg-slate-50 transition-colors">
            <td className="px-6 py-4 text-sm text-slate-900">
              {item.keyword_or_domain_queried || "—"}
            </td>
            <td className="px-6 py-4">
              <Badge tone="secondary" size="sm">
                {item.action_type || "Unknown"}
              </Badge>
            </td>
            <td className="px-6 py-4 text-sm text-slate-600 whitespace-nowrap">
              {formatDateTime(item.timestamp)}
            </td>
            <td className="px-6 py-4 text-right">
              {formatCredits(item.credits_deducted, item.credits_color)}
            </td>
          </tr>
        ))}
      </tbody>
    );
  };

  if (!authenticated) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Usage & Activity Log</h1>
        <p className="mt-2 text-sm text-slate-500">
          Detailed audit trail of your credit consumption and token burns.
        </p>
      </div>

      {error && (
        <Alert variant="error" message={error} onDismiss={() => setError(null)} />
      )}

      {/* KPI Hero Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M21 12V7H3V12M21 12V17H3V12M21 12L12 3L3 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Spendable Credits</p>
              <p className="text-2xl font-bold text-slate-900">
                {spendableCredits !== null && spendableCredits !== undefined
                  ? spendableCredits.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                  : "—"}
              </p>
              <p className="text-xs text-slate-500">Top-up: {(pricingCurrent?.purchasedCreditsRemaining || 0).toLocaleString('en-US')}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-red-50 text-red-700">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M3 3V21H21" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M7 14L11 10L15 14L21 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Total Transactions</p>
              <p className="text-2xl font-bold text-slate-900">
                {total.toLocaleString("en-US")}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M13 2L3 14H12L11 22L21 10H12L13 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Automatic Tracking</p>
              <p className="text-2xl font-bold text-emerald-700">
                {(pricingCurrent?.automaticReservedRemaining || 0).toLocaleString('en-US')}
              </p>
              <p className="text-xs text-emerald-600">Reserved from {(pricingCurrent?.automaticReservedAllocation || 0).toLocaleString('en-US')}; unavailable for optional actions.</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-700">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M12 2V4M12 20V22M4 12H2M22 12H20M19.07 4.93L17.66 6.34M6.34 17.66L4.93 19.07M19.07 19.07L17.66 17.66M6.34 6.34L4.93 4.93" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Last Credit Refresh</p>
              <p className="text-sm font-semibold text-slate-900">
                {lastCreditResetAt ? new Date(lastCreditResetAt).toLocaleDateString() : "—"}
              </p>
              <p className="text-xs text-slate-500">
                Next: {nextCreditResetAt ? new Date(nextCreditResetAt).toLocaleDateString() : "—"}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Credit Transaction History Table */}
      <Card padding="p-0">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Credit Transaction History</h2>
            <p className="mt-1 text-sm text-slate-500">
              {total > 0 ? `${total} total records` : "No records found"}
            </p>
          </div>
        </div>

        <DataTable
          value={items}
          paginator
          rows={10}
          rowsPerPageOptions={[10, 20, 50, 100]}
          dataKey="ledger_id"
          emptyMessage="No transactions recorded yet."
          loading={loading}
          tableStyle={{ minWidth: '60rem', width: '100%' }}
          scrollable
          size="medium"
          scrollHeight="flex"
          frozenWidth="18rem"
        >
          <Column field="timestamp" header="Date & Time" style={{ width: '14rem' }} body={(rowData) => <span className="text-slate-600 whitespace-nowrap">{formatDateTime(rowData.timestamp)}</span>} />
          <Column field="action_type" header="Action Performed" style={{ width: '18rem' }} body={(rowData) => (
            <Badge tone="secondary" size="sm">
              {rowData.action_type || "Unknown"}
            </Badge>
          )} />
          <Column field="keyword_or_domain_queried" header="Resource Queried" style={{ width: '16rem' }} body={(rowData) => <span className="text-sm text-slate-900">{rowData.keyword_or_domain_queried || "—"}</span>} />
          <Column header="Credits Used" style={{ width: '10rem', textAlign: 'right' }} body={(rowData) => <div className="text-right">{formatCredits(rowData.credits_deducted, rowData.credits_color)}</div>} />
        </DataTable>

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
            <p className="text-xs text-slate-500">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
