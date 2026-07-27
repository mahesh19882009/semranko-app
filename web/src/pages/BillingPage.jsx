import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchInvoicesApi } from "../features/pricing/pricingApi";
import { PLANS } from "../config/pricing";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faFileInvoiceDollar,
  faWallet,
  faDownload,
  faCircleXmark,
  faSpinner,
  faArrowRight,
  faClock,
  faTag,
} from "@fortawesome/free-solid-svg-icons";

function fmt(amount) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(amount);
}

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function StatusBadge({ status }) {
  const map = {
    paid: { cls: "bg-emerald-100 text-emerald-700", label: "Paid" },
    captured: { cls: "bg-emerald-100 text-emerald-700", label: "Paid" },
    created: { cls: "bg-amber-100 text-amber-700", label: "Pending" },
    failed: { cls: "bg-rose-100 text-rose-700", label: "Failed" },
    refunded: { cls: "bg-slate-100 text-slate-600", label: "Refunded" },
  };
  const s = map[status?.toLowerCase()] ?? { cls: "bg-slate-100 text-slate-600", label: status || "—" };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.cls}`}>
      {s.label}
    </span>
  );
}

// Very simple print-to-PDF invoice (opens browser print dialog)
function printInvoice(inv) {
  const invoiceNumber = `INV-${inv.invoice_id.slice(-8).toUpperCase()}`;
  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8"/>
      <title>Invoice ${invoiceNumber} – RankCare</title>
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; color: #1e293b; font-size: 14px; padding: 40px; }
        .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; }
        .brand { font-size: 24px; font-weight: 700; color: #4f46e5; }
        .brand-sub { font-size: 11px; color: #64748b; margin-top: 2px; }
        .inv-meta { text-align: right; }
        .inv-meta h2 { font-size: 20px; font-weight: 700; color: #1e293b; }
        .inv-meta p { font-size: 12px; color: #64748b; margin-top: 3px; }
        .divider { border: none; border-top: 1px solid #e2e8f0; margin: 20px 0; }
        .section { margin-bottom: 24px; }
        .section-title { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8; margin-bottom: 8px; }
        .bill-to p { font-size: 14px; color: #334155; line-height: 1.6; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
        th { text-align: left; font-size: 12px; text-transform: uppercase; color: #94a3b8; padding: 8px 12px; border-bottom: 2px solid #e2e8f0; }
        td { padding: 12px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }
        .totals { width: 260px; margin-left: auto; }
        .totals td { padding: 6px 12px; }
        .totals .label { color: #64748b; }
        .totals .grand { font-weight: 700; font-size: 16px; color: #1e293b; border-top: 2px solid #e2e8f0; padding-top: 10px; }
        .footer { text-align: center; font-size: 12px; color: #94a3b8; margin-top: 40px; }
        .badge { display: inline-block; background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; border-radius: 9999px; padding: 2px 10px; font-size: 12px; font-weight: 600; }
        @media print { body { padding: 20px; } }
      </style>
    </head>
    <body>
      <div class="header">
        <div>
          <div class="brand">RankCare</div>
          <div class="brand-sub">SEO Ranking Suite · rankcare.app</div>
        </div>
        <div class="inv-meta">
          <h2>TAX INVOICE</h2>
          <p><strong>${invoiceNumber}</strong></p>
          <p>Date: ${fmtDate(inv.date)}</p>
          <p><span class="badge">${inv.status?.toUpperCase() || "PAID"}</span></p>
        </div>
      </div>
      <hr class="divider"/>
      <div style="display:flex; gap: 60px; margin-bottom: 24px;">
        <div class="section">
          <div class="section-title">Billed By</div>
          <div class="bill-to">
            <p><strong>RankCare Technologies</strong></p>
            <p>GST: 29AAACR0000A1Z5 (placeholder)</p>
            <p>support@rankcare.app</p>
          </div>
        </div>
        <div class="section">
          <div class="section-title">Billed To</div>
          <div class="bill-to">
            <p><strong>${inv.user_name}</strong></p>
            <p>${inv.user_email}</p>
          </div>
        </div>
        <div class="section" style="margin-left:auto; text-align:right;">
          <div class="section-title">Payment Reference</div>
          <div class="bill-to">
            <p>Order: ${inv.order_id}</p>
            ${inv.payment_id ? `<p>Payment: ${inv.payment_id}</p>` : ""}
          </div>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Description</th>
            <th>HSN/SAC</th>
            <th style="text-align:right">Amount</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            <td>RankCare ${inv.plan_name} Plan – Monthly Subscription</td>
            <td>998313</td>
            <td style="text-align:right">${fmt(inv.base_amount)}</td>
          </tr>
        </tbody>
      </table>
      <table class="totals">
        <tr><td class="label">Subtotal (excl. GST)</td><td style="text-align:right">${fmt(inv.base_amount)}</td></tr>
        <tr><td class="label">IGST @ ${inv.gst_rate}%</td><td style="text-align:right">${fmt(inv.gst_amount)}</td></tr>
        <tr class="grand"><td><strong>Total</strong></td><td style="text-align:right"><strong>${fmt(inv.total_amount)}</strong></td></tr>
      </table>
      <hr class="divider"/>
      <div class="footer">
        <p>This is a computer-generated invoice. No signature required.</p>
        <p style="margin-top:4px;">RankCare · support@rankcare.app</p>
      </div>
    </body>
    </html>
  `;
  const win = window.open("", "_blank");
  win.document.write(html);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 500);
}

