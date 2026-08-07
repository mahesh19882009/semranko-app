'use client'
import { useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  faArrowTrendUp,
  faChartSimple,
  faFolderOpen,
} from '@fortawesome/free-solid-svg-icons';
import StatCard from '../components/StateCard';
import Card from '../components/ui/Card';
import { useNavigate } from '../lib/navigation';
import { Chart } from 'primereact/chart';
import { apiRequest } from '../lib/api';
import {
  selectStats,
  selectRankTrend,
  selectSelectedProject,
  selectDashboardLoading,
  selectDashboardError,
  selectProjectsList,
} from '../features/dashboard/dashboardSelectors';
import {
  fetchKeywordsByProject,
  fetchRankingsByProject,
  resetKeywordsForProjectChange,
} from '../features/keywords/keywordsSlice';
import {
  fetchDashboardByProject,
  resetDashboard,
} from '../features/dashboard/dashboardSlice';

function DashboardPage() {
  const dispatch = useDispatch();

  const stats = useSelector(selectStats);
  const trend = useSelector(selectRankTrend);
  const project = useSelector(selectSelectedProject);
  const allProjects = useSelector(selectProjectsList)
  const loading = useSelector(selectDashboardLoading);
  const error = useSelector(selectDashboardError);
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);
  const pricingCurrent = useSelector((state) => state.pricing.current);
  const creditBalance = pricingCurrent?.creditBalance ?? 0;

  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewError, setOverviewError] = useState(null);

  useEffect(() => {
    if (!selectedProjectId) {
      dispatch(resetKeywordsForProjectChange(null));
      dispatch(resetDashboard());
      return;
    }

    dispatch(resetKeywordsForProjectChange(selectedProjectId));
    dispatch(fetchKeywordsByProject(selectedProjectId));
    dispatch(fetchRankingsByProject(selectedProjectId));
    dispatch(fetchDashboardByProject(selectedProjectId));
  }, [dispatch, selectedProjectId]);

  useEffect(() => {
    let cancelled = false;
    setOverviewLoading(true);
    setOverviewError(null);

    apiRequest('/dashboard/overview')
      .then((response) => {
        if (!cancelled) {
          setOverview(response?.data || null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('Dashboard overview error:', err);
          setOverviewError(err.message || 'Failed to load overview');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setOverviewLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const chartData = useMemo(() => {
    if (!overview?.chart_data) return null;

    const { labels, positions, credits } = overview.chart_data;

    const hasPositionData = positions && positions.some(p => p !== null && p !== undefined);

    if (!labels || labels.length === 0) return null;

    const datasets = [];

    if (hasPositionData) {
      datasets.push({
        type: 'line',
        label: 'Average Position',
        data: positions,
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        yAxisID: 'y',
        tension: 0,
        fill: true,
      });
    }

    if (credits && credits.some(c => c > 0)) {
      datasets.push({
        type: 'line',
        label: 'Credit Usage',
        data: credits,
        yAxisID: 'y1',
        fill: true,
        borderColor: '#ffa726cc',
        tension: 0,
        backgroundColor: '#ffa72633'
      });
    }

    if (datasets.length === 0) return null;

    return {
      labels,
      datasets,
    };
  }, [overview]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: { position: 'top' },
      tooltip: {
        callbacks: {
          label: function (context) {
            let label = context.dataset.label || '';
            if (label) label += ': ';
            if (context.parsed.y !== null) {
              label += context.parsed.y;
              label += context.dataset.yAxisID === 'y' ? ' (Pos)' : ' (Credits)';
            }
            return label;
          }
        }
      }
    },
    scales: {
      x: { grid: { display: false } },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: { display: true, text: 'Average Position' },
        reverse: true,
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
        min: 0,
      },
      y1: {
        type: 'linear',
        display: true,
        position: 'right',
        title: { display: true, text: 'Credit Usage' },
        grid: { drawOnChartArea: false },
        beginAtZero: true,
      },
    },
  };

  return (
    <div className="space-y-6">
      <Card padding="p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-700">
              Dashboard overview
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
              {project ? project.name : 'SEO dashboard'}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              {project ? `Monitor rankings for ${project.name}.` : 'Select a project.'}
            </p>
          </div>
        </div>
      </Card>

      {error && (
        <Card padding="p-6 text-center" border="border-rose-200" className="bg-rose-50/70">
          <h3 className="text-lg font-semibold text-slate-900">Dashboard failed to load</h3>
          <p className="mt-2 text-sm text-slate-600">{error}</p>
        </Card>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Total Projects"
          value={allProjects ? allProjects.length : '-'}
          hint={overviewLoading ? 'Loading...' : ''}
          icon={faFolderOpen}
        />
        <StatCard
          title="Tracked keywords"
          value={(overview?.tracked_keywords_count ?? stats.totalKeywords).toLocaleString('en-US')}
          hint={overviewLoading ? 'Loading...' : 'Active keywords'}
          icon={faChartSimple}
        />
        <StatCard
          title="Average rank"
          value={overview?.average_rank ? `#${overview.average_rank}` : '-'}
          hint={overview?.average_rank ? 'Current average' : 'No rank data yet'}
          icon={faArrowTrendUp}
          tone="green"
        />
        <StatCard
          title="Credit balance"
          value={creditBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          hint="Available credits"
          icon={faChartSimple}
          tone="purple"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.5fr,1fr]">
        <article className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Position & Credit Tracking</h3>
              <p className="mt-1 text-sm text-slate-500">Last 7 days activity.</p>
            </div>
          </div>
          <div className="mt-6">
            {chartData ? (
              <Chart type="line" data={chartData} options={chartOptions} />
            ) : (
              <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 text-sm text-slate-500">
                <span className="mb-2 text-xl">📉</span>
                <p>No historical ranking data yet.</p>
                <p className="text-xs mt-1">Run a tracking job to see trends.</p>
              </div>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}

export default DashboardPage;