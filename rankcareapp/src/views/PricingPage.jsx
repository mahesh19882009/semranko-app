'use client'
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "../lib/navigation";
import { isAuthenticated } from "../utils/auth";
import { initRazorpayCheckout, apiRequest } from "../lib/api";
import { createPaymentOrderApi, verifyPaymentApi } from "../features/pricing/pricingApi";
import { useSelector, useDispatch } from "react-redux";
import Alert from "../components/ui/Alert";
import { fetchCurrentPricing } from "../features/pricing/pricingSlice";

const PLAN_ORDER = {
  free_trial: 0,
  starter: 1,
  pro: 2,
  agency: 3,
  enterprise: 4,
};

const PLAN_ID_MAP = {
  starter: 0,
  pro: 1,
  agency: 2,
};

export default function PricingPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    setAuthenticated(isAuthenticated());
    if (isAuthenticated()) {
      dispatch(fetchCurrentPricing());
    }
  }, [dispatch]);

  const [loadingPlan, setLoadingPlan] = useState(null);
  const [paymentError, setPaymentError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [faqs, setFaqs] = useState([]);
  const [loadingFaqs, setLoadingFaqs] = useState(true);
  const [openFaq, setOpenFaq] = useState(null);

  const pricingCurrent = useSelector((state) => state.pricing.current);
  const pricingLoading = useSelector((state) => state.pricing.loading);
  const pricingPlans = useSelector((state) => state.pricing.plans);

  const currentPlan = pricingCurrent?.plan || null;
  const currentCreditBalance = pricingCurrent?.creditBalance;

  const plans = pricingPlans || [];

  useEffect(() => {
    let cancelled = false;
    setLoadingFaqs(true);
    fetch("/api/marketing/pricing-faqs")
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled && Array.isArray(data)) {
          setFaqs(data);
        }
      })
      .catch(() => { })
      .finally(() => {
        if (!cancelled) setLoadingFaqs(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelectPlan = async (planKey) => {
    setPaymentError(null);
    setSuccessMessage(null);

    if (planKey === "enterprise") {
      window.location.href = "mailto:sales@rankcare.com?subject=Enterprise Plan Inquiry";
      return;
    }

    if (!authenticated) {
      navigate("/register");
      return;
    }

    const plan = plans.find((p) => p.key === planKey);
    if (!plan) return;

    if (planKey === "free_trial") {
      navigate("/dashboard");
      return;
    }

    setLoadingPlan(planKey);
    try {
      const planId = PLAN_ID_MAP[planKey];
      const amount = plan.monthlyPrice * 100;
      const order = await createPaymentOrderApi(planId, amount);

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
              response.razorpay_signature,
              planId,
              0
            );
            if (verifyResult?.success) {
              setSuccessMessage(`Successfully upgraded to ${plan.name}!`);
              dispatch(fetchCurrentPricing());
              setTimeout(() => navigate("/dashboard"), 1500);
            } else {
              setPaymentError("Payment verification failed. Please contact support.");
            }
          } catch (err) {
            setPaymentError(err.message || "Payment verification failed");
          } finally {
            setLoadingPlan(null);
          }
        },
        onPaymentError: async (error) => {
          setPaymentError(error?.description || "Payment failed. Please try again.");
          setLoadingPlan(null);

          try {
            if (order?.order_id) {
              await apiRequest("/payments/mark-failed", {
                method: "POST",
                body: JSON.stringify({ razorpay_order_id: order.order_id }),
              });
            }
          } catch (err) {
            console.error("Failed to mark payment as failed:", err);
          }
        },
      });
    } catch (err) {
      setPaymentError(err.message || "Failed to initiate payment");
      setLoadingPlan(null);
    }
  };

  const toggleFaq = (index) => {
    setOpenFaq(openFaq === index ? null : index);
  };

  const displayedCreditBalance = useMemo(() => {
    if (currentCreditBalance !== null && currentCreditBalance !== undefined) {
      return currentCreditBalance;
    }
    return pricingLoading ? null : 0;
  }, [currentCreditBalance, pricingLoading]);

  const renderPlanFeatures = (plan) => {
    const limits = plan.limits || {};
    const features = [];
    if (limits.monthlyCredits) {
      features.push(`${limits.monthlyCredits.toLocaleString('en-US')} monthly credits`);
    }
    if (limits.keywordLimit) {
      features.push(`Track up to ${limits.keywordLimit.toLocaleString('en-US')} keywords`);
    }
    if (limits.competitorsPerProject) {
      features.push(`${limits.competitorsPerProject} competitors per project`);
    }
    if (plan.domain_limit) {
      features.push(`${plan.domain_limit} project domain${plan.domain_limit > 1 ? 's' : ''}`);
    }
    if (plan.refreshFrequency) {
      features.push(`${plan.refreshFrequency.charAt(0).toUpperCase() + plan.refreshFrequency.slice(1)} refresh`);
    }
    return features;
  };

  return (
    <div className="bg-slate-50">
      <div className="mx-auto max-w-7xl px-6 py-16">
        {/* Trial Banner / Current Plan Banner */}
        <div className="mx-auto max-w-3xl text-center">
          {authenticated && currentPlan ? (
            <div className="inline-flex items-center gap-3 rounded-full bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700">
              <span>Current Plan: {currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1)}</span>
              <span className="text-emerald-400">|</span>
              <span>
                Credits: {displayedCreditBalance !== null ? displayedCreditBalance.toLocaleString('en-US') : '...'}
              </span>
            </div>
          ) : (
            <Link
              to="/register"
              className="inline-flex items-center gap-2 rounded-full bg-indigo-50 px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-100"
            >
              Start Free Trial — No credit card required
            </Link>
          )}
        </div>

        {/* Pricing Header */}
        <div className="mx-auto max-w-3xl text-center mt-12">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
            Simple plans for growing SEO workflows
          </h1>
          <p className="mt-4 text-lg text-slate-600">
            Start with a free trial and choose the plan that fits your SEO workflow.
          </p>
        </div>

        {/* Pricing Grid */}
        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3 justify-center">
          {plans.map((plan) => {
            const isEnterprise = plan.key === "enterprise";
            const discountPct = plan.individual_discount_pct || 0;
            const basePrice = plan.monthlyPrice;
            const discountedPrice = discountPct > 0 ? basePrice * (1 - discountPct / 100) : basePrice;
            const cleanDisplayPrice = Number.isInteger(discountedPrice) ? discountedPrice : Math.round(discountedPrice);
            const priceDisplay = isEnterprise
              ? "Custom"
              : `₹${cleanDisplayPrice.toLocaleString('en-US')} / month`;
            const isCurrentPlan = authenticated && currentPlan === plan.key;
            const currentPlanOrder = currentPlan ? PLAN_ORDER[currentPlan] : -1;
            const planOrder = PLAN_ORDER[plan.key];
            const isLowerTier = currentPlanOrder > -1 && planOrder < currentPlanOrder;
            const isHigherTier = currentPlanOrder > -1 && planOrder > currentPlanOrder;

            return (
              <div
                key={plan.key}
                className={`relative flex flex-col rounded-2xl border bg-white p-6 shadow-sm ${isCurrentPlan
                  ? "border-emerald-500 ring-1 ring-emerald-500"
                  : plan.highlighted
                    ? "border-indigo-600 ring-1 ring-indigo-600"
                    : "border-slate-200"
                  }`}
              >
                {isCurrentPlan && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold text-white">
                      Current Plan
                    </span>
                  </div>
                )}
                {isLowerTier && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="rounded-full bg-slate-400 px-3 py-1 text-xs font-semibold text-white">
                      Managed Plan
                    </span>
                  </div>
                )}
                {plan.highlighted && !isCurrentPlan && !isLowerTier && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="rounded-full bg-indigo-600 px-3 py-1 text-xs font-semibold text-white">
                      Best Value
                    </span>
                  </div>
                )}

                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-slate-900">{plan.name}</h3>
                  <p className="mt-1 text-sm text-slate-500">{plan.description}</p>
                </div>

                <div className="mb-6">
                  {discountPct > 0 && !isEnterprise ? (
                    <div className="flex flex-col gap-1">
                      <span className="text-sm text-slate-400 line-through">
                        ₹{basePrice.toLocaleString('en-US')}
                      </span>
                      <span className="text-3xl font-bold text-slate-900">{priceDisplay}</span>
                      <span className="text-xs font-medium text-emerald-600">
                        Save {discountPct}%
                      </span>
                    </div>
                  ) : (
                    <>
                      <span className="text-3xl font-bold text-slate-900">{priceDisplay}</span>
                      {!isEnterprise && (
                        <span className="text-sm text-slate-500">/ month</span>
                      )}
                    </>
                  )}
                </div>

                <div className="mb-6 rounded-xl bg-slate-50 p-4">
                  <p className="text-sm font-medium text-slate-700">
                    {plan.limits?.monthlyCredits ? `${plan.limits.monthlyCredits.toLocaleString('en-US')} Monthly Credits` : 'Custom Credits'}
                  </p>
                  <ul className="mt-3 space-y-2 text-sm text-slate-600">
                    {renderPlanFeatures(plan).map((feature, idx) => (
                      <li key={idx} className="flex items-center gap-2">
                        <span className="text-indigo-600">✓</span>
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>

                {isCurrentPlan ? (
                  <button
                    disabled
                    className="w-full rounded-xl px-4 py-3 text-sm font-semibold cursor-default bg-emerald-50 text-emerald-700"
                  >
                    Current Plan
                  </button>
                ) : isLowerTier ? (
                  <button
                    disabled
                    className="w-full rounded-xl px-4 py-3 text-sm font-semibold cursor-default bg-slate-100 text-slate-500"
                  >
                    Managed Plan
                  </button>
                ) : (
                  <button
                    onClick={() => handleSelectPlan(plan.key)}
                    disabled={loadingPlan === plan.key}
                    className={`w-full rounded-xl px-4 py-3 text-sm font-semibold transition ${plan.highlighted
                      ? "bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60"
                      : "bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-60"
                      }`}
                  >
                    {loadingPlan === plan.key
                      ? "Processing..."
                      : !authenticated
                        ? (plan.key === "free_trial" ? "Start Free Trial" : "Get Started")
                        : isHigherTier
                          ? `Upgrade to ${plan.name}`
                          : plan.cta
                    }
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* FAQ Section */}
        <div className="mt-20">
          <h2 className="text-center text-2xl font-bold text-slate-900">Pricing FAQs</h2>
          <p className="mt-2 text-center text-sm text-slate-500">
            Everything you need to know about credits and billing.
          </p>

          <div className="mx-auto mt-8 max-w-3xl">
            {loadingFaqs ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 animate-pulse rounded-xl bg-slate-200" />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {faqs.map((faq, index) => (
                  <div
                    key={index}
                    className="rounded-xl border border-slate-200 bg-white"
                  >
                    <button
                      onClick={() => toggleFaq(index)}
                      className="flex w-full items-center justify-between px-5 py-4 text-left"
                    >
                      <span className="text-sm font-semibold text-slate-900">{faq.q}</span>
                      <span className="ml-4 text-slate-400 transition-transform">
                        {openFaq === index ? "−" : "+"}
                      </span>
                    </button>
                    {openFaq === index && (
                      <div className="px-5 pb-4">
                        <p className="text-sm text-slate-600">{faq.a}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Alerts */}
        {paymentError && (
          <div className="mx-auto mt-8 max-w-3xl">
            <Alert variant="error" message={paymentError} />
          </div>
        )}
        {successMessage && (
          <div className="mx-auto mt-8 max-w-3xl">
            <Alert variant="success" message={successMessage} />
          </div>
        )}
      </div>
    </div>
  );
}
