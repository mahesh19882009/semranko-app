'use client'
import { useEffect, useState } from "react";
import { useNavigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";
import { apiRequest, initRazorpayCheckout } from "../lib/api";
import {
  createCreditPurchaseOrderApi,
  verifyCreditPaymentApi,
  getBillingHistoryApi,
  downloadInvoiceApi,
  createCreditTopUpOrderApi,
  fetchCreditBalanceApi,
  fetchTopUpPackagesApi,
} from "../features/pricing/pricingApi";
import { useSelector, useDispatch } from "react-redux";
import { fetchCurrentPricing, updateCreditBalance } from "../features/pricing/pricingSlice";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import { useToast } from "../components/ui/Toast";
import { ToastProvider } from "../components/ui/Toast";
import { formatDate } from "../utils/date";
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';

function formatCurrency(amount) {
  if (amount === null || amount === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(amount);
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
    <Alert variant={tone} className="!pt-1 !pb-[6px] !px-2">
      {status}
    </Alert>
  );
}

export default function BillingPage() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();
  const { addToast } = useToast();
  const dispatch = useDispatch();

  const pricingCurrent = useSelector((state) => state.pricing.current);
  const spendableCredits = pricingCurrent?.spendableCreditsRemaining ?? null;
  const automaticCredits = pricingCurrent?.automaticReservedRemaining ?? null;
  const purchasedCredits = pricingCurrent?.purchasedCreditsRemaining ?? null;

  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState(null);

  const [packages, setPackages] = useState([]);
  const [loadingPackages, setLoadingPackages] = useState(true);
  const [packagesError, setPackagesError] = useState(null);
  const [selectedPackageId, setSelectedPackageId] = useState(null);
  const [loadingPack, setLoadingPack] = useState(null);
  const [paymentError, setPaymentError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [topUpError, setTopUpError] = useState("");

  useEffect(() => {
    if (!authenticated) {
      navigate("/login");
      return;
    }
    loadHistory();
    loadCreditBalance();
    loadPackages();
    dispatch(fetchCurrentPricing());
  }, [authenticated, dispatch]);

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

  const loadCreditBalance = async () => {
    try {
      const data = await fetchCreditBalanceApi();
      if (data?.balance !== undefined) {
        dispatch(updateCreditBalance(data.balance));
      }
    } catch {
      // The primary billing view remains usable; balance fetch has its own retry on revisit.
    }
  };

  const loadPackages = async () => {
    setLoadingPackages(true);
    setPackagesError(null);
    try {
      const data = await fetchTopUpPackagesApi();
      const items = Array.isArray(data) ? data : [];
      setPackages(items);
      if (items.length > 0 && !selectedPackageId) {
        setSelectedPackageId(items[0].id);
      }
    } catch (err) {
      setPackagesError(err.message || "Failed to load top-up packages");
    } finally {
      setLoadingPackages(false);
    }
  };

  const selectedPackage = packages.find((pkg) => pkg.id === selectedPackageId) || null;

  const handlePurchase = async (pack) => {
    setTopUpError("");
    setPaymentError(null);
    setSuccessMessage(null);
    setLoadingPack(pack.id);

    try {
      const order = await createCreditTopUpOrderApi(pack.id);

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
              const added = verifyResult.data?.credits_added || pack.credits;
              const newBalance = verifyResult.data?.new_balance;
              setSuccessMessage(`Successfully topped up ${added.toLocaleString()} credits!`);
              setSelectedPackageId(pack.id);

              if (newBalance !== undefined) {
                dispatch(updateCreditBalance(newBalance));
              }

              loadHistory();
            } else {
              setPaymentError("Payment verification failed. Please contact support.");
            }
          } catch (err) {
            setPaymentError(err.message || "Payment verification failed");
          } finally {
            setLoadingPack(null);
          }
        },
        onPaymentError: async (error) => {
          setPaymentError(error?.description || "Payment failed. Please try again.");
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
          } catch {
            // Best-effort provider reconciliation; the original payment error is already visible.
          }
        },
      });
    } catch (err) {
      setPaymentError(err.message || "Failed to initiate payment");
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
          <div className="flex w-full flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-900">Billing & Invoices</h1>
              <p className="mt-2 text-sm text-slate-500">
                Review transactions, download invoices with GST details, and purchase credits.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className={`rounded-xl border border-slate-200 px-8 py-5 text-center shadow-sm ${spendableCredits > 0 ? 'bg-green-100' : 'bg-red-100'}`}>
                <p className="text-xs font-medium">Spendable Credits</p>
                <p className="text-xl font-bold text-slate-900">
                  {spendableCredits !== null && spendableCredits !== undefined
                    ? spendableCredits.toLocaleString('en-US')
                    : '—'}
                </p>
                <p className="mt-1 text-xs text-slate-500">Plan {pricingCurrent?.planSpendableCreditsRemaining?.toLocaleString('en-US') || 0} + top-up {purchasedCredits?.toLocaleString('en-US') || 0}</p>
              </div>
              <div className="rounded-xl border border-blue-200 bg-blue-50 px-8 py-5 text-center shadow-sm">
                <p className="text-xs font-medium text-blue-800">Automatic Tracking</p>
                <p className="text-xl font-bold text-slate-900">{automaticCredits?.toLocaleString('en-US') || 0}</p>
                <p className="mt-1 text-xs text-blue-700">Reserved; not spendable on optional actions</p>
              </div>
            </div>
          </div>
        </div>

        <Card>
          <div className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-5">
            <div><p className="text-slate-500">Current plan</p><p className="font-semibold capitalize text-slate-900">{pricingCurrent?.effectivePlan === 'free_trial' ? 'Free' : (pricingCurrent?.effectivePlan || '—')}</p></div>
            <div><p className="text-slate-500">Status</p><p className="font-semibold capitalize text-slate-900">{pricingCurrent?.subscriptionStatus || '—'}</p></div>
            <div><p className="text-slate-500">Next renewal</p><p className="font-semibold text-slate-900">{pricingCurrent?.subscriptionEndDate ? formatDate(pricingCurrent.subscriptionEndDate) : '—'}</p></div>
            <div><p className="text-slate-500">Credit reset</p><p className="font-semibold text-slate-900">{pricingCurrent?.nextCreditResetAt ? formatDate(pricingCurrent.nextCreditResetAt) : '—'}</p></div>
            <div><p className="text-slate-500">Pending plan change</p><p className="font-semibold capitalize text-slate-900">{pricingCurrent?.pendingPlanChange || 'None'}</p></div>
          </div>
        </Card>

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
            <DataTable
              value={history}
              paginator
              rows={10}
              rowsPerPageOptions={[10, 20, 50, 100]}
              dataKey="id"
              emptyMessage="No transactions found."
              loading={loadingHistory}
              tableStyle={{ minWidth: '60rem', width: '100%' }}
              className="compact-datatable"
              scrollable
              scrollHeight="flex"
              frozenWidth="18rem"
            >
              <Column field="purchase_type" header="Title" style={{ width: '14rem' }} body={(rowData) => (
                <div className="font-bold text-md text-slate-900">
                  {rowData.purchase_type === "SUBSCRIPTION_UPGRADE" ? "Subscription" : rowData.purchase_type === "CREDIT_TOP_UP" ? "Credit Top-Up" : "—"}
                </div>
              )} />
              <Column header="Invoice" style={{ width: '16rem' }} body={(rowData) => (
                <div className="flex flex-col">
                  {(rowData.status == 'completed' || rowData.status == 'paid') ? (
                    <>
                      <span className="font-mono text-xs text-slate-500">{rowData.invoice_number || `INV-${rowData.id.slice(0, 8).toUpperCase()}`}</span>
                      <span className="text-xs text-slate-400">{rowData.order_id ? `Order ${rowData.order_id.slice(0, 12)}...` : "—"}</span>
                    </>
                  ) : '—'}
                </div>
              )} />
              <Column field="timestamp" header="Date" style={{ width: '12rem' }} body={(rowData) => <span className="text-slate-600">{formatDate(rowData.timestamp)}</span>} />
              <Column header="Amount (₹)" style={{ width: '10rem' }} body={(rowData) => <span className="font-semibold text-slate-900">{formatCurrency(rowData.amount_paid_inr, "INR")}</span>} />
              <Column header="Status" style={{ width: '10rem' }} body={(rowData) => <StatusChip status={rowData.status} />} />
              <Column header="Actions" style={{ width: '8rem' }} body={(rowData) => (
                (rowData.status === "completed" || rowData.status === "paid") ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDownloadInvoice(rowData.id)}
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
                )
              )} />
            </DataTable>
          )}
        </Card>

        {/* Purchase Credits */}
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Purchase Credits</h2>

          <p className="font-semibold">
            💡 Need more credits? Choose a Top-Up package below. 18% GST will be applied at payment time.
          </p>

          {packagesError && (
            <div className="mt-4">
              <Alert variant="error" message={packagesError} />
            </div>
          )}

          {/* Predefined Package Cards */}
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {loadingPackages
              ? [1, 2, 3, 4, 5].map((n) => (
                <div key={n} className="h-40 animate-pulse rounded-2xl bg-slate-200" />
              ))
              : packages.map((pack) => (
                <div
                  key={pack.id}
                  className={`relative flex flex-col rounded-2xl border bg-white p-5 shadow-sm ${selectedPackageId === pack.id ? "border-brand-500 ring-1 ring-brand-500" : "border-slate-200"
                    }`}
                >
                  <div className="mb-3">
                    <p className="text-2xl font-bold text-slate-900">{pack.credits.toLocaleString('en-US')}</p>
                    <p className="text-sm text-slate-500">credits</p>
                  </div>
                  <div className="mb-4">
                    <span className="text-xl font-bold text-slate-900">₹{pack.priceInr.toLocaleString('en-US')}</span>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedPackageId(pack.id);
                      handlePurchase(pack);
                    }}
                    disabled={loadingPack === pack.id}
                    className={`w-full rounded-xl px-4 py-2.5 text-sm font-semibold transition ${selectedPackageId === pack.id
                        ? "bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-60"
                        : "bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-60"
                      }`}
                  >
                    {loadingPack === pack.id ? "Processing..." : "Buy Now"}
                  </button>
                </div>
              ))}
          </div>
        </div>

        {/* Alerts */}
        {
          paymentError && (
            <Alert variant="error" message={paymentError} onDismiss={() => setPaymentError(null)} />
          )
        }
        {
          successMessage && (
            <Alert variant="success" message={successMessage} onDismiss={() => setSuccessMessage(null)} />
          )
        }
      </div >
    </ToastProvider >
  );
}
