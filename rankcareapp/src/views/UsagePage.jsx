'use client'
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";
import { getUsageLogApi } from "../features/pricing/pricingApi";
import { useSelector } from "react-redux";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Alert from "../components/ui/Alert";
import { useToast } from "../components/ui/Toast";
import { Chart } from "primereact/chart";

const FILTER_OPTIONS = [
  { value: "all", label: "All Transactions" },
  { value: "live", label: "Live Searches" },
  { value: "cache", label: "Free Cache Hits" },
];

const LIVE_SEARCH_TYPES = new Set([
  "SINGLE_SEARCH",
  "BULK_SEARCH",
  "KEYWORD_IDEAS",
  "COMPETITOR_SPY",
  "TRACKING_STANDARD",
  "TRACKING_AI",
]);

const ACTION_BADGE_TONE = {
  SINGLE_SEARCH: "secondary",
  BULK_SEARCH: "secondary",
  KEYWORD_IDEAS: "info",
  COMPETITOR_SPY: "primary",
  TRACKING_STANDARD: "warning",
  TRACKING_AI: "primary",
  CACHE_HIT: "success",
  TOP_UP: "success",
};

const ACTION_LABEL = {
  SINGLE_SEARCH: "Single Search",
  BULK_SEARCH: "Bulk Search",
  KEYWORD_IDEAS: "Keyword Ideas",
  COMPETITOR_SPY: "Competitor Spy",
  TRACKING_STANDARD: "Tracking Standard",
  TRACKING_AI: "AI Tracking",
  CACHE_HIT: "Cache Hit",
  TOP_UP: "Top Up",
};

