'use client'
import { useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  faArrowTrendUp,
  faChartSimple,
  faUsersViewfinder,
} from '@fortawesome/free-solid-svg-icons';
import StatCard from '../components/StateCard';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { useNavigate } from '../lib/navigation';
import { Chart } from 'primereact/chart';
import { apiRequest } from '../lib/api';
import {
  selectStats,
  selectRankTrend,
  selectCompetitors,
  selectKeywords,
  selectSelectedProject,
  selectHasSelectedProjectData,
  selectDashboardLoading,
  selectDashboardError,
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

// Helper for trend color/icon
const getTrendInfo = (current, previous) => {
  if (!current || !previous) return { color: 'text-gray-400', label: '-' };
  const diff = previous - current; // Lower rank is better
  if (diff > 0) return { color: 'text-green-600', label: '↑' }; // Improved
  if (diff < 0) return { color: 'text-red-600', label: '↓' }; // Dropped
  return { color: 'text-gray-400', label: '-' };
};

function DashboardPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const stats = useSelector(selectStats);
  const trend = useSelector(selectRankTrend);
  const competitors = useSelector(selectCompetitors);
  const keywords = useSelector(selectKeywords);
  const project = useSelector(selectSelectedProject);
  const hasSelectedProjectData = useSelector(selectHasSelectedProjectData);
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

  // Prepare chart data for dual-axis chart
  const chartData = useMemo(() => {
    if (!overview?.chart_data) return null;

    const { labels, positions, credits } = overview.chart_data;

    if (labels.length === 0 && positionData.length === 0 && creditData.length === 0 && keywords.length === 0) {
      return null;
    }

    return {
      labels,
      datasets: [
        {
          type: 'line',
          label: 'Average Position',
          data: positions,
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          yAxisID: 'y',
          tension: 0.4,
          fill: true,
        },
        {
          type: 'bar',
          label: 'Credit Usage',
          data: credits,
          backgroundColor: '#10B981',
          yAxisID: 'y1',
        },
      ],
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
      legend: {
        position: 'top',
      },
      tooltip: {
        callbacks: {
          label: function (context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y;
              if (context.dataset.yAxisID === 'y') {
                label += ' (Pos)';
              } else {
                label += ' (Credits)';
              }
            }
            return label;
          }
        }
      }
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
      },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: {
          display: true,
          text: 'Average Position',
        },
        reverse: true, // Lower position is better
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
      },
      y1: {
        type: 'linear',
        display: true,
        position: 'right',
        title: {
          display: true,
          text: 'Credit Usage',
        },
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  };

  const keywordsList = overview?.keywords || [];

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
              {project
                ? `Monitor rankings, competitors, and AIO for ${project.name}.`
                : 'Select a project to load dashboard data.'}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bg-slate-50 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Status
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-900">
                {project ? 'Selected' : 'Not selected'}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-50 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Data state
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-900">
                {overviewLoading ? 'Loading...' : error ? 'Error' : 'Live'}
              </p>
            </div>
          </div>
        </div>
      </Card>

      {error && (
        <Card padding="p-6 text-center" border="border-rose-200" className="bg-rose-50/70">
          <h3 className="text-lg font-semibold text-slate-900">Dashboard failed to load</h3>
          <p className="mt-2 text-sm text-slate-600">{error}</p>
        </Card>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatCard
          title="Tracked keywords"
          value={(overview?.tracked_keywords_count ?? stats.totalKeywords).toLocaleString('en-US')}
          hint={overviewLoading ? 'Loading...' : 'Active tracked keywords'}
          icon={faChartSimple}
        />
        <StatCard
          title="Average rank"
          value={overview?.average_rank ? `#${overview.average_rank}` : '-'}
          hint={overviewLoading ? 'Loading...' : 'Updated ranking data'}
          icon={faArrowTrendUp}
          tone="green"
        />
        <StatCard
          title="Credit balance"
          value={creditBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          hint="Available credits"
          icon={faUsersViewfinder}
          tone="purple"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.5fr,1fr]">
        <article className="rounded-xs border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Position & Credit Tracking</h3>
              <p className="mt-1 text-sm text-slate-500">
                Ranking position and credit usage over the last 7 days.
              </p>
            </div>
          </div>

          <div className="mt-6" style={{ height: '300px' }}>
            {chartData ? (
              <Chart type="line" data={chartData} options={chartOptions} />
            ) : (
              <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-slate-200 text-sm text-slate-500">
                {overviewLoading ? 'Loading chart data...' : 'No trend data available yet'}
              </div>
            )}
          </div>
        </article>

        <article className="rounded-xs border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Competitors</h3>
              <p className="mt-1 text-sm text-slate-500">
                Tracked competitors and shared keyword exposure.
              </p>
            </div>
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate('/competitors')}
              className="text-brand-700 hover:bg-brand-50"
            >
              View all
            </Button>
          </div>

          <div className="mt-5 space-y-4">
            {competitors.length > 0 ? (
              competitors.map((item) => (
                <div key={item.id} className="rounded-2xl border border-slate-100 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-semibold text-slate-900">{item.domain}</p>
                      <p className="mt-1 text-sm text-slate-500">
                        {item.sharedKeywords} shared keywords
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-slate-500">Overlap</p>
                      <p className="font-semibold text-slate-900">{item.overlap}%</p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
                No competitors tracked for the selected project.
              </div>
            )}
          </div>
        </article>
      </section>

      {/* New Section: Detailed Keywords Table */}
      <section className="rounded-xs border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Recent Keywords Details</h3>
        {overviewLoading ? (
          <div className="text-center py-8 text-slate-500">Loading keyword details...</div>
        ) : keywordsList.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500">
                <tr>
                  <th className="px-4 py-3 rounded-l-lg">Keyword</th>
                  <th className="px-4 py-3">Rank</th>
                  <th className="px-4 py-3">Trend</th>
                  <th className="px-4 py-3">KD</th>
                  <th className="px-4 py-3">CPC</th>
                  <th className="px-4 py-3">Intent</th>
                  <th className="px-4 py-3">Volume</th>
                  <th className="px-4 py-3 rounded-r-lg">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {keywordsList.map((kw) => {
                  const trendInfo = getTrendInfo(kw.current_rank, kw.previous_rank);
                  return (
                    <tr key={kw.id} className="hover:bg-slate-50 transition">
                      <td className="px-4 py-3 font-medium text-slate-900">
                        {kw.keyword}
                        <div className="text-xs text-slate-400 truncate max-w-[150px]">{kw.location}</div>
                      </td>
                      <td className="px-4 py-3">
                        {kw.current_rank ? `#${kw.current_rank}` : '-'}
                      </td>
                      <td className={`px-4 py-3 font-bold ${trendInfo.color}`}>
                        {trendInfo.label}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${kw.difficulty > 70 ? 'bg-red-50 text-red-700 ring-red-600/20' :
                          kw.difficulty > 40 ? 'bg-yellow-50 text-yellow-700 ring-yellow-600/20' :
                            'bg-green-50 text-green-700 ring-green-600/20'
                          }`}>
                          {kw.difficulty}
                        </span>
                      </td>
                      <td className="px-4 py-3">${parseFloat(kw.cpc || 0).toFixed(2)}</td>
                      <td className="px-4 py-3 capitalize">{kw.intent || '-'}</td>
                      <td className="px-4 py-3">{kw.search_volume?.toLocaleString() || 0}</td>
                      <td className="px-4 py-3 text-slate-400 text-xs">
                        {kw.last_updated ? new Date(kw.last_updated).toLocaleDateString() : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500">
            No keywords tracked yet. Add keywords to see detailed metrics like KD, CPC, and Intent.
          </div>
        )}
      </section>
    </div>
  );
}

export default DashboardPage;