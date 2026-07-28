import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  changePlan,
  checkPlanChange,
  fetchCurrentPricing,
  fetchPricingPlans,
} from "../features/pricing/pricingSlice";
import { createPaymentOrderApi, verifyPaymentApi, markPaymentFailedApi } from "../features/pricing/pricingApi";
import { initRazorpayCheckout } from "../lib/api";
import { isAuthenticated } from "../utils/auth";
import { PLAN_COMPARISON, PLANS } from "../config/pricing";
import ConfirmModal from "../components/ConfirmModal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCreditCard,
  faShieldHalved,
  faXmark,
  faCircleCheck,
  faCircleExclamation,
  faWallet,
  faClock,
} from "@fortawesome/free-solid-svg-icons";

const PLAN_ORDER = {
  starter: 1,
  pro: 2,
  agency: 3,
};

const GST_RATE = 0.18;

const formatDate = (value) => {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}-${month}-${year}`;
};

const getDaysLeft = (value) => {
  if (!value) return null;
  const end = new Date(value);
  if (Number.isNaN(end.getTime())) return null;
  const now = new Date();
  const diff = end.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
};

const UsageRow = ({ label, used = 0, allowed = 0 }) => {
  const percent = allowed > 0 ? Math.min(100, Math.round((used / allowed) * 100)) : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>{label}</span>
        <span>
          {used} / {allowed}
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-200">
        <div
          className={`h-2 rounded-full ${percent >= 100 ? "bg-red-500" : "bg-indigo-600"}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};

