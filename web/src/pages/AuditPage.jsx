import { useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  clearAuditMessage,
  fetchAuditsByProject,
  resetAuditForProjectChange,
  runAuditByProject,
} from '../features/audit/auditSlice';
import { AlertTriangle, Bug, CheckCircle2, PlayCircle } from 'lucide-react';
import { formatDateTime } from '../utils/date';

const severityClasses = {
  CRITICAL: 'bg-rose-100 text-rose-700 border border-rose-200',
  WARNING: 'bg-amber-100 text-amber-700 border border-amber-200',
  PASSED: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
};

export default function AuditPage() {
  const dispatch = useDispatch();

  const {
    list: projects,
    selectedProjectId,
    loading: projectsLoading,
  } = useSelector((state) => state.projects);

  const {
    auditRuns,
    loading,
    running,
    error,
    actionMessage,
  } = useSelector((state) => state.audit);

  const selectedProject = useMemo(() => {
    if (!selectedProjectId) return null;

    return (
      projects.find((project) => String(project.id) === String(selectedProjectId)) || null
    );
  }, [projects, selectedProjectId]);

  const latestAudit = auditRuns.length ? auditRuns[0] : null;
  const latestIssues = latestAudit?.issues || [];

  useEffect(() => {
    if (!selectedProjectId) {
      dispatch(resetAuditForProjectChange(null));
      return;
    }

    if (projectsLoading) return;
    if (!selectedProject) return;

    dispatch(resetAuditForProjectChange(selectedProjectId));
    dispatch(fetchAuditsByProject(selectedProjectId));
  }, [dispatch, selectedProjectId, selectedProject, projectsLoading]);

  useEffect(() => {
    return () => {
      dispatch(clearAuditMessage());
    };
  }, [dispatch]);

  if (!selectedProjectId) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h1 className="text-xl font-semibold text-slate-900">No project selected</h1>
        <p className="mt-2 text-sm text-slate-500">
          Please select a project first to review audit results.
        </p>
      </div>
    );
  }

  if (projectsLoading || !selectedProject) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h1 className="text-xl font-semibold text-slate-900">Loading project...</h1>
        <p className="mt-2 text-sm text-slate-500">
          Restoring selected project after refresh.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Audit module</p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-900">
              {selectedProject.name}
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              Review audit findings, priority issues, and project readiness from one place.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="rounded-xl bg-slate-100 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-900">
                {latestAudit?.score ?? 0}
              </span>
              <span className="ml-2 text-slate-500">Score</span>
            </div>
            <div className="rounded-xl bg-slate-100 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-900">
                {latestAudit?.totalIssues ?? 0}
              </span>
              <span className="ml-2 text-slate-500">Checks</span>
            </div>
            <div className="rounded-xl bg-slate-100 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-900">
                {latestAudit?.criticalIssues ?? 0}
              </span>
              <span className="ml-2 text-slate-500">Critical</span>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Run audit</h2>
            <p className="mt-1 text-sm text-slate-500">
              Generate a fresh audit for this project using current project, keyword, competitor, and ranking data.
            </p>
          </div>

          <button
            type="button"
            onClick={() => dispatch(runAuditByProject(selectedProjectId))}
            disabled={running}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <PlayCircle size={16} />
            {running ? 'Running audit...' : 'Run audit'}
          </button>
        </div>

        {error ? (
          <p className="mt-4 text-sm font-medium text-rose-600">{error}</p>
        ) : null}

        {actionMessage ? (
          <p className="mt-4 text-sm font-medium text-emerald-600">{actionMessage}</p>
        ) : null}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Latest audit results</h2>
            <p className="mt-1 text-sm text-slate-500">
              Review the most recent audit run and its findings for this project.
            </p>
          </div>
          {loading ? <span className="text-sm text-slate-500">Loading...</span> : null}
        </div>

        {!loading && !latestAudit ? (
          <div className="mt-6 rounded-xl border border-dashed border-slate-300 p-10 text-center">
            <p className="text-sm font-medium text-slate-700">No audit runs yet.</p>
            <p className="mt-2 text-sm text-slate-500">
              Run your first audit to generate project health checks and recommendations.
            </p>
          </div>
        ) : latestAudit ? (
          <>
            <div className="mt-6 grid gap-4 md:grid-cols-4">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center gap-2 text-slate-500">
                  <Bug size={16} />
                  <span className="text-sm font-medium">Total checks</span>
                </div>
                <p className="mt-3 text-2xl font-semibold text-slate-900">
                  {latestAudit.totalIssues}
                </p>
              </div>

              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
                <div className="flex items-center gap-2 text-rose-600">
                  <AlertTriangle size={16} />
                  <span className="text-sm font-medium">Critical</span>
                </div>
                <p className="mt-3 text-2xl font-semibold text-rose-700">
                  {latestAudit.criticalIssues}
                </p>
              </div>

              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                <div className="flex items-center gap-2 text-amber-600">
                  <AlertTriangle size={16} />
                  <span className="text-sm font-medium">Warnings</span>
                </div>
                <p className="mt-3 text-2xl font-semibold text-amber-700">
                  {latestAudit.warningIssues}
                </p>
              </div>

              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <div className="flex items-center gap-2 text-emerald-600">
                  <CheckCircle2 size={16} />
                  <span className="text-sm font-medium">Passed</span>
                </div>
                <p className="mt-3 text-2xl font-semibold text-emerald-700">
                  {latestAudit.passedChecks}
                </p>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-medium text-slate-900">{latestAudit.summary}</p>
              <p className="mt-1 text-xs text-slate-500">
                Last run:{' '}
                {latestAudit.createdAt
                  ? formatDateTime(latestAudit.createdAt)
                  : '-'}
              </p>
            </div>

            <div className="mt-6 overflow-x-auto">
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-sm text-slate-500 sticky top-0 bg-slate-50">
                      <th className="py-3 pr-4 font-medium">Issue</th>
                      <th className="py-3 pr-4 font-medium">Category</th>
                      <th className="py-3 pr-4 font-medium">Severity</th>
                      <th className="py-3 pr-4 font-medium">Status</th>
                      <th className="py-3 font-medium">Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {latestIssues.map((issue) => (
                      <tr key={issue.id} className="border-b border-slate-100 text-sm align-top">
                        <td className="py-3 pr-4">
                          <p className="font-medium text-slate-900">{issue.title}</p>
                          {issue.description ? (
                            <p className="mt-1 text-slate-500">{issue.description}</p>
                          ) : null}
                        </td>
                        <td className="py-3 pr-4 text-slate-700">
                          {issue.category}
                        </td>
                        <td className="py-3 pr-4">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                              severityClasses[issue.severity] || 'bg-slate-100 text-slate-700 border border-slate-200'
                            }`}
                          >
                            {issue.severity}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-slate-700">{issue.status}</td>
                        <td className="py-3 text-slate-700">
                          {issue.recommendation || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : null}
      </section>
    </div>
  );
}