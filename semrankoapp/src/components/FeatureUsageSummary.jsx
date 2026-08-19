'use client'

function formatReset(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'long' }).format(new Date(value));
}

export default function FeatureUsageSummary({ label, usage, costLabel }) {
  const used = usage?.used ?? 0;
  const limit = usage?.limit ?? 0;
  const remaining = usage?.remaining ?? Math.max(0, limit - used);
  const exhausted = limit > 0 && remaining <= 0;

  return (
    <div className={`rounded-xl border p-3 text-sm ${exhausted ? 'border-amber-300 bg-amber-50' : 'border-slate-200 bg-slate-50'}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold text-slate-900">{label}: {used} of {limit} used</span>
        {costLabel && <span className="text-xs text-slate-500">{costLabel}</span>}
      </div>
      <p className={`mt-1 text-xs ${exhausted ? 'font-semibold text-amber-800' : 'text-slate-500'}`}>
        {exhausted ? 'Allowance exhausted' : `${remaining} remaining`} · Resets {formatReset(usage?.resetAt)}
      </p>
    </div>
  );
}
