'use client'

import { useCallback, useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { BarChart3, CreditCard, FolderKanban, Gauge, KeyRound, Sparkles } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { ErrorState } from '../components/ui/StateView';
import { Link } from '../lib/navigation';
import { apiRequest, normalizeApiError } from '../lib/api';
import { formatNumber, formatResetDate } from '../utils/formatters';

function MetricCard({ icon: Icon, label, value, hint, loading = false }) {
  return (
    <Card padding="p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-text-secondary">{label}</p>
          {loading ? <div className="mt-3 h-8 w-20 animate-pulse rounded bg-surface-muted" /> : <p className="mt-3 text-3xl font-bold tracking-tight text-text-primary">{value}</p>}
          <p className="mt-2 text-sm text-text-muted">{hint}</p>
        </div>
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700"><Icon className="h-5 w-5" aria-hidden="true" /></div>
      </div>
    </Card>
  );
}

function FeatureUsage({ label, usage, loading }) {
  const value = usage ? `${usage.used} / ${usage.limit}` : '—';
  return <MetricCard icon={Gauge} label={label} value={value} loading={loading} hint={usage ? `${usage.remaining} remaining this billing cycle` : 'Usage unavailable'} />;
}

export default function DashboardPage() {
  const projects = useSelector((state) => state.projects.list || []);
  const projectsLoading = useSelector((state) => state.projects.loading);
  const pricing = useSelector((state) => state.pricing.current);
  const pricingLoading = useSelector((state) => state.pricing.loadingCurrent);
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState(null);

  const loadOverview = useCallback(async () => {
    setOverviewLoading(true);
    setOverviewError(null);
    try {
      const response = await apiRequest('/dashboard/overview');
      setOverview(response?.data || null);
    } catch (error) {
      setOverviewError(normalizeApiError(error, 'Failed to load your account overview.'));
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  useEffect(() => { loadOverview(); }, [loadOverview]);

  const usage = pricing?.usage || overview?.usage?.usage || {};
  const limits = pricing?.limits || overview?.usage?.limits || {};
  const featureUsage = pricing?.featureUsage || overview?.usage?.featureUsage || {};
  const projectCount = overview?.projects_count ?? usage.projects ?? projects.length;
  const keywordCount = overview?.tracked_keywords_count ?? usage.keywords ?? 0;
  const keywordLimit = limits.keywordLimit;
  const planName = pricing?.effectivePlan === 'free_trial' ? 'Free' : (pricing?.effectivePlan || pricing?.plan || '—');
  const spendable = pricing?.spendableCreditsRemaining;

  return (
    <div className="space-y-6">
      <Card padding="p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-700">Account overview</p>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-text-primary">Your Semranko workspace</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">Account-wide capacity, credits, and the keyword coverage currently available to your team.</p>
          </div>
          <Link to="/billing"><Button>Manage billing</Button></Link>
        </div>
      </Card>

      {overviewError ? <ErrorState title="Account overview unavailable" description={overviewError.message} onRetry={loadOverview} /> : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Account metrics">
        <MetricCard icon={FolderKanban} label="Projects" value={`${formatNumber(projectCount)} / ${limits.domain_limit ?? '—'}`} loading={overviewLoading || projectsLoading || pricingLoading} hint="Projects in your account" />
        <MetricCard icon={KeyRound} label="Tracked keywords" value={keywordLimit != null ? `${formatNumber(keywordCount)} / ${formatNumber(keywordLimit)}` : formatNumber(keywordCount)} loading={overviewLoading || pricingLoading} hint={`${formatNumber(overview?.active_keywords_count ?? usage.activeKeywords ?? 0)} active · ${formatNumber(overview?.inactive_keywords_count ?? 0)} inactive`} />
        <MetricCard icon={CreditCard} label="Spendable credits" value={spendable != null ? formatNumber(spendable) : '—'} loading={pricingLoading} hint="Optional actions only" />
        <MetricCard icon={Sparkles} label="AIO coverage" value={formatNumber(overview?.aio_keywords_count ?? 0)} loading={overviewLoading} hint="Tracked keywords with an AI Overview" />
      </section>

      <section className="grid gap-4 lg:grid-cols-3" aria-label="Paid feature usage">
        <FeatureUsage label="Manual Refresh" usage={featureUsage.manualRefresh} loading={pricingLoading} />
        <FeatureUsage label="Keyword Research" usage={featureUsage.keywordResearch} loading={pricingLoading} />
        <FeatureUsage label="Competitor Spy" usage={featureUsage.competitorSpy} loading={pricingLoading} />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.25fr,1fr]">
        <Card padding="p-6">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-brand-50 p-2 text-brand-700"><BarChart3 className="h-5 w-5" aria-hidden="true" /></div>
            <div>
              <h2 className="text-lg font-semibold text-text-primary">Ranking snapshot</h2>
              <p className="mt-1 text-sm text-text-secondary">Only current, account-wide ranking data is shown here.</p>
            </div>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl bg-surface-subtle p-4"><p className="text-sm text-text-secondary">Average position</p><p className="mt-2 text-2xl font-bold text-text-primary">{overview?.average_rank ? `#${overview.average_rank}` : '—'}</p></div>
            <div className="rounded-xl bg-surface-subtle p-4"><p className="text-sm text-text-secondary">Active keyword coverage</p><p className="mt-2 text-2xl font-bold text-text-primary">{formatNumber(overview?.active_keywords_count ?? usage.activeKeywords ?? 0)}</p></div>
          </div>
          <p className="mt-4 text-xs leading-5 text-text-muted">Historical movement is not displayed until a reliable account-level series is available; no derived movement is invented here.</p>
        </Card>
        <Card padding="p-6">
          <h2 className="text-lg font-semibold text-text-primary">Plan & reset</h2>
          <dl className="mt-5 space-y-4 text-sm">
            <div className="flex justify-between gap-4"><dt className="text-text-secondary">Current plan</dt><dd className="font-semibold capitalize text-text-primary">{planName}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-text-secondary">Next credit reset</dt><dd className="font-semibold text-text-primary">{pricing?.nextCreditResetAt ? formatResetDate(pricing.nextCreditResetAt) : '—'}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-text-secondary">Automatic tracking</dt><dd className="font-semibold text-text-primary">{pricing?.automaticReservedRemaining != null ? `${formatNumber(pricing.automaticReservedRemaining)} reserved` : '—'}</dd></div>
            {pricing?.pendingPlanChange ? <div className="rounded-lg bg-warning-light px-3 py-2 text-warning-dark">Pending plan change: <span className="font-semibold capitalize">{pricing.pendingPlanChange}</span></div> : null}
          </dl>
        </Card>
      </section>
    </div>
  );
}
