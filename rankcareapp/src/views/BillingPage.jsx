'use client'
import { useEffect, useState } from "react";
import { useNavigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";
import { initRazorpayCheckout } from "../lib/api";
import {
  createCreditPurchaseOrderApi,
  verifyCreditPaymentApi,
  getBillingHistoryApi,
  downloadInvoiceApi,
} from "../features/pricing/pricingApi";
import { useSelector } from "react-redux";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import { useToast } from "../components/ui/Toast";
import { ToastProvider } from "../components/ui/Toast";

function formatCurrency(amount) {
  if (amount === null || amount === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(amount);
}

function formatDate(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusChip({ status }) {
  const tone =
    status === "completed"
      ? "success"
      : status === "failed"
        ? "danger"
        : "warning";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold capitalize`}>
      {status}
    </span>
  );
}

export default function BillingPage() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();
  const { addToast } = useToast();

  const pricingCurrent = useSelector((state) => state.pricing.current);
  const currentCreditBalance = pricingCurrent?.creditBalance ?? null;

  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState(null);

  const [loadingPack, setLoadingPack] = useState(null);
  const [paymentError, setPaymentError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [customCredits, setCustomCredits] = useState(0);
  const [customCreditError, setCustomCreditError] = useState("");

  useEffect(() => {
    if (!authenticated) {
      navigate("/login");
      return;
    }
    loadHistory();
  }, [authenticated]);

  const loadHistory = async () => {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const data = await getBillingHistoryApi();
      setHistory(data?.history || []);
    } catch (err) {
      setHistoryError(err.message || "Failed to load billing history");
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleCustomPurchase = async () => {
    setCustomCreditError("");
    setPaymentError(null);
    setSuccessMessage(null);

    // Validation
    if (customCredits < 1000) {
      setCustomCreditError("Minimum 1,000 credits required.");
      return;
    }
    if (customCredits % 1000 !== 0) {
      setCustomCreditError("Please enter credit volumes only in clean multiples of 1,000.");
      return;
    }

    setLoadingPack(customCredits);

    try {
      const order = await createCreditPurchaseOrderApi(customCredits);

      await initRazorpayCheckout({
        order_id: order.order_id,
        amount: order.amount,
        currency: order.currency || "INR",
        key_id: order.key_id,
        prefill: {
          name: "",
          email: "",
        },
        onPaymentSuccess: async (response) => {
          try {
            const verifyResult = await verifyCreditPaymentApi(
              response.razorpay_order_id,
              response.razorpay_payment_id,
              response.razorpay_signature
            );
            if (verifyResult?.success) {
              setSuccessMessage(`Successfully purchased ${customCredits.toLocaleString()} credits!`);
              addToast(`Successfully purchased ${customCredits.toLocaleString()} credits!`, "success");
              setCustomCredits(0);
              loadHistory();
            } else {
              setPaymentError("Payment verification failed. Please contact support.");
              addToast("Payment verification failed. Please contact support.", "error");
            }
          } catch (err) {
            setPaymentError(err.message || "Payment verification failed");
            addToast(err.message || "Payment verification failed", "error");
          } finally {
            setLoadingPack(null);
          }
        },
        onPaymentError: (error) => {
          setPaymentError(error?.description || "Payment failed. Please try again.");
          addToast(error?.description || "Payment failed. Please try again.", "error");
          setLoadingPack(null);
        },
      });
    } catch (err) {
      setPaymentError(err.message || "Failed to initiate payment");
      addToast(err.message || "Failed to initiate payment", "error");
      setLoadingPack(null);
    }
  };

  const handleDownloadInvoice = async (ledgerId) => {
    try {
      const blob = await downloadInvoiceApi(ledgerId);
      const url = URL.createObjectURL(blob);
      const win = window.open(url, "_blank");
      if (!win) {
        addToast("Please allow popups to download invoices", "warning");
      }
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      addToast(err.message || "Failed to download invoice", "error");
    }
  };

  if (!authenticated) {
    return null;
  }

  return (
    <ToastProvider>
      <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Billing & Invoices</h1>
          <p className="mt-2 text-sm text-slate-500">
            Review transactions, download invoices, and purchase credits.
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <p className="text-xs font-medium text-slate-500">Available Credits</p>
          <p className="text-xl font-bold text-slate-900">
            {currentCreditBalance !== null && currentCreditBalance !== undefined
              ? currentCreditBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
              : '—'}
          </p>
        </div>
      </div>

      {/* Transaction History */}
      <Card padding="p-0">
        <div className="border-b border-slate-200 px-6 py-5">
          <h2 className="text-lg font-semibold text-slate-900">Transaction History</h2>
          <p className="mt-1 text-sm text-slate-500">All payment transactions linked to your account.</p>
        </div>

        {historyError && (
          <div className="p-6">
            <Alert variant="error" message={historyError} />
          </div>
        )}

        {loadingHistory ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-xl bg-slate-200" />
            ))}
          </div>
        ) : history.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-sm text-slate-500">No transactions found.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-4 font-medium">Invoice</th>
                  <th className="px-6 py-4 font-medium">Date</th>
                  <th className="px-6 py-4 font-medium">Amount</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {history.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="font-mono text-xs text-slate-500">{item.invoice_number || `INV-${item.id.slice(0, 8).toUpperCase()}`}</span>
                        <span className="text-xs text-slate-400">{item.order_id ? `Order ${item.order_id.slice(0, 12)}...` : "—"}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-600">{formatDate(item.timestamp)}</td>
                    <td className="px-6 py-4 font-semibold text-slate-900">{formatCurrency(item.amount_paid_inr)}</td>
                    <td className="px-6 py-4">
                      <StatusChip status={item.status} />
                    </td>
                    <td className="px-6 py-4 text-right">
                      {item.status === "completed" ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownloadInvoice(item.id)}
                          className="gap-1.5"
                        >
                          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                            <path d="M7 1V9M7 9L4 6M7 9L10 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            <path d="M1 10V12H13V10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                          PDF
                        </Button>
                      ) : (
                        <span className="text-xs text-slate-400">N/A</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Razorpay Tier Grid */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Purchase Credits</h2>
        
        {/* Accurate Legal Disclaimer */}
        <div className="mt-4 rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-800">
          <p className="font-semibold">💡 Monthly subscription baseline credits reset at the end of each billing cycle. However, any manually purchased Credit Top-ups will remain securely added to your account and valid for use as long as your underlying paid plan subscription remains active.</p>
        </div>

        {/* Credit Top-Up Form */}
        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Custom Credit Top-Up</h3>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="credit-input" className="block text-sm font-medium text-slate-700 mb-2">
                Enter Credits to Add (Minimum 1,000, must be in multiples of 1,000)
              </label>
              <input
                id="credit-input"
                type="number"
                min="1000"
                step="1000"
                value={customCredits}
                onChange={(e) => setCustomCredits(parseInt(e.target.value) || 0)}
                disabled={loadingPack}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-900 disabled:bg-slate-50 disabled:cursor-not-allowed"
                placeholder="Enter credits (e.g., 1000, 2000, 3000...)"
              />
              {customCreditError && (
                <p className="mt-2 text-sm font-medium text-rose-600">{customCreditError}</p>
              )}
            </div>

            {/* Live Price Calculator */}
            {customCredits >= 1000 && customCredits % 1000 === 0 && (
              <div className="rounded-lg bg-slate-50 px-4 py-3">
                <p className="text-sm text-slate-600">
                  <span className="font-semibold">Base Price:</span> ₹{(customCredits * 0.20).toFixed(2)} per 1,000 credits, excluding 18% GST
                </p>
                <p className="text-sm text-slate-600 mt-1">
                  <span className="font-semibold">Total Payable (incl. GST):</span> ₹{((customCredits * 0.20) * 1.18).toFixed(2)}
                </p>
              </div>
            )}

            <Button
              onClick={() => handleCustomPurchase()}
              disabled={loadingPack || customCredits < 1000 || customCredits % 1000 !== 0}
              loading={loadingPack}
              fullWidth
            >
              {loadingPack ? "Processing..." : "Proceed to Payment"}
            </Button>
          </div>
        </div>
      </div>

      {/* Alerts */}
      {paymentError && (
        <Alert variant="error" message={paymentError} onDismiss={() => setPaymentError(null)} />
      )}
      {successMessage && (
        <Alert variant="success" message={successMessage} onDismiss={() => setSuccessMessage(null)} />
      )}
    </div>
    </ToastProvider>
  );
}
