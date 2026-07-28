import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  faArrowTrendUp,
  faChartSimple,
  faUsers,
  faWrench,
  faLink,
  faFileCircleCheck,
} from '@fortawesome/free-solid-svg-icons';
import RankTrendList from '../components/RankTrendList';
import KeywordTable from '../components/KeywordTable';
import LowHangingFruits from '../components/LowHangingFruits';
import SerpFeatures from '../components/SerpFeatures';
import { useNavigate } from 'react-router-dom';
import {
  selectStats,
  selectRankTrend,
  selectAudits,
  selectCompetitors,
  selectReports,
  selectDateRange,
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
import StatCard from '../components/StateCard';

function DashboardPage() {
  const dispatch = useDispatch();

  const navigate = useNavigate();
  const stats = useSelector(selectStats);
  const trend = useSelector(selectRankTrend);
  const audits = useSelector(selectAudits);
  const competitors = useSelector(selectCompetitors);
  const reports = useSelector(selectReports);
  const dateRange = useSelector(selectDateRange);
  const project = useSelector(selectSelectedProject);
  const hasSelectedProjectData = useSelector(selectHasSelectedProjectData);
  const loading = useSelector(selectDashboardLoading);
  const error = useSelector(selectDashboardError);
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);

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

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
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
                ? `Monitor rankings, technical health, competitors, and reports for ${project.name} in one place.`
                : 'Select a project to load dashboard data.'}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-slate-50 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Date range
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{dateRange}</p>
            </div>
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
                {loading
                  ? 'Loading'
                  : error
                  ? 'Error'
                  : project
                  ? hasSelectedProjectData
                    ? 'Data available'
                    : 'No dashboard data'
                  : 'Idle'}
              </p>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <section className="rounded-3xl border border-rose-200 bg-rose-50/70 p-6 text-center shadow-soft">
          <h3 className="text-lg font-semibold text-slate-900">Dashboard failed to load</h3>
          <p className="mt-2 text-sm text-slate-600">{error}</p>
        </section>
      )}

      {project && !loading && !error && !hasSelectedProjectData && (
        <section className="rounded-3xl border border-dashed border-amber-300 bg-amber-50/70 p-6 text-center shadow-soft">
          <h3 className="text-lg font-semibold text-slate-900">
            No dashboard data for {project.name}
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            This project is selected, but no dashboard records are available yet.
          </p>
        </section>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatCard
          title="Tracked keywords"
          value={stats.totalKeywords.toLocaleString()}
          hint={stats.totalKeywordsHint}
          icon={faChartSimple}
        />
        <StatCard
          title="Average rank"
          value={stats.avgRank ? `#${stats.avgRank}` : '-'}
          hint={stats.avgRankHint}
          icon={faArrowTrendUp}
          tone="green"
        />
        <StatCard
          title="Estimated traffic"
          value={stats.estimatedTraffic.toLocaleString()}
          hint={stats.estimatedTrafficHint}
          icon={faUsers}
        />
        <StatCard
          title="Technical health"
          value={stats.technicalHealth ? `${stats.technicalHealth}%` : '-'}
          hint={stats.technicalHealthHint}
          icon={faWrench}
          tone="amber"
        />
        <StatCard
          title="Backlinks"
          value={stats.backlinks.toLocaleString()}
          hint={stats.backlinksHint}
          icon={faLink}
        />
        <StatCard
          title="Reports sent"
          value={stats.reportsSent.toLocaleString()}
          hint={stats.reportsSentHint}
          icon={faFileCircleCheck}
          tone="green"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.5fr,1fr]">
        <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Average ranking trend</h3>
              <p className="mt-1 text-sm text-slate-500">
                {project
                  ? `Recent ranking movement for ${project.name}. Lower average position means stronger search visibility.`
                  : 'Recent ranking movement for the selected project.'}
              </p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
              {dateRange}
            </span>
          </div>

          <div className="mt-6">
            {trend.length > 0 ? (
              <RankTrendList data={trend} />
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
                No trend data is available for the current selection.
              </div>
            )}
          </div>
        </article>

        <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Audit summary</h3>
              <p className="mt-1 text-sm text-slate-500">
                Quick view of technical findings and health indicators.
              </p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
              Snapshot
            </span>
          </div>

          <div className="mt-5 space-y-4">
            {audits.length > 0 ? (
              audits.map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3"
                >
                  <span className="text-sm font-medium text-slate-600">{item.label}</span>
                  <span className="text-lg font-bold text-slate-900">{item.value}</span>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
                No audit summary available yet.
              </div>
            )}
          </div>
        </article>
      </section>

      <KeywordTable />

      <LowHangingFruits />

      <SerpFeatures />

      <section className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Competitor overlap</h3>
              <p className="mt-1 text-sm text-slate-500">
                {project
                  ? `Tracked competitors and shared keyword exposure for ${project.name}.`
                  : 'Current competitor comparison snapshot.'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/app/competitors')}
              className="rounded-xl px-3 py-2 text-sm font-semibold text-brand-700 transition hover:bg-brand-50 text-nowrap"
            >
              View all
            </button>
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

        <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Scheduled reports</h3>
              <p className="mt-1 text-sm text-slate-500">
                {project
                  ? `Reporting activity for ${project.name} within ${dateRange.toLowerCase()}.`
                  : `Reporting activity filtered for ${dateRange.toLowerCase()}.`}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/app/reports')}
              className="rounded-xl px-3 py-2 text-sm font-semibold text-brand-700 transition hover:bg-brand-50"
            >
              Create report
            </button>
          </div>

          <div className="mt-5 space-y-4">
            {reports.length > 0 ? (
              reports.map((report) => (
                <div key={report.id} className="rounded-2xl border border-slate-100 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-semibold text-slate-900">{report.name}</p>
                      <p className="mt-1 text-sm text-slate-500">
                        {report.schedule} · {report.type}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        report.status === 'Active'
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {report.status}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
                No reports available for the selected project and range.
              </div>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}

export default DashboardPage;