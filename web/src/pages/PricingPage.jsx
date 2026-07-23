import { useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  changePlan,
  checkPlanChange,
  fetchCurrentPricing,
  fetchPricingPlans,
} from "../features/pricing/pricingSlice";
import { isAuthenticated } from "../utils/auth";
import { PLAN_COMPARISON, PLANS } from "../config/pricing";

const PLAN_ORDER = {
  starter: 1,
  pro: 2,
  agency: 3,
};

const formatDate = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString();
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

  const handleSelectPlan = (planKey) => {
    const normalizedPlanKey = (planKey || "").toLowerCase();

    if (!authenticated) {
      navigate(`/register?plan=${normalizedPlanKey}`);
      return;
    }

    if (normalizedPlanKey === currentPlan || changingPlan) return;

    dispatch(changePlan(normalizedPlanKey))
      .unwrap()
      .then(() => {
        dispatch(fetchCurrentPricing());
      })
      .catch(() => {});
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

          {error ? (
            <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </div>

        {authenticated ? (
          <div className="mt-12 grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">Current subscription</h2>
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
                  <dt className="text-sm text-slate-500">Trial ends</dt>
                  <dd className="mt-1 text-lg font-semibold text-slate-900">
                    {formatDate(current?.trialEndsAt)}
                  </dd>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <dt className="text-sm text-slate-500">Trial length</dt>
                  <dd className="mt-1 text-lg font-semibold text-slate-900">
                    {resolvedTrialDays} days
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
              Manual plan switching is enabled for now while payment integration is pending.
            </p>
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
                        <span className="text-4xl font-bold text-slate-900">${plan.monthlyPrice}</span>
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

                    <button
                      type="button"
                      onClick={() => handleSelectPlan(targetPlan)}
                      disabled={isCurrent || changingPlan || showDowngradeWarning}
                      className={`mt-5 w-full rounded-xl px-4 py-2 text-sm font-semibold transition ${
                        isCurrent || showDowngradeWarning
                          ? "cursor-not-allowed bg-slate-200 text-slate-500"
                          : "bg-indigo-600 text-white hover:bg-indigo-700"
                      }`}
                    >
                      {isCurrent
                        ? "Current Plan"
                        : changingPlan && authenticated
                        ? "Updating..."
                        : showDowngradeWarning
                        ? "Resolve limits first"
                        : authenticated
                        ? `Switch to ${plan.name}`
                        : `Start ${plan.name} Trial`}
                    </button>
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
    </div>
  );
}