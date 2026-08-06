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
  createCreditTopUpOrderApi,
} from "../features/pricing/pricingApi";
import { useSelector } from "react-redux";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import { useToast } from "../components/ui/Toast";
import { ToastProvider } from "../components/ui/Toast";

function formatCurrency(amount, currency = "INR") {
  if (amount === null || amount === undefined) return "—";
  if (currency === "USD") {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    }).format(amount);
  }
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
  const normalized = (status || "").toLowerCase();
  const tone =
    normalized === "completed" || normalized === "paid"
      ? "success"
      : normalized === "failed" || normalized === "created"
        ? "error"
        : "warning";
  return (
    <Alert variant={tone}>
      {status}
    </Alert>
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
  const [multiplier, setMultiplier] = useState(1);
  const [topUpError, setTopUpError] = useState("");
  const [currency, setCurrency] = useState("INR");

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
    setTopUpError("");
    setPaymentError(null);
    setSuccessMessage(null);

    if (multiplier < 1) {
      setTopUpError("Minimum multiplier is 1 (600 credits).");
      return;
    }

    const credits = multiplier * 600;
    const basePrice = multiplier * 100;
    const discountPct = pricingCurrent?.individual_discount_pct || 0;
    const discountedPrice = discountPct > 0 ? basePrice * (1 - discountPct / 100) : basePrice;
    const cleanPrice = Number.isInteger(discountedPrice) ? discountedPrice : Math.round(discountedPrice);

    setLoadingPack(multiplier);

    try {
      const order = await createCreditTopUpOrderApi(multiplier);

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
            const verifyResult = await verifyPaymentApi(
              response.razorpay_order_id,
              response.razorpay_payment_id,
              response.razorpay_signature
            );
            if (verifyResult?.success) {
              const added = verifyResult.data?.credits_added || (multiplier * 1000);
              setSuccessMessage(`Successfully topped up ${added.toLocaleString()} credits!`);
              addToast(`Successfully topped up ${added.toLocaleString()} credits!`, "success");
              setMultiplier(1);
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
        onPaymentError: async (error) => {
          setPaymentError(error?.description || "Payment failed. Please try again.");
          addToast(error?.description || "Payment failed. Please try again.", "error");
          setLoadingPack(null);

          try {
            const orderId = order.order_id;
            if (orderId) {
              await apiRequest("/payments/mark-failed", {
                method: "POST",
                body: JSON.stringify({ razorpay_order_id: orderId }),
              });
              loadHistory();
            }
          } catch (err) {
            logger.error("Failed to mark payment as failed: %s", err);
          }
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
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Billing & Invoices</h1>
            <p className="mt-2 text-sm text-slate-500">
              Review transactions, download invoices with GST details, and purchase credits.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <p className="text-xs font-medium text-slate-500">Available Credits</p>
              <p className="text-xl font-bold text-slate-900">
                {currentCreditBalance !== null && currentCreditBalance !== undefined
                  ? currentCreditBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                  : '—'}
              </p>
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
              <span className="text-xs font-medium text-slate-500">Currency:</span>
              <button
                onClick={() => setCurrency("INR")}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${currency === "INR" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
              >
                ₹ INR
              </button>
              <button
                onClick={() => setCurrency("USD")}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${currency === "USD" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
              >
                $ USD
              </button>
            </div>
          </div>
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
                    <th className="px-6 py-4 font-medium">Amount ({currency === "INR" ? "₹" : "$"})</th>
                    <th className="px-6 py-4 font-medium">GST</th>
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
                          {item.purchase_type && (
                            <span className="text-xs text-slate-400">{item.purchase_type === "SUBSCRIPTION_UPGRADE" ? "Subscription" : "Credit Top-Up"}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-600">{formatDate(item.timestamp)}</td>
                      <td className="px-6 py-4 font-semibold text-slate-900">{formatCurrency(item.amount_paid_inr, currency)}</td>
                      <td className="px-6 py-4 text-slate-600">
                        {item.gst_amount ? `${item.gst_amount.toFixed(2)} (18%)` : "—"}
                      </td>
                      <td className="px-6 py-4">
                        <StatusChip status={item.status} />
                      </td>
                      <td className="px-6 py-4 text-right">
                        {item.status === "completed" || item.status === "paid" ? (
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

          <div className="mt-4 rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-800">
            <p className="font-semibold">💡 Credit Top-Up: 600 credits per ₹100. No bulk discount. All payments processed via Razorpay with 18% GST applied at payment time.</p>
          </div>

          {/* Credit Top-Up Form */}
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">Credit Top-Up</h3>

            <div className="space-y-4">
              <div>
                <label htmlFor="multiplier-input" className="block text-sm font-medium text-slate-700 mb-2">
                  Select Credit Pack (each pack = 600 credits)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    id="multiplier-input"
                    type="number"
                    min="1"
                    step="1"
                    value={multiplier}
                    onChange={(e) => setMultiplier(Math.max(1, parseInt(e.target.value) || 1))}
                    disabled={loadingPack}
                    className="w-24 rounded-xl border border-slate-300 px-4 py-3 text-center text-sm outline-none focus:border-slate-900 disabled:bg-slate-50 disabled:cursor-not-allowed"
                  />
                  <span className="text-sm text-slate-500">pack(s) = {(multiplier * 600).toLocaleString()} credits</span>
                </div>
                {topUpError && (
                  <p className="mt-2 text-sm font-medium text-rose-600">{topUpError}</p>
                )}
              </div>

              {/* Live Price Calculator */}
              {multiplier >= 1 && (
                <div className="rounded-lg bg-slate-50 px-4 py-3">
                  {(() => {
                    const basePrice = multiplier * 500;
                    const discountPct = pricingCurrent?.individual_discount_pct || 0;
                    const discountedPrice = discountPct > 0 ? basePrice * (1 - discountPct / 100) : basePrice;
                    const cleanPrice = Number.isInteger(discountedPrice) ? discountedPrice : Math.round(discountedPrice);
                    return (
                      <>
                        {discountPct > 0 ? (
                          <div className="space-y-1">
                            <p className="text-sm text-slate-400 line-through">
                              Base Price: ₹{basePrice.toLocaleString('en-US')}
                            </p>
                            <p className="text-sm font-semibold text-slate-900">
                              Your Price: ₹{cleanPrice.toLocaleString('en-US')} ({discountPct}% off)
                            </p>
                            <p className="text-xs text-slate-500">
                              {(multiplier * 600).toLocaleString()} credits at ₹{(cleanPrice / (multiplier * 600)).toFixed(2)} per credit
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-1">
                            <p className="text-sm font-semibold text-slate-900">
                              Total: ₹{cleanPrice.toLocaleString('en-US')}
                            </p>
                            <p className="text-xs text-slate-500">
                              {(multiplier * 600).toLocaleString()} credits at ₹{(cleanPrice / (multiplier * 600)).toFixed(2)} per credit
                            </p>
                          </div>
                        )}
                      </>
                    );
                  })()}
                </div>
              )}

              <Button
                onClick={() => handleCustomPurchase()}
                disabled={loadingPack || multiplier < 1}
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
