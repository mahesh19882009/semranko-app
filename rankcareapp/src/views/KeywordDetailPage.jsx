'use client'
import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useSelector } from 'react-redux';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { getKeywordHistoryApi, getWeeklyComparisonApi } from '../lib/api';
import Card from '../components/ui/Card';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

function HistoryChart({ data, type = 'line', label, color, reverseY = false, suffix = '' }) {
  const chartData = useMemo(() => {
    const datasets = [];
    if (type === 'line') {
      datasets.push({
        label,
        data: data.map((d) => d.value),
        borderColor: color,
        backgroundColor: color.replace('1)', '0.1)').replace('rgb', 'rgba'),
        tension: 0.3,
        fill: true,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: color,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
      });
    } else if (type === 'bar') {
      datasets.push({
        label,
        data: data.map((d) => d.value),
        backgroundColor: color.replace('1)', '0.7)').replace('rgb', 'rgba'),
        borderColor: color,
        borderWidth: 1,
        borderRadius: 4,
      });
    }
    return {
      labels: data.map((d) => d.label),
      datasets,
    };
  }, [data, type, label, color]);

  const options = useMemo(() => {
    const opts = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#fff',
          bodyColor: '#fff',
          padding: 12,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            label: (ctx) => `${label}: ${ctx.parsed.y}${suffix}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            maxRotation: 45,
            minRotation: 45,
            font: { size: 11 },
            color: '#64748b',
          },
        },
        y: {
          reverse: reverseY,
          min: reverseY ? 1 : undefined,
          beginAtZero: !reverseY,
          grid: {
            color: 'rgba(148, 163, 184, 0.1)',
          },
          ticks: {
            callback: (value) => `${value}${suffix}`,
            color: '#64748b',
          },
        },
      },
    };
    return opts;
  }, [label, reverseY, suffix]);

  return (
    <div className="h-64 w-full">
      {type === 'line' ? (
        <Line data={chartData} options={options} />
      ) : (
        <Bar data={chartData} options={options} />
      )}
    </div>
  );
}

function ComparisonCard({ title, thisWeek, lastWeek, change, direction, suffix = '' }) {
  const dirColor = direction === 'up' ? 'text-emerald-600' : direction === 'down' ? 'text-rose-600' : 'text-slate-500';
  const dirIcon = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→';
  const fmt = (v) => (v === null || v === undefined ? '—' : `${v}${suffix}`);

  return (
    <Card padding="p-5">
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <div className="mt-3 space-y-1">
        <p className="text-xs text-slate-500">This week: <span className="font-semibold text-slate-900">{fmt(thisWeek)}</span></p>
        <p className="text-xs text-slate-500">Last week: <span className="font-semibold text-slate-900">{fmt(lastWeek)}</span></p>
        <p className={`text-sm font-semibold ${dirColor}`}>
          {change !== null && change !== undefined ? `${dirIcon} ${change}${suffix}` : 'No change'}
        </p>
      </div>
    </Card>
  );
}

function KeywordDetailPage() {
  const params = useParams();
  const router = useRouter();
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);

  const keywordId = params?.id;
  const [history, setHistory] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!selectedProjectId || !keywordId) return;
    let cancelled = false;
    setLoading(true);
    setError('');

    Promise.all([
      getKeywordHistoryApi(selectedProjectId, keywordId),
      getWeeklyComparisonApi(selectedProjectId),
    ])
      .then(([histRes, compRes]) => {
        if (!cancelled) {
          setHistory(histRes.data);
          setComparison(compRes.data);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'Failed to load keyword details');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [selectedProjectId, keywordId]);

  const positionData = useMemo(() => {
    if (!history?.history) return [];
    return history.history.map((h) => ({ label: h.week_start.slice(5), value: h.avg_position || 0 }));
  }, [history]);

  const visibilityData = useMemo(() => {
    if (!history?.history) return [];
    return history.history.map((h) => ({ label: h.week_start.slice(5), value: h.avg_visibility || 0 }));
  }, [history]);

  const trafficData = useMemo(() => {
    if (!history?.history) return [];
    return history.history.map((h) => ({ label: h.week_start.slice(5), value: h.traffic || 0 }));
  }, [history]);

  if (!keywordId) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="max-w-7xl mx-auto">
          <p className="text-sm text-slate-500">Keyword not found.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Keyword History</h1>
            <p className="mt-1 text-sm text-slate-500">
              {history?.keyword ? `Performance trends for "${history.keyword}"` : 'Loading...'}
            </p>
          </div>
          <button
            onClick={() => router.back()}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Back
          </button>
        </div>

        {error && <Card padding="p-4 border-rose-200 bg-rose-50" border="border-rose-200"><p className="text-sm text-rose-700">{error}</p></Card>}

        {loading && (
          <Card padding="p-10 text-center">
            <p className="text-sm text-slate-500">Loading keyword history...</p>
          </Card>
        )}

        {!loading && !error && (
          <>
            <section className="grid gap-4 md:grid-cols-3">
              {comparison && (
                <>
                  <ComparisonCard
                    title="Position"
                    thisWeek={comparison.position?.this_week}
                    lastWeek={comparison.position?.last_week}
                    change={comparison.position?.change}
                    direction={comparison.position?.direction}
                    suffix=""
                  />
                  <ComparisonCard
                    title="Visibility"
                    thisWeek={comparison.visibility?.this_week}
                    lastWeek={comparison.visibility?.last_week}
                    change={comparison.visibility?.change}
                    direction={comparison.visibility?.direction}
                    suffix="%"
                  />
                  <ComparisonCard
                    title="Traffic"
                    thisWeek={comparison.traffic?.this_week}
                    lastWeek={comparison.traffic?.last_week}
                    change={comparison.traffic?.change}
                    direction={comparison.traffic?.direction}
                    suffix=""
                  />
                </>
              )}
              {!comparison && (
                <Card padding="p-6 md:col-span-3">
                  <p className="text-sm text-slate-500">No weekly comparison data yet.</p>
                </Card>
              )}
            </section>

            <section className="grid gap-6 xl:grid-cols-1">
              <Card padding="p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Position Trend</h3>
                {positionData.length > 0 ? (
                  <HistoryChart data={positionData} label="Position" color="rgb(79, 70, 229)" reverseY={true} />
                ) : (
                  <p className="text-sm text-slate-500">No position history yet.</p>
                )}
              </Card>

              <Card padding="p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Visibility Trend</h3>
                {visibilityData.length > 0 ? (
                  <HistoryChart data={visibilityData} label="Visibility" color="rgb(16, 185, 129)" reverseY={false} suffix="%" />
                ) : (
                  <p className="text-sm text-slate-500">No visibility history yet.</p>
                )}
              </Card>

              <Card padding="p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Traffic (ETV) Trend</h3>
                {trafficData.length > 0 ? (
                  <HistoryChart data={trafficData} label="Traffic" color="rgb(245, 158, 11)" type="bar" />
                ) : (
                  <p className="text-sm text-slate-500">No traffic history yet.</p>
                )}
              </Card>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

export default KeywordDetailPage;
