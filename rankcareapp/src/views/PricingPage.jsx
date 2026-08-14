"use client";

import { useEffect, useState } from "react";
import { Check, X, ArrowRight } from "lucide-react";

import { Link, useNavigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";
import { apiRequest, initRazorpayCheckout } from "../lib/api";
import {
  createPaymentOrderApi,
  verifyPaymentApi,
} from "../features/pricing/pricingApi";
import { useDispatch, useSelector } from "react-redux";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import {
  fetchCurrentPricing,
  fetchPricingPlans,
} from "../features/pricing/pricingSlice";

const ORDER = { free_trial: 0, starter: 1, pro: 2, agency: 3 };
const PLAN_IDS = { starter: 0, pro: 1, agency: 2 };

export default function PricingPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [authenticated, setAuthenticated] = useState(false);
  const [currency, setCurrency] = useState("INR");
  const [period, setPeriod] = useState("monthly");
  const [loadingPlan, setLoadingPlan] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const plans = useSelector((state) => state.pricing.plans).filter((plan) =>
    ["free_trial", "starter", "pro", "agency"].includes(plan.key),
  );
  const loading = useSelector((state) => state.pricing.loadingPlans);
  const current = useSelector((state) => state.pricing.current);
  const currentPlan = current?.effectivePlan || current?.plan;
  useEffect(() => {
    const signedIn = isAuthenticated();
    setAuthenticated(signedIn);
    dispatch(fetchPricingPlans());
    if (signedIn) dispatch(fetchCurrentPricing());
  }, [dispatch]);

  const choosePlan = async (plan) => {
    setError("");
    setSuccess("");
    if (plan.key === "free_trial") {
      navigate(authenticated ? "/dashboard" : "/register");
      return;
    }
    if (!authenticated) {
      navigate("/register");
      return;
    }
    if (currency === "USD") {
      setError(
        "USD checkout is not available yet. Please choose INR or contact sales.",
      );
      return;
    }
    setLoadingPlan(plan.key);
    try {
      const order = await createPaymentOrderApi(
        PLAN_IDS[plan.key],
        period,
        currency,
      );
      await initRazorpayCheckout({
        order_id: order.order_id,
        amount: order.amount,
        currency: order.currency,
        key_id: order.key_id,
        prefill: {},
        onPaymentSuccess: async (response) => {
          try {
            const verified = await verifyPaymentApi(
              response.razorpay_order_id,
              response.razorpay_payment_id,
              response.razorpay_signature,
              PLAN_IDS[plan.key],
              0,
              period,
            );
            if (!verified?.success)
              throw new Error("Payment verification failed.");
            setSuccess(`Successfully updated to ${plan.name}.`);
            dispatch(fetchCurrentPricing());
          } catch (paymentError) {
            setError(paymentError.message || "Payment verification failed.");
          } finally {
            setLoadingPlan(null);
          }
        },
        onPaymentError: async (paymentError) => {
          setError(
            paymentError?.description || "Payment failed. Please try again.",
          );
          setLoadingPlan(null);
          try {
            await apiRequest("/payments/mark-failed", {
              method: "POST",
              body: JSON.stringify({ razorpay_order_id: order.order_id }),
            });
          } catch {}
        },
      });
    } catch (requestError) {
      setError(requestError.message || "Unable to start checkout.");
      setLoadingPlan(null);
    }
  };
  const amount = (plan) => {
    if (plan.key === "free_trial") return 0;
    const field =
      currency === "INR"
        ? period === "yearly"
          ? "yearlyPrice"
          : "monthlyPrice"
        : period === "yearly"
          ? "yearlyPriceUsd"
          : "monthlyPriceUsd";
    return Number(plan[field] || 0);
  };
  return (
    <div className="bg-surface-subtle">
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[.18em] text-brand-700">
            Pricing
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-text-primary sm:text-5xl">
            Plans that make limits clear.
          </h1>
          <p className="mt-5 text-lg leading-8 text-text-secondary">
            Start with Free, choose paid allowances when your workflow needs
            them, or talk to us about a tailored setup. INR prices exclude
            applicable GST.
          </p>
          <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Toggle
              label="Currency"
              value={currency}
              onChange={setCurrency}
              options={["INR", "USD"]}
            />
            <Toggle
              label="Billing"
              value={period}
              onChange={setPeriod}
              options={["monthly", "yearly"]}
            />
          </div>
          {period === "yearly" ? (
            <p className="mt-3 text-sm font-semibold text-success-dark">
              Annual billing: 12 months for the price of 11.
            </p>
          ) : null}
          {currency === "USD" ? (
            <p className="mt-3 text-sm text-text-muted">
              USD prices are displayed for planning. USD checkout is currently
              unavailable.
            </p>
          ) : null}
        </div>
        {error ? (
          <Alert
            className="mx-auto mt-8 max-w-3xl"
            variant="error"
            message={error}
            onDismiss={() => setError("")}
          />
        ) : null}
        {success ? (
          <Alert
            className="mx-auto mt-8 max-w-3xl"
            variant="success"
            message={success}
            onDismiss={() => setSuccess("")}
          />
        ) : null}
        <div className="mt-12 grid gap-5 md:grid-cols-2 xl:grid-cols-5">
          {loading ? (
            <PricingSkeleton />
          ) : (
            plans.map((plan) => (
              <PlanCard
                key={plan.key}
                plan={plan}
                amount={amount(plan)}
                currency={currency}
                period={period}
                authenticated={authenticated}
                currentPlan={currentPlan}
                loading={loadingPlan === plan.key}
                onSelect={() => choosePlan(plan)}
              />
            ))
          )}
          <CustomCard />
        </div>
        <Comparison plans={plans} />
        <div className="mx-auto mt-12 max-w-4xl rounded-2xl border border-border bg-surface p-6 text-sm leading-6 text-text-secondary">
          <p>
            <strong className="text-text-primary">
              Credits and automatic tracking:
            </strong>{" "}
            monthly plan credits include a protected automatic-tracking
            allocation where a plan provides it. Remaining spendable credits are
            for eligible optional actions. Purchased top-up credits are tracked
            separately.
          </p>
          <p className="mt-3">
            <strong className="text-text-primary">GST:</strong> INR checkout
            applies the existing GST calculation. USD checkout is disabled
            pending payment-provider and international tax readiness.
          </p>
        </div>
      </section>
    </div>
  );
}