function formatCurrency(amount) {
  if (amount === null || amount === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(amount);
}

function formatDateTime(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

export default function UsagePage() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();
  const { addToast } = useToast();

  const pricingCurrent = useSelector((state) => state.pricing.current);
  const creditBalance = pricingCurrent?.creditBalance ?? null;

  const [filter, setFilter] = useState("all");
  const [usageData, setUsageData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

    getUsageLogApi(1, 20, filter === "all" ? null : filter === "cache" ? "CACHE_HIT" : null)
      .then((data) => {
        if (!cancelled) {
          setUsageData(data || null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Failed to load usage log");
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
  }, [filter]);

  const totalSpent = usageData?.total_spent_this_month ?? 0;
  const totalSaved = usageData?.total_saved_by_cache ?? 0;
  const items = usageData?.items || [];

  // Prepare chart data for credit consumption by action type
  const chartData = useMemo(() => {
    if (!items || items.length === 0) return null;

    const actionCounts = {};
    items.forEach(item => {
      const action = item.action_type || 'Unknown';
      actionCounts[action] = (actionCounts[action] || 0) + (item.credits_spent || 0);
    });

    const labels = Object.keys(actionCounts);
    const data = Object.values(actionCounts);
    const colors = [
      '#3B82F6', // blue
      '#10B981', // green
      '#F59E0B', // amber
      '#EF4444', // red
      '#8B5CF6', // purple
      '#EC4899', // pink
      '#6366F1', // indigo
      '#14B8A6', // teal
    ];

    return {
      labels,
      datasets: [{
        data,
        backgroundColor: colors.slice(0, labels.length),
        hoverBackgroundColor: colors.slice(0, labels.length),
      }]
    };
  }, [items]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: {
          usePointStyle: true,
          padding: 20,
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.parsed || 0;
            const total = context.dataset.data.reduce((a, b) => a + b, 0);
            const percentage = ((value / total) * 100).toFixed(1);
            return `${label}: ${value} credits (${percentage}%)`;
          }
        }
      }
    }
  };

  const renderTableBody = () => {
    if (loading) {
      return (
        <tbody className="divide-y divide-slate-100">
          {[1, 2, 3, 4, 5].map((i) => (
            <tr key={i}>
              <td className="px-6 py-4">
                <div className="h-4 w-32 animate-pulse rounded bg-slate-200" />
              </td>
              <td className="px-6 py-4">
                <div className="h-4 w-24 animate-pulse rounded bg-slate-200" />
              </td>
              <td className="px-6 py-4">
                <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />
              </td>
              <td className="px-6 py-4">
                <div className="h-4 w-28 animate-pulse rounded bg-slate-200" />
              </td>
              <td className="px-6 py-4 text-right">
                <div className="ml-auto h-4 w-16 animate-pulse rounded bg-slate-200" />
              </td>
            </tr>
          ))}
        </tbody>
      );
    }

    if (items.length === 0) {
      return (
        <tbody>
          <tr>
            <td colSpan={5} className="px-6 py-16 text-center">
              <div className="flex flex-col items-center gap-3">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-3xl">
                  📊
                </div>
                <p className="text-sm font-medium text-slate-600">No activity recorded yet.</p>
                <p className="text-xs text-slate-400">
                  Start exploring keywords to populate your dashboard log!
                </p>
              </div>
            </td>
          </tr>
        </tbody>
      );
    }

    return (
      <tbody className="divide-y divide-slate-100">
        {items.map((item) => {
          const isCacheHit = item.action_type === "CACHE_HIT";
          const isTopUp = item.action_type === "TOP_UP";
          const tone = ACTION_BADGE_TONE[item.action_type] || "secondary";
          const label = ACTION_LABEL[item.action_type] || item.action_type;

          return (
            <tr key={item.id} className="hover:bg-slate-50 transition-colors">
              <td className="px-6 py-4 text-sm text-slate-600">
                {formatDateTime(item.timestamp)}
              </td>
              <td className="px-6 py-4">
                <Badge tone={tone} size="sm">
                  {label}
                </Badge>
              </td>
              <td className="px-6 py-4 text-sm text-slate-900">
                {item.query_target || "—"}
              </td>
              <td className="px-6 py-4 text-sm text-slate-600">
                {item.triggered_by_user_id ? (
                  <span className="inline-flex items-center gap-1.5">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
                      {(item.triggered_by_user_id || "?").slice(0, 2).toUpperCase()}
                    </span>
                    <span className="font-mono text-xs text-slate-500">
                      {item.triggered_by_user_id.slice(0, 8)}...
                    </span>
                  </span>
                ) : (
                  <span className="text-slate-400">System</span>
                )}
              </td>
              <td className="px-6 py-4 text-right text-sm font-semibold">
                {isCacheHit ? (
                  <span className="text-emerald-600">0 Credits</span>
                ) : isTopUp ? (
                  <span className="text-emerald-600">+{item.credits_spent || 0}</span>
                ) : (
                  <span className="text-red-600">-{item.credits_spent || 0} Credits</span>
                )}
              </td>
            </tr>
          );
        })}
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
          Detailed audit trail of your credit consumption and team actions.
        </p>
      </div>

      {error && (
        <Alert variant="error" message={error} onDismiss={() => setError(null)} />
      )}

      {/* KPI Hero Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M21 12V7H3V12M21 12V17H3V12M21 12L12 3L3 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Current Balance</p>
              <p className="text-2xl font-bold text-slate-900">
                {creditBalance !== null && creditBalance !== undefined
                  ? creditBalance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                  : "—"}
              </p>
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
              <p className="text-xs font-medium text-slate-500">Credits Burned This Month</p>
              <p className="text-2xl font-bold text-slate-900">
                {totalSpent.toLocaleString("en-US")}
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
              <p className="text-xs font-medium text-slate-500">Cache Savings</p>
              <p className="text-2xl font-bold text-emerald-700">
                {totalSaved.toLocaleString("en-US")}
              </p>
              <p className="text-xs text-emerald-600">⚡ Saved by Database Cache (₹0 Cost Lookups)</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Credit Consumption Chart */}
      {chartData && (
        <Card>
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Credit Consumption by Action Type</h2>
            <p className="mt-1 text-sm text-slate-500">
              Breakdown of your credit usage across different activities.
            </p>
          </div>
          <div className="flex items-center justify-center" style={{ height: '300px' }}>
            <Chart type="pie" data={chartData} options={chartOptions} />
          </div>
        </Card>
      )}

      {/* Audit Trail Table */}
      <Card padding="p-0">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Activity Log</h2>
            <p className="mt-1 text-sm text-slate-500">
              {usageData?.total
                ? `${usageData.total} total records`
                : "No records found"}
            </p>
          </div>

          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm outline-none transition focus:border-brand-600 focus:ring-brand-200"
          >
            {FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
                <th className="px-6 py-4 font-medium">Date & Time</th>
                <th className="px-6 py-4 font-medium">Feature Used</th>
                <th className="px-6 py-4 font-medium">Searched Target</th>
                <th className="px-6 py-4 font-medium">Run By</th>
                <th className="px-6 py-4 font-medium text-right">Credit Cost</th>
              </tr>
            </thead>
            {renderTableBody()}
          </table>
        </div>

        {usageData && usageData.total_pages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
            <p className="text-xs text-slate-500">
              Page {usageData.page} of {usageData.total_pages}
            </p>
            <div className="flex gap-2">
              <button
                disabled={usageData.page <= 1}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                disabled={usageData.page >= usageData.total_pages}
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
