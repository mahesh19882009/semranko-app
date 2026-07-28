import { useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import ConfirmModal from '../components/ConfirmModal';
import {
  clearReportError,
  clearReportMessage,
  clearSelectedReport,
  deleteAllReports,
  deleteReportById,
  fetchReportById,
  fetchReports,
  runReport,
} from '../features/reports/reportSlice';
import { fetchCurrentPricing } from '../features/pricing/pricingSlice';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';

import { formatDateTime } from '../utils/date';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEye, faTimes, faTrash } from '@fortawesome/free-solid-svg-icons';

function getScoreTone(score) {
  if (score >= 80) {
    return 'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200';
  }

  if (score >= 60) {
    return 'bg-amber-100 text-amber-700 ring-1 ring-amber-200';
  }

  return 'bg-red-100 text-red-700 ring-1 ring-red-200';
}

function StatChip({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-900">{value ?? '—'}</p>
    </div>
  );
}

function ReportDetailsModal({ open, onClose, report, loading, error }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <div className="sticky top-0 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Report details</h3>
            <p className="text-sm text-slate-500">Detailed report information</p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
          >
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        <div className="px-6 py-5">
          {loading ? (
            <Alert
              variant="plain"
              message="Loading report details..."
            />
          ) : error ? (
            <Alert
              variant="error"
              message={error}
            />
          ) : !report ? (
            <Alert
              variant="plain"
              message="No report selected."
            />
          ) : (
            <div className="space-y-6">
              <div className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Report
                  </p>
                  <h4 className="mt-1 text-xl font-semibold text-slate-900">
                    {report.title || 'Untitled report'}
                  </h4>
                  <p className="mt-2 text-sm text-slate-500">
                    Generated on {formatDateTime(report.createdAt)}
                  </p>
                </div>

                <div
                  className={`rounded-full px-3 py-1 text-sm font-semibold ${getScoreTone(
                    Number(report.visibilityScore || 0)
                  )}`}
                >
                  Score: {report.visibilityScore ?? 0}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <StatChip label="SEO Score" value={report.visibilityScore ?? 0} />
                <StatChip label="Issues" value={report.issueCount ?? 0} />
                <StatChip label="Warnings" value={report.warningCount ?? 0} />
                <StatChip label="Passed checks" value={report.passedChecks ?? 0} />
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <h5 className="text-sm font-semibold text-slate-900">Summary</h5>
                <div className="mt-3 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700 whitespace-pre-wrap">
                  {report.summary || 'No summary available for this report.'}
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <h5 className="text-sm font-semibold text-slate-900">Strengths</h5>
                  {Array.isArray(report.strengths) && report.strengths.length > 0 ? (
                    <ul className="mt-3 space-y-2 text-sm text-slate-700">
                      {report.strengths.map((item, index) => (
                        <li
                          key={`${item}-${index}`}
                          className="rounded-xl bg-emerald-50 px-3 py-2 text-emerald-800"
                        >
                          {item}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-sm text-slate-500">No strengths recorded.</p>
                  )}
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <h5 className="text-sm font-semibold text-slate-900">Recommendations</h5>
                  {Array.isArray(report.recommendations) && report.recommendations.length > 0 ? (
                    <ul className="mt-3 space-y-2 text-sm text-slate-700">
                      {report.recommendations.map((item, index) => (
                        <li
                          key={`${item}-${index}`}
                          className="rounded-xl bg-amber-50 px-3 py-2 text-amber-800"
                        >
                          {item}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-sm text-slate-500">No recommendations available.</p>
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <h5 className="text-sm font-semibold text-slate-900">Raw details</h5>
                <pre className="mt-3 overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
                  {JSON.stringify(report, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const dispatch = useDispatch();

  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);
  const {
    reports,
    loading,
    running,
    error,
    message,
    selectedReport,
    selectedReportLoading,
    selectedReportError,
    deleteLoadingById,
    deleteAllLoading,
  } = useSelector((state) => state.reports);
  const pricingCurrent = useSelector((state) => state.pricing.current);

  const reportLimit = pricingCurrent?.limits?.reportsPerMonth || 0;
  const reportsUsed = pricingCurrent?.usage?.reportsThisMonth || 0;
  const reportLimitReached = reportLimit > 0 && reportsUsed >= reportLimit;

  const [detailsOpen, setDetailsOpen] = useState(false);
  const [confirmState, setConfirmState] = useState({
    open: false,
    mode: null,
    reportId: null,
    reportTitle: '',
  });

  useEffect(() => {
    if (!selectedProjectId) {
      return;
    }

    dispatch(fetchReports(selectedProjectId));
  }, [dispatch, selectedProjectId]);

  useEffect(() => {
    return () => {
      dispatch(clearSelectedReport());
      dispatch(clearReportError());
      dispatch(clearReportMessage());
    };
  }, [dispatch]);

  const sortedReports = useMemo(() => {
    return [...reports].sort((a, b) => {
      const aTime = new Date(a.createdAt || 0).getTime();
      const bTime = new Date(b.createdAt || 0).getTime();
      return bTime - aTime;
    });
  }, [reports]);

  const handleRunReport = async () => {
    if (reportLimitReached) {
      return;
    }
    if (!selectedProjectId || running) return;

    const resultAction = await dispatch(runReport(selectedProjectId));

    if (!runReport.rejected.match(resultAction)) {
      await dispatch(fetchCurrentPricing());
    }
  };

  const handleOpenDetails = async (reportId) => {
    setDetailsOpen(true);
    await dispatch(fetchReportById(reportId));
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    dispatch(clearSelectedReport());
  };

  const openDeleteOneConfirm = (report) => {
    setConfirmState({
      open: true,
      mode: 'single',
      reportId: report.id,
      reportTitle: report.title || 'Untitled report',
    });
  };

  const openDeleteAllConfirm = () => {
    setConfirmState({
      open: true,
      mode: 'all',
      reportId: null,
      reportTitle: '',
    });
  };

  const closeConfirm = () => {
    if (deleteAllLoading) return;

    const activeDeleteLoading =
      confirmState.reportId && deleteLoadingById?.[confirmState.reportId];

    if (activeDeleteLoading) return;

    setConfirmState({
      open: false,
      mode: null,
      reportId: null,
      reportTitle: '',
    });
  };

  const handleConfirmDelete = async () => {
    if (!selectedProjectId) return;

    if (confirmState.mode === 'single' && confirmState.reportId) {
      const resultAction = await dispatch(
        deleteReportById({
          reportId: confirmState.reportId,
          projectId: selectedProjectId,
        })
      );

      if (!deleteReportById.rejected.match(resultAction)) {
        await dispatch(fetchCurrentPricing());

        if (selectedReport?.id === confirmState.reportId) {
          setDetailsOpen(false);
          dispatch(clearSelectedReport());
        }
        closeConfirm();
      }
    }

    if (confirmState.mode === 'all') {
      const resultAction = await dispatch(deleteAllReports(selectedProjectId));

      if (!deleteAllReports.rejected.match(resultAction)) {
        await dispatch(fetchCurrentPricing());
        setDetailsOpen(false);
        dispatch(clearSelectedReport());
        closeConfirm();
      }
    }
  };

  const confirmLoading =
    confirmState.mode === 'all'
      ? deleteAllLoading
      : !!(confirmState.reportId && deleteLoadingById?.[confirmState.reportId]);

  return (
    <div className="space-y-6">
      {reportLimitReached ? (
        <Alert
          variant="warning"
          message="You have reached your monthly report limit. Upgrade your plan to generate more reports."
        />
      ) : null}
      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-sky-600">Reports</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
              SEO reports
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-500">
              Generate, inspect, and manage reports for the selected project.
            </p>
          </div>


          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              onClick={handleRunReport}
              disabled={!selectedProjectId || running || reportLimitReached}
              loading={running}
            >
              Create report
            </Button>

            <Button
              variant="danger"
              onClick={openDeleteAllConfirm}
              disabled={!selectedProjectId || sortedReports.length === 0 || deleteAllLoading}
              loading={deleteAllLoading}
            >
              Delete all
            </Button>
          </div>
        </div>
        <p className="mt-2 mb-3 text-sm text-slate-500">
          Usage: {reportsUsed} / {reportLimit} reports used this month.
        </p>

        {!selectedProjectId ? (
          <Alert
            variant="warning"
            message="Please select a project first to manage reports."
          />
        ) : null}

        {message ? (
          <Alert
            variant="success"
            message={message}
          />
        ) : null}

        {error ? (
          <Alert
            variant="error"
            message={error}
          />
        ) : null}
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Generated reports</h2>
            <p className="mt-1 text-sm text-slate-500">
              Latest reports for the active project.
            </p>
          </div>

          <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
            {sortedReports.length} total
          </div>
        </div>

        {!selectedProjectId ? (
          <Alert
            variant="plain"
            message="No project selected."
          />
        ) : loading ? (
          <Alert
            variant="plain"
            message="Loading reports..."
          />
        ) : sortedReports.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-10 text-center">
            <p className="text-sm font-medium text-slate-700">No reports found</p>
            <p className="mt-1 text-sm text-slate-500">
              Create the first report for this project to see analysis here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
              <table className="min-w-full text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                  <tr>
                    <th className="px-5 py-4">Report</th>
                    <th className="px-5 py-4">Generated</th>
                    <th className="px-5 py-4">Score</th>
                    <th className="px-5 py-4">Issues</th>
                    <th className="px-5 py-4">Warnings</th>
                    <th className="px-5 py-4">Passed</th>
                    <th className="px-5 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedReports.map((report) => {
                    const deletingThis = !!deleteLoadingById?.[report.id];

                    return (
                      <tr key={report.id} className="border-t border-slate-100">
                        <td className="px-5 py-4">
                          <p className="font-semibold text-slate-900">{report.title || 'Untitled report'}</p>
                        </td>
                        <td className="px-5 py-4 text-slate-700 whitespace-nowrap">
                          {formatDateTime(report.createdAt)}
                        </td>
                        <td className="px-5 py-4">
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${getScoreTone(Number(report.visibilityScore || 0))}`}>
                            {report.visibilityScore ?? 0}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-slate-700">{report.issueCount ?? 0}</td>
                        <td className="px-5 py-4 text-slate-700">{report.warningCount ?? 0}</td>
                        <td className="px-5 py-4 text-slate-700">{report.passedChecks ?? 0}</td>
                        <td className="px-5 py-4">
                          <div className="flex flex-wrap items-center gap-2">
                            <Button
                              type="button"
                              onClick={() => handleOpenDetails(report.id)}
                              variant="ghost"
                              className="!text-indigo-600 hover:!text-indigo-700"
                            >
                              <FontAwesomeIcon icon={faEye} />
                            </Button>
                            <Button
                              type="button"
                              onClick={() => openDeleteOneConfirm(report)}
                              disabled={deletingThis}
                              variant="ghost"
                              className="!text-red-600 hover:!text-red-700"
                            >
                              <FontAwesomeIcon icon={faTrash} />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <ReportDetailsModal
        open={detailsOpen}
        onClose={handleCloseDetails}
        report={selectedReport}
        loading={selectedReportLoading}
        error={selectedReportError}
      />

      <ConfirmModal
        open={confirmState.open}
        title={confirmState.mode === 'all' ? 'Delete all reports' : 'Delete report'}
        message={
          confirmState.mode === 'all'
            ? 'Are you sure you want to delete all reports for this project? This action cannot be undone.'
            : `Are you sure you want to delete "${confirmState.reportTitle}"? This action cannot be undone.`
        }
        confirmText={confirmState.mode === 'all' ? 'Delete all' : 'Delete'}
        cancelText="Cancel"
        type="danger"
        loading={confirmLoading}
        onConfirm={handleConfirmDelete}
        onClose={closeConfirm}
      />
    </div>
  );
}