function Toggle({ label, value, onChange, options }) {
  return (
    <fieldset className="inline-flex rounded-xl border border-border bg-surface p-1">
      <legend className="sr-only">{label}</legend>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={value === option}
          onClick={() => onChange(option)}
          className={`rounded-lg px-3 py-2 text-sm font-semibold capitalize focus:outline-none focus:ring-4 focus:ring-brand-100 ${value === option ? "bg-brand-600 text-white" : "text-text-secondary hover:bg-surface-muted"}`}
        >
          {option === "yearly" ? "Annually" : option}
        </button>
      ))}
    </fieldset>
  );
}
function PlanCard({
  plan,
  amount,
  currency,
  period,
  authenticated,
  currentPlan,
  loading,
  onSelect,
}) {
  const limits = plan.limits || {};
  const isCurrent = currentPlan === plan.key;
  const above = (ORDER[plan.key] ?? -1) > (ORDER[currentPlan] ?? -1);
  return (
    <Card
      padding="p-6"
      className={`flex min-h-[34rem] flex-col ${plan.highlighted ? "border-brand-500 ring-1 ring-brand-500" : ""}`}
    >
      <div>
        <p className="text-lg font-bold text-text-primary">{plan.name}</p>
        <p className="mt-2 min-h-12 text-sm leading-5 text-text-secondary">
          {plan.description}
        </p>
        <div className="mt-5">
          <span className="text-3xl font-bold text-text-primary">
            {currency === "INR" ? "₹" : "$"}
            {amount.toLocaleString("en-IN")}
          </span>
          <span className="ml-1 text-sm text-text-muted">
            {amount === 0 ? "" : period === "yearly" ? "/ year" : "/ month"}
          </span>
          {period === "yearly" && amount > 0 ? (
            <p className="mt-1 text-xs text-success-dark">1 month free</p>
          ) : null}
        </div>
      </div>
      <ul className="mt-6 space-y-3 text-sm">
        <Feature
          text={`${plan.domain_limit} project${plan.domain_limit === 1 ? "" : "s"}`}
        />
        <Feature text={`${limits.keywordLimit || 0} keywords`} />
        <Feature text={`${limits.monthlyCredits || 0} monthly credits`} />
        <Feature
          text={
            limits.automaticCredits
              ? `${limits.automaticCredits} automatic tracking credits`
              : "Automatic tracking unavailable"
          }
          available={Boolean(limits.automaticCredits)}
        />
        <Feature
          text={
            limits.manualRefreshLimit
              ? `Manual Refresh: ${limits.manualRefreshLimit} keywords / cycle`
              : "Manual Refresh unavailable"
          }
          available={Boolean(limits.manualRefreshLimit)}
        />
        <Feature
          text={
            limits.keywordResearchLimit
              ? `Keyword Research: ${limits.keywordResearchLimit} reports / cycle`
              : "Keyword Research unavailable"
          }
          available={Boolean(limits.keywordResearchLimit)}
        />
        <Feature
          text={
            limits.competitorSpyLimit
              ? `Competitor Spy: ${limits.competitorSpyLimit} reports / cycle`
              : "Competitor Spy unavailable"
          }
          available={Boolean(limits.competitorSpyLimit)}
        />
      </ul>
      <div className="mt-auto pt-6">
        {isCurrent ? (
          <Button className="w-full" variant="outline" disabled>
            Current plan
          </Button>
        ) : (
          <Button
            className="w-full"
            variant={plan.highlighted ? "primary" : "outline"}
            loading={loading}
            onClick={onSelect}
          >
            {plan.key === "free_trial"
              ? "Start Free"
              : !authenticated
                ? "Get started"
                : above
                  ? `Choose ${plan.name}`
                  : `Switch to ${plan.name}`}
          </Button>
        )}
      </div>
    </Card>
  );
}
function Feature({ text, available = true }) {
  const Icon = available ? Check : X;
  return (
    <li
      className={`flex gap-2 ${available ? "text-text-secondary" : "text-text-muted"}`}
    >
      <Icon
        className={`mt-0.5 h-4 w-4 shrink-0 ${available ? "text-success-dark" : "text-text-muted"}`}
        aria-hidden="true"
      />
      <span>{text}</span>
    </li>
  );
}
function CustomCard() {
  return (
    <Card
      padding="p-6"
      className="flex min-h-[34rem] flex-col bg-surface-subtle"
    >
      <div>
        <p className="text-lg font-bold text-text-primary">Custom</p>
        <p className="mt-2 min-h-12 text-sm leading-5 text-text-secondary">
          Need higher limits or a tailored setup? Contact us to discuss your
          requirements.
        </p>
        <p className="mt-5 text-3xl font-bold text-text-primary">
          Custom pricing
        </p>
      </div>
      <ul className="mt-6 space-y-3 text-sm text-text-secondary">
        <Feature text="Sales-assisted plan" />
        <Feature text="Limits agreed with your team" />
        <Feature text="No self-service checkout" available={false} />
      </ul>
      <div className="mt-auto pt-6">
        <Link to="/contact">
          <Button
            className="w-full"
            rightIcon={<ArrowRight className="h-4 w-4" />}
          >
            Contact sales
          </Button>
        </Link>
      </div>
    </Card>
  );
}
function Comparison({ plans }) {
  const rows = [
    ["Projects", (p) => p.domain_limit],
    ["Keywords", (p) => p.limits?.keywordLimit || 0],
    [
      "Automatic tracking",
      (p) => (p.limits?.automaticCredits ? "Included" : "Unavailable"),
    ],
    [
      "Manual Refresh",
      (p) =>
        p.limits?.manualRefreshLimit
          ? `${p.limits.manualRefreshLimit} / cycle`
          : "Unavailable",
    ],
    [
      "Keyword Research",
      (p) =>
        p.limits?.keywordResearchLimit
          ? `${p.limits.keywordResearchLimit} / cycle`
          : "Unavailable",
    ],
    [
      "Competitor Spy",
      (p) =>
        p.limits?.competitorSpyLimit
          ? `${p.limits.competitorSpyLimit} / cycle`
          : "Unavailable",
    ],
    ["Monthly credits", (p) => p.limits?.monthlyCredits || 0],
  ];
  return (
    <section className="mt-16">
      <h2 className="text-2xl font-bold tracking-tight text-text-primary">
        Compare plan allowances
      </h2>
      <div className="mt-6 overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="min-w-[46rem] w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-subtle">
              <th className="px-4 py-3 font-semibold text-text-primary">
                Feature
              </th>
              {plans.map((p) => (
                <th
                  key={p.key}
                  className="px-4 py-3 font-semibold text-text-primary"
                >
                  {p.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, get]) => (
              <tr key={label} className="border-b border-border last:border-0">
                <th className="px-4 py-3 font-medium text-text-secondary">
                  {label}
                </th>
                {plans.map((p) => (
                  <td key={p.key} className="px-4 py-3 text-text-primary">
                    {get(p)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
function PricingSkeleton() {
  return (
    <>
      {[1, 2, 3, 4].map((n) => (
        <Card key={n} padding="p-6" className="min-h-[34rem]">
          <div className="h-6 w-24 animate-pulse rounded bg-surface-muted" />
          <div className="mt-5 h-10 w-32 animate-pulse rounded bg-surface-muted" />
        </Card>
      ))}
    </>
  );
}
