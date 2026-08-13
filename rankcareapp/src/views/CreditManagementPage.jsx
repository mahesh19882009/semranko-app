'use client'
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";
import { initRazorpayCheckout } from "../lib/api";
import {
  createCreditTopUpOrderApi,
  fetchCreditBalanceApi,
  verifyCreditPaymentApi,
} from "../features/pricing/pricingApi";
import Alert from "../components/ui/Alert";

const TOP_UP_MULTIPLIERS = [
  { multiplier: 1, credits: 600, priceInr: 100, popular: false },
  { multiplier: 2, credits: 1200, priceInr: 200, popular: false },
  { multiplier: 3, credits: 1800, priceInr: 300, popular: true },
  { multiplier: 5, credits: 3000, priceInr: 500, popular: false },
  { multiplier: 10, credits: 6000, priceInr: 1000, popular: false },
];

export default function CreditManagementPage() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();
  const [balance, setBalance] = useState(null);
  const [loadingBalance, setLoadingBalance] = useState(false);
  const [loadingMultiplier, setLoadingMultiplier] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (!authenticated) {
      navigate("/login");
      return;
    }
    loadBalance();
  }, [authenticated]);

  const loadBalance = async () => {
    setLoadingBalance(true);
    setError(null);
    try {
      const data = await fetchCreditBalanceApi();
      if (data?.balance !== undefined) {
        setBalance(data.balance);
      }
    } catch (err) {
      setError(err.message || "Failed to load credit balance");
    } finally {
      setLoadingBalance(false);
    }
  };

  const handlePurchase = async (pack) => {
    setError(null);
    setSuccess(null);
    setLoadingMultiplier(pack.multiplier);

    try {
      const order = await createCreditTopUpOrderApi(pack.multiplier);

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
              setSuccess(`Successfully topped up ${added.toLocaleString()} credits!`);
              loadBalance();
            } else {
              setError("Payment verification failed. Please contact support.");
            }
          } catch (err) {
            setError(err.message || "Payment verification failed");
          } finally {
            setLoadingMultiplier(null);
          }
        },
        onPaymentError: (error) => {
          setError(error?.description || "Payment failed. Please try again.");
          setLoadingMultiplier(null);
        },
      });
    } catch (err) {
      setError(err.message || "Failed to initiate credit purchase");
      setLoadingMultiplier(null);
    }
  };

  const estimatedTotal = useMemo(() => {
    return balance;
  }, [balance]);

  if (!authenticated) {
    return null;
  }

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-5xl px-6 py-16">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900">Credit Management</h1>
          <p className="mt-2 text-sm text-slate-500">
            Purchase credits, track usage, and manage your account balance.
          </p>
        </div>

        {/* Balance Card */}
        <div className="mx-auto mt-10 max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="text-center">
            <p className="text-sm font-medium text-slate-500">Spendable Credits</p>
            {loadingBalance ? (
              <div className="mt-2 h-10 w-32 animate-pulse rounded bg-slate-200 mx-auto" />
            ) : (
              <p className="mt-2 text-4xl font-bold text-slate-900">
                {estimatedTotal !== null ? estimatedTotal.toFixed(2) : "—"}
              </p>
            )}
            <button
              onClick={loadBalance}
              className="mt-4 text-sm font-medium text-indigo-600 hover:text-indigo-700"
            >
              Refresh balance
            </button>
          </div>
        </div>

        {/* Credit Packs */}
        <div className="mt-16">
          <h2 className="text-center text-2xl font-bold text-slate-900">Top Up Credits</h2>
          <p className="mt-2 text-center text-sm text-slate-500">
            Top up credits at any time. 600 credits per ₹100. Credits never expire.
          </p>

          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
            {TOP_UP_MULTIPLIERS.map((pack) => {
              const perCredit = pack.priceInr / pack.credits;
              return (
                <div
                  key={pack.multiplier}
                  className={`relative flex flex-col rounded-2xl border bg-white p-6 shadow-sm ${
                    pack.popular ? "border-indigo-600 ring-1 ring-indigo-600" : "border-slate-200"
                  }`}
                >
                  {pack.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="rounded-full bg-indigo-600 px-3 py-1 text-xs font-semibold text-white">
                        Best Value
                      </span>
                    </div>
                  )}

                  <div className="mb-4">
                    <p className="text-2xl font-bold text-slate-900">
                      {pack.credits.toLocaleString('en-US')}
                    </p>
                    <p className="text-sm text-slate-500">credits</p>
                  </div>

                  <div className="mb-6">
                    <span className="text-xl font-bold text-slate-900">₹{pack.priceInr.toLocaleString('en-US')}</span>
                    <p className="text-xs text-slate-400">
                      ₹{perCredit.toFixed(2)} / credit
                    </p>
                  </div>

                  <button
                    onClick={() => handlePurchase(pack)}
                    disabled={loadingMultiplier === pack.multiplier}
                    className={`w-full rounded-xl px-4 py-3 text-sm font-semibold transition ${
                      pack.popular
                        ? "bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60"
                        : "bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-60"
                    }`}
                  >
                    {loadingMultiplier === pack.multiplier ? "Processing..." : "Top Up"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Alerts */}
        {error && (
          <div className="mx-auto mt-8 max-w-2xl">
            <Alert variant="error" message={error} />
          </div>
        )}
        {success && (
          <div className="mx-auto mt-8 max-w-2xl">
            <Alert variant="success" message={success} />
          </div>
        )}
      </div>
    </div>
  );
}