export default function PricingPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const authenticated = isAuthenticated();
  
  const [isProcessingPayment, setIsProcessingPayment] = useState(false);
  const [selectedBillingCycle, setSelectedBillingCycle] = useState("monthly");

  // Confirmation Modal state for plan switches/upgrades
  const [pendingPlanAction, setPendingPlanAction] = useState(null);

  // Mock Razorpay Checkout UI Modal state (used in dev mode when keys are missing)
  const [mockPaymentSession, setMockPaymentSession] = useState(null);
  const [isSubmittingMockPayment, setIsSubmittingMockPayment] = useState(false);

  // Inline Success & Error banners
  const [successMessage, setSuccessMessage] = useState(null);
  const [paymentError, setPaymentError] = useState(null);

  const {
    plans,
    current,
    trialDays,
    loadingPlans,
    loadingCurrent,
    changingPlan,
    error,
    changePlanValidation,
  } = useSelector((state) => state.pricing);

  useEffect(() => {
    dispatch(fetchPricingPlans());
    if (authenticated) {
      dispatch(fetchCurrentPricing());
    }
  }, [dispatch, authenticated]);

  const displayPlans = Array.isArray(plans) && plans.length > 0 ? plans : PLANS;
  const currentPlan = (current?.plan || "").toLowerCase();
  const usage = current?.usage || {};
  const limits = current?.limits || {};
  const resolvedTrialDays = current?.trialDays ?? trialDays ?? 10;
  const daysLeft = getDaysLeft(current?.trialEndsAt);
  const userCreditBalance = current?.creditBalance || 0;

  useEffect(() => {
    if (!authenticated || !currentPlan || !displayPlans.length) return;

    displayPlans.forEach((plan) => {
      const targetPlan = (plan.key || "").toLowerCase();
      const isLowerPlan = PLAN_ORDER[targetPlan] < PLAN_ORDER[currentPlan];

      if (targetPlan !== currentPlan && isLowerPlan) {
        dispatch(checkPlanChange(targetPlan));
      }
    });
  }, [dispatch, authenticated, currentPlan, displayPlans]);

  const heroText = useMemo(() => {
    if (!authenticated) {
      return `Start with a ${resolvedTrialDays}-day trial and choose the plan that fits your SEO workflow.`;
    }
    if (current?.subscriptionStatus === "trialing") {
      return daysLeft === 0
        ? "Your trial ends today. Pick the right plan to continue without interruption."
        : `You are currently on trial with ${daysLeft ?? "—"} day(s) left.`;
    }
    return "Manage your current plan, monitor usage, and switch plans when needed.";
  }, [authenticated, current?.subscriptionStatus, daysLeft, resolvedTrialDays]);

  // Request Confirmation for Free Plan Switch / Downgrade
  const handleRequestSelectPlan = (plan) => {
    const normalizedPlanKey = (plan.key || "").toLowerCase();

    if (!authenticated) {
      navigate(`/register?plan=${normalizedPlanKey}`);
      return;
    }

    if (normalizedPlanKey === currentPlan || changingPlan) return;

    setSuccessMessage(null);
    setPaymentError(null);

    setPendingPlanAction({
      type: "downgrade",
      planKey: normalizedPlanKey,
      planName: plan.name,
    });
  };

  // Request Confirmation for Paid Plan Upgrade
  const handleRequestUpgradeWithPayment = (plan, billingCycle = "monthly") => {
    const planKey = (plan.key || "").toLowerCase();

    if (!authenticated) {
      navigate(`/register?plan=${planKey}`);
      return;
    }

    if (isProcessingPayment) return;

    const price = billingCycle === "yearly" ? plan.yearlyPrice : plan.monthlyPrice;
    const totalPrice = price * (1 + GST_RATE);
    const priceInPaise = Math.round(totalPrice * 100);
    const appliedCredit = Math.min(totalPrice, userCreditBalance);
    const netPrice = Math.max(0, totalPrice - appliedCredit);

    setSuccessMessage(null);
    setPaymentError(null);
    setPendingPlanAction({
      type: "upgrade",
      planKey,
      planName: plan.name,
      billingCycle,
      price: totalPrice,
      appliedCredit,
      netPrice,
      amount: priceInPaise,
    });
  };

  // Confirmed in Modal -> Execute Action
  const handleConfirmPlanAction = async () => {
    if (!pendingPlanAction) return;

    const action = pendingPlanAction;
    setPendingPlanAction(null);

    if (action.type === "downgrade") {
      dispatch(changePlan(action.planKey))
        .unwrap()
        .then(() => {
          dispatch(fetchCurrentPricing());
          setSuccessMessage(`Your plan will be changed to ${action.planName} at the end of your current billing period.`);
        })
        .catch((err) => {
          setPaymentError(err?.message || "Failed to schedule plan change.");
        });
    } else if (action.type === "upgrade") {
      executeUpgradeWithPayment(action.planKey, action.billingCycle, action.planName, action.price, action.amount, action.appliedCredit);
    }
  };

  const executeUpgradeWithPayment = async (planKey, billingCycle, planName, price, amount, creditApplied = 0) => {
    const planIndex = { starter: 0, pro: 1, agency: 2 }[planKey];

    try {
      setIsProcessingPayment(true);
      
      // Create payment order
      const orderData = await createPaymentOrderApi(planIndex, amount);
      
      if (!orderData) {
        throw new Error("Failed to create payment order");
      }

      // 100% Covered by Account Credit Balance
      if (orderData.is_fully_credited) {
        dispatch(fetchCurrentPricing());
        const proratedMsg = orderData.prorated_discount > 0 
          ? ` Prorated discount: ₹${orderData.prorated_discount.toLocaleString('en-IN')}.` 
          : '';
        setSuccessMessage(`Plan upgraded to ${planName}!${proratedMsg} Applied ₹${orderData.credit_applied} account credit (Remaining balance: ₹${orderData.remaining_credit}).`);
        setIsProcessingPayment(false);
        return;
      }

      if (orderData.is_mock) {
        // DEVELOPMENT MODE (No Razorpay keys configured): Show Mock Razorpay Checkout UI Modal
        setMockPaymentSession({
          orderData,
          planKey,
          planIndex,
          planName,
          price,
          amount: orderData.net_amount || amount,
          netPrice: (orderData.net_amount ? orderData.net_amount / 100 : price),
          creditApplied: orderData.credit_applied || creditApplied,
          proratedDiscount: orderData.prorated_discount || 0,
          billingCycle,
        });
        setIsProcessingPayment(false);
      } else {
        // PRODUCTION / TEST MODE with Razorpay Keys: Initialize official Razorpay Checkout SDK
        await initRazorpayCheckout({
          order_id: orderData.order_id,
          amount: orderData.net_amount || amount,
          currency: orderData.currency || "INR",
          key_id: orderData.key_id,
          prefill: {
            name: current?.user?.name || "RankCare User",
            email: current?.user?.email || "",
            contact: "9999999999",
          },
          onPaymentSuccess: async (response) => {
            try {
              await verifyPaymentApi(
                response.razorpay_order_id,
                response.razorpay_payment_id,
                response.razorpay_signature,
                planIndex,
                orderData.credit_applied || creditApplied
              );
              
              dispatch(fetchCurrentPricing());
              const proratedMsg = orderData.prorated_discount > 0 
                ? ` Prorated discount: ₹${orderData.prorated_discount.toLocaleString('en-IN')}.` 
                : '';
              setSuccessMessage(`Payment successful! Your ${planName} subscription has been activated.${proratedMsg}`);
            } catch (error) {
              console.error("Payment verification failed:", error);
              setPaymentError("Payment verification failed. Please contact support with payment ID: " + response.razorpay_payment_id);
            } finally {
              setIsProcessingPayment(false);
            }
          },
          onPaymentError: async (error) => {
            console.error("Payment failed:", error);
            const desc = error?.description || error?.reason || "Payment failed or was cancelled.";
            setPaymentError(`${desc} (Test Tip: In Razorpay test mode, choose Netbanking or UPI vpa "success@razorpay" to complete test payment).`);
            setIsProcessingPayment(false);

            const failedOrderId = error?.metadata?.order_id;
            if (failedOrderId) {
              try {
                await markPaymentFailedApi(failedOrderId);
              } catch (e) {
                console.error("Failed to mark payment as failed:", e);
              }
            }
          },
        });
      }
    } catch (error) {
      console.error("Payment initialization failed:", error);
      setPaymentError("Failed to initialize payment: " + (error.message || "Unknown error"));
      setIsProcessingPayment(false);
    }
  };

  // Called from Mock Razorpay Checkout UI Modal on "Complete Test Payment"
  const handleSimulateMockPayment = async () => {
    if (!mockPaymentSession || isSubmittingMockPayment) return;

    const { orderData, planIndex, planName, creditApplied } = mockPaymentSession;
    const orderSuffix = (orderData.order_id || "").split("_").pop() || "dev";
    const mockPaymentId = "mock_pay_" + orderSuffix;
    const mockSignature = "mock_sig_" + orderSuffix;

    try {
      setIsSubmittingMockPayment(true);
      await verifyPaymentApi(
        orderData.order_id,
        mockPaymentId,
        mockSignature,
        planIndex,
        creditApplied
      );

      dispatch(fetchCurrentPricing());
      setSuccessMessage(`Payment successful! Your ${planName} subscription has been activated.`);
      setMockPaymentSession(null);
    } catch (error) {
      console.error("Mock payment verification failed:", error);
      setPaymentError("Payment verification failed: " + (error.message || "Unknown error"));
    } finally {
      setIsSubmittingMockPayment(false);
      setIsProcessingPayment(false);
    }
  };

  const handleCancelMockPayment = () => {
    setMockPaymentSession(null);
    setIsProcessingPayment(false);
    setPaymentError("Payment process was cancelled.");
  };

  return (
    <div className="bg-slate-50">
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex rounded-full bg-indigo-100 px-4 py-1 text-sm font-semibold text-indigo-700">
            RankCare Pricing
          </span>
          <h1 className="mt-6 text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
            Simple plans for growing SEO teams
          </h1>
          <p className="mt-4 text-lg text-slate-600">{heroText}</p>

          {/* Pending Plan Change Banner */}
          {current?.pendingPlanChange && (
            <div className="mt-6 flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800 shadow-sm text-left">
              <FontAwesomeIcon icon={faClock} className="text-lg text-amber-600 shrink-0" />
              <div className="flex-1 font-medium">
                Your plan will change to {PLANS.find(p => p.key === current.pendingPlanChange)?.name || current.pendingPlanChange} at the end of your current billing period.
              </div>
            </div>
          )}

          {!authenticated ? (
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link
                to="/register"
                className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700"
              >
                Start free trial
              </Link>
              <Link
                to="/login"
                className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-white"
              >
                Login
              </Link>
            </div>
          ) : null}

          {/* Success Banner */}
          {successMessage ? (
            <div className="mt-6 flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800 shadow-sm text-left">
              <FontAwesomeIcon icon={faCircleCheck} className="text-lg text-emerald-600 shrink-0" />
              <div className="flex-1 font-medium">{successMessage}</div>
              <button
                type="button"
                onClick={() => setSuccessMessage(null)}
                className="text-emerald-600 hover:text-emerald-800"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>
          ) : null}

          {/* Error Banner */}
          {paymentError || error ? (
            <div className="mt-6 flex items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-800 shadow-sm text-left">
              <FontAwesomeIcon icon={faCircleExclamation} className="text-lg text-rose-600 shrink-0" />
              <div className="flex-1 font-medium">{paymentError || error}</div>
              <button
                type="button"
                onClick={() => setPaymentError(null)}
                className="text-rose-600 hover:text-rose-800"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>
          ) : null}
        </div>

        {authenticated ? (
          <div className="mt-12 grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">Current subscription</h2>
                {userCreditBalance > 0 && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
                    <FontAwesomeIcon icon={faWallet} />
                    Account Credit: ₹{userCreditBalance.toLocaleString('en-IN')}
                  </span>
                )}
              </div>
              <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <dt className="text-sm text-slate-500">Plan</dt>
                  <dd className="mt-1 text-lg font-semibold text-slate-900">
                    {current?.plan ? current.plan.toUpperCase() : "—"}
                  </dd>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <dt className="text-sm text-slate-500">Status</dt>
                  <dd className="mt-1 text-lg font-semibold capitalize text-slate-900">
                    {current?.subscriptionStatus || "—"}
                  </dd>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <dt className="text-sm text-slate-500">Trial / Renewal ends</dt>
                  <dd className="mt-1 text-lg font-semibold text-slate-900">
                    {formatDate(current?.trialEndsAt)}
                  </dd>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <dt className="text-sm text-slate-500">Account Balance</dt>
                  <dd className="mt-1 text-lg font-semibold text-emerald-600">
                    ₹{userCreditBalance.toLocaleString('en-IN')}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">Current usage</h2>
              <div className="mt-6 space-y-5">
                <UsageRow label="Projects" used={usage.projects ?? 0} allowed={limits.projects ?? 0} />
                <UsageRow label="Keywords" used={usage.keywords ?? 0} allowed={limits.keywords ?? 0} />
                <UsageRow
                  label="Reports this month"
                  used={usage.reportsThisMonth ?? 0}
                  allowed={limits.reportsPerMonth ?? 0}
                />
                <UsageRow
                  label="Max competitors in a project"
                  used={usage.maxCompetitorsPerProject ?? 0}
                  allowed={limits.competitorsPerProject ?? 0}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="mx-auto mt-12 max-w-3xl rounded-3xl border border-indigo-100 bg-white p-8 text-center shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Start with a free trial</h2>
            <p className="mt-3 text-slate-600">
              Every new account starts with a {trialDays}-day trial. Pick any plan now and continue
              with that plan after trial once billing is enabled.
            </p>
          </div>
        )}

        <div className="mt-16">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-slate-900">Plans</h2>
            <p className="mt-3 text-slate-600">
              Choose the perfect plan for your SEO needs. Start with a free trial, upgrade anytime.
            </p>
            
            {/* Billing cycle toggle */}
            {authenticated && (
              <div className="mt-4 flex items-center justify-center gap-2">
                <span className={`text-sm ${selectedBillingCycle === "monthly" ? "font-semibold text-indigo-600" : "text-slate-500"}`}>
                  Monthly
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedBillingCycle(selectedBillingCycle === "monthly" ? "yearly" : "monthly")}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                    selectedBillingCycle === "yearly" ? "bg-indigo-600" : "bg-slate-300"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                      selectedBillingCycle === "yearly" ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
                <span className={`text-sm ${selectedBillingCycle === "yearly" ? "font-semibold text-indigo-600" : "text-slate-500"}`}>
                  Yearly <span className="text-xs text-green-600">(Save 20%)</span>
                </span>
              </div>
            )}
          </div>

          {loadingPlans || (authenticated && loadingCurrent) ? (
            <div className="mt-10 text-center text-slate-500">Loading pricing details...</div>
          ) : (
            <div className="mt-10 grid gap-6 lg:grid-cols-3">
              {displayPlans.map((plan) => {
                const targetPlan = (plan.key || "").toLowerCase();
                const isCurrent = authenticated && currentPlan === targetPlan;
                const isLowerPlan =
                  authenticated && PLAN_ORDER[targetPlan] < PLAN_ORDER[currentPlan];
                const competitorLimit =
                  plan?.limits?.competitorsPerProject ?? plan?.limits?.competitors ?? 0;

                const validation = changePlanValidation?.[targetPlan];
                const showDowngradeWarning =
                  authenticated &&
                  !isCurrent &&
                  isLowerPlan &&
                  validation?.allowed === false;

                const violations = showDowngradeWarning ? validation?.violations || [] : [];
                
                // Calculate price based on billing cycle (in INR ₹)
                const price = selectedBillingCycle === "yearly" ? plan.yearlyPrice : plan.monthlyPrice;

                return (
                  <article
                    key={plan.key}
                    className={`rounded-3xl border p-6 shadow-sm transition ${
                      plan.highlighted
                        ? "border-indigo-200 bg-indigo-50/60"
                        : "border-slate-200 bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-xl font-semibold text-slate-900">{plan.name}</h3>
                      {isCurrent ? (
                        <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">
                          Current
                        </span>
                      ) : null}
                    </div>

                    {plan.description ? (
                      <p className="mt-3 text-sm leading-6 text-slate-600">{plan.description}</p>
                    ) : null}

                    {"monthlyPrice" in plan ? (
                      <div className="mt-6 flex items-end gap-2">
                        <span className="text-4xl font-bold text-slate-900">₹{price.toLocaleString('en-IN')}</span>
                        <span className="pb-1 text-sm text-slate-500">/ month</span>
                      </div>
                    ) : null}

                    <ul className="mt-6 space-y-3 text-sm text-slate-700">
                      <li>Projects: {plan.limits.projects}</li>
                      <li>Keywords: {plan.limits.keywords}</li>
                      <li>Competitors / project: {competitorLimit}</li>
                      <li>Reports / month: {plan.limits.reportsPerMonth}</li>
                    </ul>

                    {showDowngradeWarning ? (
                      <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4">
                        <p className="text-sm font-semibold text-amber-800">
                          Downgrade blocked. Reduce usage first:
                        </p>
                        <ul className="mt-2 space-y-2 text-sm text-amber-700">
                          {violations.map((item) => (
                            <li key={item.resource}>
                              {item.resource}: {item.used} / {item.allowed} — remove {item.remove}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    <div className="mt-5 space-y-3">
                      {/* Free plan switch (for downgrades only) */}
                      {authenticated && isLowerPlan && !showDowngradeWarning && (
                        <button
                          type="button"
                          onClick={() => handleRequestSelectPlan(plan)}
                          disabled={changingPlan}
                          className={`w-full rounded-xl px-4 py-2 text-sm font-semibold transition ${
                            changingPlan
                              ? "cursor-not-allowed bg-slate-200 text-slate-500"
                              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                          }`}
                        >
                          {changingPlan ? "Updating..." : `Switch to ${plan.name}`}
                        </button>
                      )}
                      
                      {/* Paid upgrade button */}
                      {authenticated && !isCurrent && !isLowerPlan && (
                        <button
                          type="button"
                          onClick={() => handleRequestUpgradeWithPayment(plan, selectedBillingCycle)}
                          disabled={isProcessingPayment}
                          className="w-full rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-400"
                        >
                          {isProcessingPayment ? "Processing..." : `Upgrade - ₹${price.toLocaleString('en-IN')}/mo`}
                        </button>
                      )}
                      
                      {/* Start trial button for non-authenticated users */}
                      {!authenticated && (
                        <button
                          type="button"
                          onClick={() => handleRequestSelectPlan(plan)}
                          className="w-full rounded-xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200"
                        >
                          {`Start ${plan.name} Trial`}
                        </button>
                      )}
                      
                       {/* Current plan indicator / Activate for trial users */}
                       {isCurrent && current?.subscriptionStatus === "trialing" ? (
                         <button
                           type="button"
                           onClick={() => handleRequestUpgradeWithPayment(plan, selectedBillingCycle)}
                           disabled={isProcessingPayment}
                           className="w-full rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-400"
                         >
                           {isProcessingPayment ? "Processing..." : `Activate ${plan.name} Plan`}
                         </button>
                       ) : isCurrent ? (
                         <button
                           type="button"
                           disabled
                           className="w-full rounded-xl bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-500 cursor-not-allowed"
                         >
                           Current Plan
                         </button>
                       ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>

        <div className="mt-16 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-6 py-4">
            <h2 className="text-xl font-semibold text-slate-900">Plan comparison</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-6 py-4 font-semibold">Feature</th>
                  <th className="px-6 py-4 font-semibold">Starter</th>
                  <th className="px-6 py-4 font-semibold">Pro</th>
                  <th className="px-6 py-4 font-semibold">Agency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {PLAN_COMPARISON.map((row) => (
                  <tr key={row.label}>
                    <td className="px-6 py-4 font-medium text-slate-900">{row.label}</td>
                    <td className="px-6 py-4 text-slate-600">{row.starter}</td>
                    <td className="px-6 py-4 text-slate-600">{row.pro}</td>
                    <td className="px-6 py-4 text-slate-600">{row.agency}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Confirmation Modal for Plan Switches & Upgrades */}
      <ConfirmModal
        open={Boolean(pendingPlanAction)}
        title={
          pendingPlanAction?.type === "upgrade"
            ? `Upgrade to ${pendingPlanAction?.planName}`
            : `Switch to ${pendingPlanAction?.planName}`
        }
        message={
          pendingPlanAction?.type === "upgrade"
            ? `Are you sure you want to upgrade to ${pendingPlanAction?.planName} (₹${pendingPlanAction?.price.toLocaleString('en-IN')}/${pendingPlanAction?.billingCycle === "yearly" ? "yr" : "mo"} incl. GST)?${
                pendingPlanAction?.appliedCredit > 0
                  ? ` (Account Credit applied: -₹${pendingPlanAction?.appliedCredit.toLocaleString('en-IN')} -> Net Payable: ₹${pendingPlanAction?.netPrice.toLocaleString('en-IN')})`
                   : ''
              }`
            : `Are you sure you want to switch your plan to ${pendingPlanAction?.planName}? The change will take effect at the end of your current billing period.`
        }
        confirmText={
          pendingPlanAction?.type === "upgrade" ? "Proceed to Payment" : "Confirm Plan Switch"
        }
        cancelText="Cancel"
        tone={pendingPlanAction?.type === "upgrade" ? "info" : "warning"}
        loading={changingPlan || isProcessingPayment}
        onConfirm={handleConfirmPlanAction}
        onClose={() => setPendingPlanAction(null)}
      />

      {/* Mock Razorpay Checkout UI Modal for Development Mode (when keys missing) */}
      {mockPaymentSession && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center px-4 py-6 sm:px-6">
          <button
            type="button"
            aria-label="Close mock payment screen"
            onClick={handleCancelMockPayment}
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-[2px] transition"
          />

          <div className="relative z-10 w-full max-w-md overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl">
            {/* Razorpay Brand Header */}
            <div className="bg-indigo-600 px-6 py-5 text-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-white font-bold">
                  <FontAwesomeIcon icon={faCreditCard} className="text-lg" />
                </div>
                <div>
                  <h3 className="font-bold text-base leading-tight">Razorpay Checkout</h3>
                  <p className="text-xs text-indigo-200 flex items-center gap-1 mt-0.5">
                    <FontAwesomeIcon icon={faShieldHalved} className="text-[10px]" />
                    Development Mock UI
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleCancelMockPayment}
                className="rounded-lg p-1.5 text-indigo-200 hover:bg-white/10 hover:text-white transition"
              >
                <FontAwesomeIcon icon={faXmark} className="text-lg" />
              </button>
            </div>

            {/* Order Info */}
            <div className="p-6">
              <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Merchant</span>
                  <span className="font-semibold text-slate-900">RankCare SEO Suite</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Plan</span>
                  <span className="font-semibold text-slate-900">
                    {mockPaymentSession.planName} ({mockPaymentSession.billingCycle})
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Order ID</span>
                  <span className="font-mono text-xs font-medium text-slate-600">
                    {mockPaymentSession.orderData.order_id}
                  </span>
                </div>
                {mockPaymentSession.creditApplied > 0 && (
                  <div className="flex justify-between text-sm text-emerald-600 font-medium">
                    <span>Credit Applied</span>
                    <span>-₹{mockPaymentSession.creditApplied.toLocaleString('en-IN')}</span>
                  </div>
                )}
                <div className="pt-2 border-t border-slate-200 flex justify-between items-center">
                  <span className="font-medium text-slate-700">Net Payable Amount</span>
                  <span className="text-2xl font-bold text-indigo-600">
                    ₹{mockPaymentSession.netPrice.toLocaleString('en-IN')}
                  </span>
                </div>
              </div>

              {/* Dev notice */}
              <div className="mt-4 rounded-xl bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
                <span className="font-semibold">Dev Mode Note:</span> Razorpay API keys are not set in .env. Click below to simulate completing the checkout process.
              </div>

              {/* Actions */}
              <div className="mt-6 flex flex-col gap-2.5">
                <button
                  type="button"
                  onClick={handleSimulateMockPayment}
                  disabled={isSubmittingMockPayment}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-5 py-3.5 text-sm font-semibold text-white shadow-soft transition hover:bg-indigo-700 disabled:opacity-60"
                >
                  {isSubmittingMockPayment ? (
                    <>
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Verifying Payment...
                    </>
                  ) : (
                    `Complete Test Payment (₹${mockPaymentSession.netPrice.toLocaleString('en-IN')})`
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleCancelMockPayment}
                  disabled={isSubmittingMockPayment}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}