export default function BillingPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [invoices, setInvoices] = useState([]);
  const [creditBalance, setCreditBalance] = useState(0);
  const [pendingPlanChange, setPendingPlanChange] = useState(null);
  const [error, setError] = useState(null);

  const loadInvoices = useCallback(async () => {
    console.log('[BillingPage] loadInvoices called');
    try {
      setLoading(true);
      setError(null);

      const fetchPromise = fetchInvoicesApi();
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Request timed out')), 10000);
      });

      const data = await Promise.race([fetchPromise, timeoutPromise]);
      console.log('[BillingPage] fetchInvoicesApi result', data);
      setInvoices(data.invoices || []);
      setCreditBalance(data.credit_balance || 0);
      setPendingPlanChange(data.pendingPlanChange || null);
    } catch (err) {
      console.error('[BillingPage] loadInvoices error', err);
      setError(err.message || "Failed to load billing history.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadInvoices();
  }, [loadInvoices]);

  const totalPaid = invoices
    .filter(inv => ["paid", "captured"].includes(inv.status?.toLowerCase()))
    .reduce((sum, inv) => sum + inv.total_amount, 0);

  const totalGST = invoices
    .filter(inv => ["paid", "captured"].includes(inv.status?.toLowerCase()))
    .reduce((sum, inv) => sum + inv.gst_amount, 0);

  return (
    <div className="min-h-screen bg-slate-50 pb-16">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white px-6 py-6 shadow-sm">
        <div className="mx-auto max-w-5xl">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Billing &amp; Invoices</h1>
              <p className="mt-1 text-sm text-slate-500">
                All transactions, GST breakdown, and account credit balance
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/pricing")}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition"
            >
              Manage Plan
              <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto pt-8">
        {/* Summary Cards */}
        <div className="grid gap-5 sm:grid-cols-2 mb-10">
          {/* Pending Plan Change */}
          {pendingPlanChange && (
            <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-white p-5 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500 text-white">
                  <FontAwesomeIcon icon={faClock} />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-amber-600">
                    Pending Plan Change
                  </p>
                  <p className="text-2xl font-bold text-slate-900">
                    {PLANS.find(p => p.key === pendingPlanChange)?.name || pendingPlanChange}
                  </p>
                </div>
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Will take effect at the end of your current billing period.
              </p>
            </div>
          )}

          {/* Account Credit */}
          {!pendingPlanChange && (
            <div className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-5 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500 text-white">
                  <FontAwesomeIcon icon={faWallet} />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-emerald-600">
                    Account Credit
                  </p>
                  <p className="text-2xl font-bold text-slate-900">{fmt(creditBalance)}</p>
                </div>
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Available for upgrades.
              </p>
            </div>
          )}

          {/* Total Paid */}
          <div className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-5 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
                <FontAwesomeIcon icon={faFileInvoiceDollar} />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
                  Total Paid
                </p>
                <p className="text-2xl font-bold text-slate-900">{fmt(totalPaid)}</p>
              </div>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Across {invoices.filter(i => ["paid", "captured"].includes(i.status?.toLowerCase())).length} payment(s)
            </p>
          </div>
        </div>

        {/* Invoice Table */}
        <div className="rounded-3xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <h2 className="text-base font-semibold text-slate-900">Invoice History</h2>
            <span className="text-xs text-slate-400">{invoices.length} transaction(s)</span>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <FontAwesomeIcon icon={faSpinner} className="animate-spin text-3xl mb-3" />
              <p className="text-sm">Loading invoices…</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-20 text-rose-500">
              <FontAwesomeIcon icon={faCircleXmark} className="text-3xl mb-3" />
              <p className="text-sm font-medium">{error}</p>
              <button
                onClick={loadInvoices}
                className="mt-4 rounded-xl border border-rose-200 px-4 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 transition"
              >
                Retry
              </button>
            </div>
          ) : invoices.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <FontAwesomeIcon icon={faFileInvoiceDollar} className="text-4xl mb-4 opacity-30" />
              <p className="text-sm font-medium text-slate-500">No invoices yet</p>
              <p className="mt-1 text-xs text-slate-400">
                Your payment history will appear here after your first subscription.
              </p>
              <button
                type="button"
                onClick={() => navigate("/pricing")}
                className="mt-5 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition"
              >
                View Plans <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table className="min-w-full text-left text-sm">
                    <thead className="sticky top-0 bg-slate-50 text-slate-500">
                      <tr>
                        <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider">Date</th>
                        <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider">Invoice</th>
                        <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider">Plan</th>
                        <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider">Credit</th>
                        <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider">Paid</th>
                        <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider">Status</th>
                        <th className="px-6 py-3 font-semibold text-xs uppercase tracking-wider">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {invoices.map((inv) => (
                        <tr key={inv.order_id} className="hover:bg-slate-50 transition">
                          <td className="px-6 py-4 text-slate-600 whitespace-nowrap">
                            {fmtDate(inv.date)}
                          </td>
                          <td className="px-6 py-4">
                            {inv.invoice_id ? (
                              <>
                                <p className="font-mono text-xs text-slate-500">
                                  INV-{inv.invoice_id.slice(-8).toUpperCase()}
                                </p>
                                <p className="font-mono text-[11px] text-slate-400 mt-0.5">
                                  {inv.order_id}
                                </p>
                              </>
                            ) : (
                              <p className="font-mono text-xs text-slate-400">—</p>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
                              {inv.plan_name}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-emerald-700 font-medium">
                            {(inv.credit_applied || 0) > 0 ? `-${fmt(inv.credit_applied)}` : "—"}
                          </td>
                          <td className="px-6 py-4 font-bold text-slate-900">
                            {fmt(inv.total_amount)}
                          </td>
                          <td className="px-6 py-4">
                            <StatusBadge status={inv.status} />
                          </td>
                          <td className="px-6 py-4">
                            {["paid", "captured"].includes(inv.status?.toLowerCase()) ? (
                              <button
                                type="button"
                                onClick={() => printInvoice(inv)}
                                title="Download / Print Invoice"
                                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
                              >
                                <FontAwesomeIcon icon={faDownload} />
                                PDF
                              </button>
                            ) : (
                              <span className="text-xs text-slate-400">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
          )}
        </div>

        {/* GST Info Footer */}
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white px-6 py-4 text-xs text-slate-500">
          <p>
            <strong className="text-slate-700">GST Note:</strong> All prices are inclusive of 18% Goods &amp; Services Tax (IGST).
            SAC Code: <strong>998313</strong> – Software as a Service (SaaS).
            For GST queries, contact <a href="mailto:support@rankcare.app" className="text-indigo-600 underline">support@rankcare.app</a>.
          </p>
        </div>
      </div>
    </div>
  );
}
