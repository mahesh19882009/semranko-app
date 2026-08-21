'use client'
import { useEffect, useMemo, useState, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import 'tippy.js/dist/tippy.css';
import tippy from 'tippy.js';

import { Chart } from 'primereact/chart';
import Button from '../components/ui/Button';
import Shimmer from '../components/ui/Shimmer';
import StatCard from '../components/StateCard';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faTrashCan,
  faUpload,
  faPlus,
  faTrash,
  faRefresh,
  faWandSparkles,
  faArrowTrendUp,
  faChartSimple,
  faMoneyBill1Wave,
} from '@fortawesome/free-solid-svg-icons';
import ConfirmModal from '../components/ConfirmModal';
import Modal from '../components/ui/Modal';
import Alert from '../components/ui/Alert';
import { getCountryCode } from '../data/locations';
import { formatDateTime } from '../utils/date';
import {
  addKeywordToProject,
  bulkAddKeywords,
  bulkDeleteKeywords,
  clearKeywordMessage,
  deleteKeywordById,
} from '../features/keywords/keywordsSlice';
import {
  addOptimisticProcessingJobs,
  buildActiveProcessingJobsByKeyword,
  completeProcessingKeyword,
  completeProcessingKeywords,
  getKeywordFieldDisplayState,
  reconcileBulkProcessingJobs,
  removeProcessingSubmission,
} from '../features/keywords/processingState';
import { fetchSubscriptionStatus } from '../features/subscription/subscriptionSlice';
import { apiRequest, API_BASE_URL} from '../lib/api';
import { Card } from '../components/ui';

const rankOptions = [
  { label: 'All Ranks', value: 'all' },
  { label: 'Top 3', value: 'top3' },
  { label: 'Top 10', value: 'top10' },
  { label: 'Not Ranking', value: 'not-ranking' },
];

function TippyTooltip({ content, children, placement = 'top', ...rest }) {
  const ref = useRef(null);
  const restRef = useRef(rest);
  restRef.current = rest;

  useEffect(() => {
    if (!ref.current) return;
    const instance = tippy(ref.current, { content, placement, ...restRef.current });
    return () => instance.destroy();
  }, [content, placement]);
  return <span ref={ref}>{children}</span>;
}

function KeywordsPage() {
  const dispatch = useDispatch();
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);
  const projects = useSelector((state) => state.projects.list);
  const projectsLoading = useSelector((state) => state.projects.loading);
  const pricingCurrent = useSelector((state) => state.pricing.current);

  const selectedProject = projects.find((p) => String(p.id) === String(selectedProjectId));
  const subscriptionData = useSelector((state) => state.subscription.data);
  const subscriptionLoading = useSelector((state) => state.subscription.loading);
  let projectCountry = 'India';
  let projectCountryCode = 2356;
  if (selectedProject?.location) {
    try {
      const parsed = JSON.parse(selectedProject.location);
      if (parsed && typeof parsed === 'object') {
        projectCountry = parsed.country || 'India';
        projectCountryCode = parsed.locationCode || parsed.countryCode || selectedProject.locationCode || getCountryCode(projectCountry) || 2356;
      }
    } catch {
      projectCountry = selectedProject.location || 'India';
      projectCountryCode = selectedProject.locationCode || getCountryCode(projectCountry);
    }
  } else if (selectedProject?.locationCode) {
    projectCountryCode = selectedProject.locationCode;
  }

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCsvSubmitting, setIsCsvSubmitting] = useState(false);
  const [keywordText, setKeywordText] = useState('');
  const [device, setDevice] = useState('desktop');
  const [csvPreview, setCsvPreview] = useState([]);
  const [showCsvConfirm, setShowCsvConfirm] = useState(false);
  const [tableData, setTableData] = useState([]);
  const [tableLoading, setTableLoading] = useState(false);
  const [tableError, setTableError] = useState('');
  const tableRequestIdRef = useRef(0);
  const [globalFilter, setGlobalFilter] = useState('');
  const [rankFilter, setRankFilter] = useState('all');
  const [selectedIds, setSelectedIds] = useState([]);
  const [nextRefresh, setNextRefresh] = useState(null);
  const [confirmState, setConfirmState] = useState({
    open: false,
    title: '',
    message: '',
    description: '',
    confirmText: 'Confirm',
    tone: 'danger',
    icon: null,
    onConfirm: null,
  });
  const [activatingId, setActivatingId] = useState(null);
  const [deactivatingId, setDeactivatingId] = useState(null);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState('');
  const [processingJobs, setProcessingJobs] = useState([]);
  const processingSubmissionIdRef = useRef(0);
  const [tableKey, setTableKey] = useState(0);

  const fetchTableData = async () => {
    if (!selectedProjectId) return;
    if (!Array.isArray(projects) || !projects.some((p) => String(p.id) === String(selectedProjectId))) {
      return;
    }

    const requestId = Date.now();
    tableRequestIdRef.current = requestId;
    setTableLoading(true);
    setTableError('');
    try {
      const json = await apiRequest(`/keywords/${selectedProjectId}/table`);
      if (tableRequestIdRef.current !== requestId) return;
      setTableData(json.data?.rows || []);
    } catch (err) {
      if (tableRequestIdRef.current !== requestId) return;
      setTableError(err.message);
    } finally {
      if (tableRequestIdRef.current === requestId) {
        setTableLoading(false);
      }
    }
  };

  useEffect(() => {
    const fetchSchedule = async () => {
      try {
        const json = await apiRequest('/rankings/schedule');
        if (json.success) {
          setNextRefresh(json.data?.nextRunAt);
        }
      } catch (err) {
        // ignore schedule fetch errors
      }
    };
    fetchSchedule();
  }, []);

  useEffect(() => {
    if (projectsLoading) return;
    if (!selectedProjectId) {
      setTableData([]);
      return;
    }
    fetchTableData();
  }, [dispatch, selectedProjectId, projectsLoading]);

  useEffect(() => {
    dispatch(fetchSubscriptionStatus());
  }, [dispatch]);

  useEffect(() => {
    if (!selectedProjectId) {
      setProcessingJobs([]);
      return;
    }

    let closed = false;

    const eventsUrl = `${API_BASE_URL}/keywords/${selectedProjectId}/events`;

    const eventSource = new EventSource(eventsUrl, {
      withCredentials: true,
    });

    const handleKeywordUpdated = async (event) => {
      if (closed) return;

      try {
        const payload = JSON.parse(event.data || '{}');
        const updatedKeyword = String(payload.keyword || '')
          .trim()
          .toLowerCase();

        // Worker publishes this event only after the completed
        // keyword data has been committed to PostgreSQL.
        await fetchTableData();

        // Remove only the keyword that actually completed.
        // This is important for bulk operations where other
        // keywords may still be processing.
        if (updatedKeyword) {
          setProcessingJobs((current) =>
            completeProcessingKeyword(current, updatedKeyword)
          );
        }

        setTableKey((key) => key + 1);
      } catch (error) {
        console.warn(
          'Failed to refresh keyword table after update:',
          error
        );
      }
    };

    eventSource.addEventListener(
      'keyword_updated',
      handleKeywordUpdated
    );

    eventSource.onerror = () => {
      // EventSource automatically reconnects.
      // No polling and no DataForSEO request is triggered here.
    };

    return () => {
      closed = true;

      eventSource.removeEventListener(
        'keyword_updated',
        handleKeywordUpdated
      );

      eventSource.close();
    };
  }, [selectedProjectId]);

  const filteredData = useMemo(() => {
    const processingByKeyword = buildActiveProcessingJobsByKeyword(
      processingJobs
    );

    let rows = tableData.map((row) => {
      const key = String(row.keyword || '').trim().toLowerCase();
      const processingJob = processingByKeyword.get(key);
      const isProcessing = Boolean(processingJob);

      return {
        ...row,
        isProcessing,
        status: isProcessing ? 'processing' : row.status,
      };
    });

    const existingKeywords = new Set(
      rows.map((row) =>
        String(row.keyword || '').trim().toLowerCase()
      )
    );

    for (const job of processingByKeyword.values()) {
      const key = String(job.keyword || '').trim().toLowerCase();

      if (!key || existingKeywords.has(key)) {
        continue;
      }

      rows.push({
        id: job.id,
        keyword: job.keyword,
        position: job.position,
        check_url: job.check_url,
        hasAIOverview: job.ai_badge === 'AIO',
        ai_description: null,
        volume: job.volume,
        kd: job.kd,
        cpc: job.cpc,
        competition: job.competition,
        backlinks: job.backlinks,
        domains: job.referring_domains,
        intent: job.intent,
        visibility:
          job.position != null
            ? job.position <= 10
              ? Math.round((1 - (job.position - 1) * 0.1) * 100) / 100
              : 0.05
            : null,
        is_active: true,
        isProcessing: true,
        status: 'processing',
      });
    }

    if (globalFilter.trim()) {
      const q = globalFilter.toLowerCase();
      rows = rows.filter((r) =>
        r.keyword.toLowerCase().includes(q)
      );
    }

    if (rankFilter === 'top3') {
      rows = rows.filter(
        (r) => r.position !== null && r.position <= 3
      );
    }

    if (rankFilter === 'top10') {
      rows = rows.filter(
        (r) => r.position !== null && r.position <= 10
      );
    }

    if (rankFilter === 'not-ranking') {
      rows = rows.filter(
        (r) =>
          r.position === null ||
          r.position === undefined
      );
    }

    return rows;
  }, [tableData, processingJobs, globalFilter, rankFilter]);

  const aioCount = useMemo(() => {
    return tableData.filter((r) => r.hasAIOverview).length;
  }, [tableData]);

  const summaryStats = useMemo(() => {
    const total = tableData.length;
    const withPosition = tableData.filter((r) => r.position != null);
    const avgPosition = withPosition.length
      ? withPosition.reduce((a, b) => a + b.position, 0) / withPosition.length
      : null;
    const withCPC = tableData.filter((r) => r.cpc != null);
    const avgCPC = withCPC.length
      ? withCPC.reduce((a, b) => a + b.cpc, 0) / withCPC.length
      : null;
    const totalVolume = tableData.reduce((a, b) => a + (b.volume || 0), 0);
    return { total, avgPosition, avgCPC, totalVolume, aioCount };
  }, [tableData, aioCount]);

  const positionDistribution = useMemo(() => {
    const top3 = tableData.filter((r) => r.position != null && r.position <= 3).length;
    const top10 = tableData.filter((r) => r.position != null && r.position > 3 && r.position <= 10).length;
    const top50 = tableData.filter((r) => r.position != null && r.position > 10 && r.position <= 50).length;
    const top100 = tableData.filter((r) => r.position != null && r.position > 50 && r.position <= 100).length;
    const notRanking = tableData.filter((r) => r.position == null || r.position === undefined).length;
    return { top3, top10, top50, top100, notRanking };
  }, [tableData]);

  const positionChartData = useMemo(() => {
    const { top3, top10, top50, top100, notRanking } = positionDistribution;
    const hasData = top3 + top10 + top50 + top100 + notRanking > 0;
    return {
      labels: hasData ? ['Top 3', 'Top 10', '11–50', '51–100', 'Not Ranking'] : ['No data'],
      datasets: [
        {
          data: hasData ? [top3, top10, top50, top100, notRanking] : [1],
          backgroundColor: ['#10B981', '#3B82F6', '#6366F1', '#F59E0B', '#94A3B8'],
          borderWidth: 0,
          hoverOffset: 4,
        },
      ],
    };
  }, [positionDistribution]);

  const positionChartOptions = useMemo(() => ({
    cutout: '70%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          usePointStyle: true,
          padding: 16,
          font: { size: 12 },
        },
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const total = context.dataset.data.reduce((a, b) => a + b, 0);
            const value = context.parsed;
            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
            return ` ${context.label}: ${value} (${percentage}%)`;
          },
        },
      },
    },
    responsive: true,
    maintainAspectRatio: false,
  }), []);

  const parseKeywords = (text) => {
    return text
      .split(/[\n,]+/)
      .map((kw) => kw.trim())
      .filter((kw) => kw.length > 0);
  };

  const handleAddKeywords = async (e) => {
    e.preventDefault();

    if (!selectedProjectId || !keywordText.trim() || isSubmitting) return;

    const parsed = parseKeywords(keywordText);

    if (parsed.length === 0) return;

    const optimisticKeywords = [...parsed];
    const submissionId = `add:${selectedProjectId}:${++processingSubmissionIdRef.current}`;

    // Close immediately after local validation.
    setKeywordText('');
    setIsAddModalOpen(false);

    // Immediately show pending rows in the table.
    setProcessingJobs((current) =>
      addOptimisticProcessingJobs(
        current,
        optimisticKeywords,
        submissionId
      )
    );

    setIsSubmitting(true);

    try {
      let resultAction;

      if (optimisticKeywords.length === 1) {
        resultAction = await dispatch(
          addKeywordToProject({
            projectId: selectedProjectId,
            payload: {
              keyword: optimisticKeywords[0],
              location_code: projectCountryCode,
              location: projectCountry,
              device,
            },
          })
        );
      } else {
        resultAction = await dispatch(
          bulkAddKeywords({
            projectId: selectedProjectId,
            keywords: optimisticKeywords,
            location_code: projectCountryCode,
            location: projectCountry,
            device,
          })
        );
      }

      const succeeded =
        optimisticKeywords.length === 1
          ? addKeywordToProject.fulfilled.match(resultAction)
          : bulkAddKeywords.fulfilled.match(resultAction);

      if (succeeded) {
        const resultData = resultAction.payload?.data;
        setProcessingJobs((current) => {
          const reconciled = bulkAddKeywords.fulfilled.match(resultAction)
            ? reconcileBulkProcessingJobs(
                current,
                submissionId,
                resultData
              )
            : current;

          return completeProcessingKeywords(
            reconciled,
            resultData?.completed_keywords
          );
        });

        // Fetch DB row after creation.
        // SSE will refresh again after SERP completes.
        setTimeout(fetchTableData, 500);
        return;
      }

      // Request failed: remove only the optimistic rows created by this attempt.
      setProcessingJobs((current) =>
        removeProcessingSubmission(current, submissionId)
      );

      setTableError(
        resultAction?.payload?.message ||
          resultAction?.error?.message ||
          'Failed to add keyword.'
      );
    } catch (error) {
      setProcessingJobs((current) =>
        removeProcessingSubmission(current, submissionId)
      );

      setTableError(error?.message || 'Failed to add keyword.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCsvChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      const lines = text.split('\n').filter((line) => line.trim());
      const keywords = lines.map((line) => line.split(',')[0].trim()).filter((kw) => kw.length > 0);
      setCsvPreview(keywords);
      setShowCsvConfirm(true);
    };
    reader.readAsText(file);
  };

  const handleCsvConfirm = async () => {
    setShowCsvConfirm(false);
    if (!selectedProjectId || csvPreview.length === 0) return;

    const submissionId = `csv:${selectedProjectId}:${++processingSubmissionIdRef.current}`;
    setIsCsvSubmitting(true);
    try {
      const resultAction = await dispatch(
        bulkAddKeywords({
          projectId: selectedProjectId,
          keywords: csvPreview,
          location_code: projectCountryCode,
          location: projectCountry,
          device,
        })
      );

      if (bulkAddKeywords.fulfilled.match(resultAction)) {
        setProcessingJobs((current) =>
          completeProcessingKeywords(
            reconcileBulkProcessingJobs(
              addOptimisticProcessingJobs(
                current,
                csvPreview,
                submissionId
              ),
              submissionId,
              resultAction.payload?.data
            ),
            resultAction.payload?.data?.completed_keywords
          )
        );

        setCsvPreview([]);
        setTimeout(fetchTableData, 500);
      }
    } finally {
      setIsCsvSubmitting(false);
    }
  };

  const handleDeleteSelected = () => {
    if (selectedIds.length === 0) return;
    setConfirmState({
      open: true,
      title: 'Delete selected keywords',
      message: `Delete ${selectedIds.length} selected keywords?`,
      description: 'This action cannot be undone.',
      confirmText: 'Delete selected',
      tone: 'danger',
      icon: faTrashCan,
      onConfirm: async () => {
        dispatch(clearKeywordMessage());
        const ids = selectedIds.map((row) => row.id);
        const resultAction = await dispatch(
          bulkDeleteKeywords({
            projectId: selectedProjectId,
            keywordIds: ids,
          })
        );
        if (bulkDeleteKeywords.fulfilled.match(resultAction)) {
          setSelectedIds([]);
          setConfirmState((s) => ({ ...s, open: false }));
          setTimeout(fetchTableData, 500);
        }
      },
    });
  };

  const handleDeleteOne = (row) => {
    setConfirmState({
      open: true,
      title: 'Delete keyword',
      message: `Delete "${row.keyword}"?`,
      description: 'Any related ranking results for this keyword may also be affected.',
      confirmText: 'Delete keyword',
      tone: 'danger',
      icon: faTrash,
      onConfirm: async () => {
        dispatch(clearKeywordMessage());
        const resultAction = await dispatch(
          deleteKeywordById({ keywordId: row.id, projectId: selectedProjectId })
        );
        if (deleteKeywordById.fulfilled.match(resultAction)) {
          setConfirmState((s) => ({ ...s, open: false }));
          setTimeout(fetchTableData, 500);
        }
      },
    });
  };

  const handleActivate = async (row) => {
    if (!row.id || activatingId) return;
    setActivatingId(row.id);
    try {
      await apiRequest(`/keywords/${row.id}/activate`, { method: 'POST' });
      setActionMessage('Keyword activated. No credits were used; it is eligible for the next scheduled refresh.');
      setTimeout(fetchTableData, 500);
    } catch (err) {
      setTableError(err.message || 'Failed to activate keyword');
    } finally {
      setActivatingId(null);
    }
  };

  const handleDeactivate = async (row) => {
    if (!row.id || deactivatingId) return;
    setDeactivatingId(row.id);
    try {
      await apiRequest(`/keywords/${row.id}/deactivate`, { method: 'POST' });
      setActionMessage('Keyword deactivated. Its row and history are preserved, and no credits were used.');
      setTimeout(fetchTableData, 500);
    } catch (err) {
      setTableError(err.message || 'Failed to deactivate keyword');
    } finally {
      setDeactivatingId(null);
    }
  };

  const handleBulkStatus = async (active) => {
    if (!selectedIds.length || bulkActionLoading) return;
    setBulkActionLoading(true);
    setActionMessage('');
    setTableError('');
    try {
      const result = await apiRequest('/keywords/bulk/status', {
        method: 'POST',
        body: JSON.stringify({ keyword_ids: selectedIds.map((row) => row.id), active }),
      });
      const invalid = result.data?.invalid?.length || 0;
      setActionMessage(invalid
        ? `${result.data?.updatedCount || 0} keyword(s) updated; ${invalid} invalid selection(s) skipped.`
        : `${result.data?.updatedCount || 0} keyword(s) ${active ? 'activated' : 'deactivated'}. No credits were used.`);
      setSelectedIds([]);
      await fetchTableData();
    } catch (err) {
      setTableError(err.message || `Failed to ${active ? 'activate' : 'deactivate'} selected keywords`);
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleManualRefresh = async () => {
    if (!selectedIds.length || bulkActionLoading) return;
    if (selectedIds.some((row) => row.deletedAt)) {
      setTableError('Deleted keywords cannot be refreshed. Re-add them only after the existing cooldown permits it.');
      return;
    }
    const inactive = selectedIds.filter((row) => row.is_active === false);
    if (inactive.length) {
      setTableError('Activate this keyword before refreshing it.');
      return;
    }
    setBulkActionLoading(true);
    setActionMessage('');
    setTableError('');
    try {
      const result = await apiRequest(`/keywords/${selectedProjectId}/refresh`, {
        method: 'POST',
        body: JSON.stringify({ keyword_ids: selectedIds.map((row) => row.id) }),
      });
      const data = result.data || {};
      setActionMessage(`${data.updated || 0} keyword(s) refreshed; ${data.skipped || 0} skipped.`);
      setSelectedIds([]);
      dispatch(fetchSubscriptionStatus());
      setTableKey((k) => k + 1);
    } catch (err) {
      setTableError(err.message || 'Manual refresh failed');
    } finally {
      setBulkActionLoading(false);
    }
  };

  const positionBodyTemplate = (rowData) => {
    if (rowData.position && rowData.position > 0) {
      return (
        <span title={`Ranked at position #${rowData.position}`}>
          #{rowData.position}
        </span>
      );
    }

    if (isRowProcessing(rowData)) {
      return <Shimmer width="w-12" />;
    }

    return <span title="Not ranking">—</span>;
  };

  const localPackPositionBodyTemplate = (rowData) => {
    if (rowData.localPackPosition && rowData.localPackPosition > 0) {
      return (
        <span title={`Local Pack position #${rowData.localPackPosition}`}>
          #{rowData.localPackPosition}
        </span>
      );
    }

    if (isRowProcessing(rowData)) {
      return <Shimmer width="w-12" />;
    }

    return <span title="Not ranking in Local Pack">—</span>;
  };

  const actionBodyTemplate = (rowData) => {
    if (rowData.deletedAt) {
      return <span className="text-xs font-medium text-slate-400">Deleted</span>;
    }
    const isActive = rowData.is_active !== false;
    if (isActive) {
      return (
        <div className="flex items-center gap-1">
          <Button variant="outline" onClick={() => handleDeactivate(rowData)} disabled={deactivatingId === rowData.id} title="Deactivate keyword" className="px-2 py-1 text-xs">
            {deactivatingId === rowData.id ? '...' : 'Deactivate'}
          </Button>
          <Button variant="danger" onClick={() => handleDeleteOne(rowData)} title="Delete keyword" className="px-2 py-1 text-xs">
            <FontAwesomeIcon icon={faTrash} />
          </Button>
        </div>
      );
    }
    return (
      <Button variant="primary" onClick={() => handleActivate(rowData)} disabled={activatingId === rowData.id} title="Activate keyword" className="px-2 py-1 text-xs">
        {activatingId === rowData.id ? '...' : 'Activate'}
      </Button>
    );
  };

  const isRowProcessing = (rowData) => rowData.isProcessing === true;

  const valueOrShimmer = (
    rowData,
    value,
    formatter = (v) => v,
    width = 'w-12'
  ) => {
    const displayState = getKeywordFieldDisplayState(rowData, value);

    // Show data immediately if it is already available,
    // even while SERP processing is still running.
    if (displayState === 'value') {
      return formatter(value);
    }

    // Only shimmer for values that are genuinely pending.
    if (displayState === 'shimmer') {
      return <Shimmer width={width} />;
    }

    return '—';
  };

  const statusBodyTemplate = (rowData) => {
    if (rowData.deletedAt) return <span className="rounded-full bg-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-600">Deleted</span>;
    if (rowData.is_active === false) return <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">Inactive</span>;
    return <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">Active</span>;
  };

  const aiBodyTemplate = (rowData) => {
    const hasAI = rowData.hasAIOverview;
    const description = rowData.ai_description;

    if (hasAI) {
      return (
        <TippyTooltip
          content={description || 'AI Overview'}
          placement="left"
          appendTo={document.body}
        >
          <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700 cursor-pointer">
            AIO
          </span>
        </TippyTooltip>
      );
    }

    if (isRowProcessing(rowData)) {
      return <Shimmer width="w-10" />;
    }

    return <span className="text-slate-400 text-xs">—</span>;
  };

  const visibilityBodyTemplate = (rowData) => {
    const vis = rowData.visibility;

    if (vis !== null && vis !== undefined) {
      return (
        <span title={`${(vis * 100).toFixed(0)}% visibility score`}>
          {(vis * 100).toFixed(0)}%
        </span>
      );
    }

    if (isRowProcessing(rowData)) {
      return <Shimmer width="w-14" />;
    }

    return <span title="No visibility data">—</span>;
  };

  const checkUrlBodyTemplate = (rowData) => {
    const rankingUrl = rowData.check_url || rowData.localPackUrl;
    if (rankingUrl) {
      return (
        <TippyTooltip
          content={rankingUrl}
          placement="left"
          appendTo={document.body}
        ><a
          href={rankingUrl}
          target="_blank"
          rel="noreferrer"
          title={rankingUrl}
          className="text-blue-600 hover:underline truncate block max-w-[200px]"
        >
          {rankingUrl}
        </a></TippyTooltip>
      );
    }

    if (isRowProcessing(rowData)) {
      return <Shimmer width="w-24" />;
    }

    return <span title="No ranking URL">—</span>;
  };

  const headerTemplate = () => {
    return (
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row">
          <InputText
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search keywords..."
            className="w-full sm:w-auto"
          />
          <Dropdown
            value={rankFilter}
            onChange={(e) => setRankFilter(e.value)}
            options={rankOptions}
            optionLabel="label"
            optionValue="value"
            placeholder="All Ranks"
            className="w-full sm:w-auto"
          />
          <Button
            variant="outline"
            onClick={fetchTableData}
            loading={tableLoading}
          ><FontAwesomeIcon icon={faRefresh} /> Refresh</Button>
        </div>
        {nextRefresh && (
          <div className="text-xs text-slate-400">
            Next data refresh: {formatDateTime(nextRefresh)}
          </div>
        )}
      </div>
    );
  };

  if (!selectedProjectId) {
    return (
      <section className="rounded-xs border border-slate-200 bg-white p-6 shadow-soft">
        <p className="text-sm text-slate-500">Select a project first to manage keywords and rankings.</p>
      </section>
    );
  }

  const rawPlanName = subscriptionData?.effectivePlan || subscriptionData?.plan || pricingCurrent?.effectivePlan || pricingCurrent?.plan;
  const planName = rawPlanName === 'free_trial' ? 'Free' : (rawPlanName || 'Free');
  const keywordLimit = subscriptionData?.limits?.keywordLimit ?? pricingCurrent?.limits?.keywordLimit ?? null;
  const totalKeywordCount = subscriptionData?.usage?.keywords ?? pricingCurrent?.usage?.keywords ?? null;
  const remainingSlots = keywordLimit != null && totalKeywordCount != null ? Math.max(0, keywordLimit - totalKeywordCount) : null;
  const creditBalance = subscriptionData?.creditBalance ?? pricingCurrent?.creditBalance ?? null;
  const spendableCredits = subscriptionData?.spendableCreditsRemaining ?? pricingCurrent?.spendableCreditsRemaining ?? creditBalance;
  const manualUsage = subscriptionData?.featureUsage?.manualRefresh;
  const manualRefreshCost = subscriptionData?.creditCosts?.manualRefresh ?? pricingCurrent?.creditCosts?.manualRefresh;
  const addKeywordCost = subscriptionData?.creditCosts?.addKeyword ?? pricingCurrent?.creditCosts?.addKeyword;
  const manualLocked = (subscriptionData?.effectivePlan || subscriptionData?.plan) === 'free_trial' || (manualUsage?.limit ?? 0) <= 0;
  const pendingKeywordCount = parseKeywords(keywordText).length;
  const pendingAddCost = addKeywordCost != null ? pendingKeywordCount * addKeywordCost : null;
  const addCapacityExceeded = remainingSlots != null && pendingKeywordCount > remainingSlots;
  const addCreditsInsufficient = pendingAddCost != null && spendableCredits != null && pendingAddCost > spendableCredits;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Keywords</h2>
          <p className="mt-1 text-sm text-slate-500">
            Tracked keywords with rank, volume, difficulty, CPC, and AI overview status in one place.
          </p>
        </div>
        <Button onClick={() => setIsAddModalOpen(true)}>
          <FontAwesomeIcon icon={faPlus} /> Add Keywords
        </Button>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-6 text-sm">
          <div>
            <span className="text-slate-500">Plan:</span>{' '}
            <span className="font-semibold text-slate-900 capitalize">{planName}</span>
          </div>
          <div>
            <span className="text-slate-500">Keywords:</span>{' '}
            <span className="font-semibold text-slate-900">{totalKeywordCount != null ? totalKeywordCount.toLocaleString('en-US') : '—'} / {keywordLimit != null ? keywordLimit.toLocaleString('en-US') : '—'}</span>
          </div>
          <div>
            <span className="text-slate-500">Remaining Slots:</span>{' '}
            <span className="font-semibold text-slate-900">{remainingSlots != null ? remainingSlots.toLocaleString('en-US') : '—'}</span>
          </div>
          <div>
            <span className="text-slate-500">Spendable Credits:</span>{' '}
            <span className="font-semibold text-slate-900">{spendableCredits != null ? spendableCredits.toLocaleString('en-US') : '—'}</span>
          </div>
          <div>
            <span className="text-slate-500">Manual Refresh:</span>{' '}
            <span className="font-semibold text-slate-900">{manualUsage ? `${manualUsage.used} of ${manualUsage.limit} used · ${manualUsage.remaining} remaining` : '—'}</span>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <h3 className="text-base font-semibold text-slate-900">Ranking Distribution</h3>
          <p className="mt-1 text-xs text-slate-500">Keywords grouped by current position</p>
          <div className="mt-4 h-24">
            <Chart height='200px' type="pie" data={positionChartData} options={positionChartOptions} />
          </div>
        </Card>
        <div className="grid grid-cols-2 gap-4 content-start">
          <StatCard
            title="Total Keywords"
            value={summaryStats.total.toLocaleString('en-US')}
            hint="Tracked keywords"
            icon={faChartSimple}
            tone="brand"
          />
          <StatCard
            title="Avg Position"
            value={summaryStats.avgPosition ? `#${summaryStats.avgPosition.toFixed(1)}` : '—'}
            hint={summaryStats.avgPosition ? 'Current average rank' : 'No rank data'}
            icon={faArrowTrendUp}
            tone="green"
          />
          <StatCard
            title="AIO Keywords"
            value={summaryStats.aioCount.toLocaleString('en-US')}
            hint="With AI Overview"
            icon={faWandSparkles}
            tone="amber"
          />
          <StatCard
            title="Avg CPC"
            value={summaryStats.avgCPC ? `₹${summaryStats.avgCPC.toFixed(2)}` : '—'}
            hint="Cost per click"
            icon={faMoneyBill1Wave}
            tone="green"
          />
        </div>
      </section>

      <section className="rounded-xs border border-slate-200 bg-white shadow-soft">
        <div className="overflow-x-auto" aria-label="Keyword table. Scroll horizontally to view all columns.">
          <DataTable
            value={filteredData}
            paginator
            rows={10}
            rowsPerPageOptions={[10, 20, 50, 100]}
            selection={selectedIds}
            onSelectionChange={(e) => setSelectedIds(e.value)}
            selectionMode="multiple"
            sortField="keyword"
            sortOrder={1}
            removableSort
            dataKey="id"
            header={headerTemplate}
            emptyMessage="No keywords found. Add keywords to get started."
            loading={tableLoading}
            tableStyle={{ minWidth: '60rem', width: '100%' }}
            className="compact-datatable"
            scrollable
            scrollHeight="flex"
            frozenWidth="18rem"
          >
            <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} frozen style={{ width: '3rem' }} />
            <Column field="keyword" header="Keyword" sortable frozen style={{ fontWeight: 600, minWidth: '14rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} />
            <Column header="Status" body={statusBodyTemplate} style={{ width: '8rem' }} />
            <Column
              field="volume"
              header="Volume"
              sortable
              style={{ width: '8rem' }}
              body={(rowData) =>
                valueOrShimmer(
                  rowData,
                  rowData.volume,
                  (value) => Number(value).toLocaleString('en-US')
                )
              }
            />
            <Column field="kd" header={
              <TippyTooltip content="Keyword Difficulty (0-100) — how hard it is to rank" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>KD</span>
              </TippyTooltip>
            } sortable style={{ width: '6rem' }}
            body={(rowData) =>
              valueOrShimmer(rowData, rowData.kd)
            } />
            <Column field="cpc" header={
              <TippyTooltip content="Cost per click in INR" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>CPC</span>
              </TippyTooltip>
            } sortable style={{ width: '7rem' }}
            body={(rowData) =>
              valueOrShimmer(
                rowData,
                rowData.cpc,
                (value) => `₹${value}`
              )
            } />
            <Column field="competition" header={
              <TippyTooltip content="Competition level (0-1) for paid search" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Competition</span>
              </TippyTooltip>
            } sortable style={{ width: '8rem' }}
            body={(rowData) =>
              valueOrShimmer(
                rowData,
                rowData.competition,
                (value) => Number(value).toFixed(2)
              )
            } />
            <Column field="backlinks" header={
              <TippyTooltip content="Total backlinks pointing to this page" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Backlinks</span>
              </TippyTooltip>
            } sortable style={{ width: '8rem' }}
            body={(rowData) =>
              valueOrShimmer(
                rowData,
                rowData.backlinks,
                (value) => Math.round(value).toLocaleString('en-US')
              )
            } />
            <Column field="domains" header={
              <TippyTooltip content="Number of referring domains" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Domains</span>
              </TippyTooltip>
            } sortable style={{ width: '8rem' }}
            body={(rowData) =>
              valueOrShimmer(
                rowData,
                rowData.domains,
                (value) => Math.round(value).toLocaleString('en-US')
              )
            } />
            <Column
              field="intent"
              header={
                <TippyTooltip
                  content="Search intent: informational, navigational, commercial, transactional"
                  placement="top"
                  appendTo={document.body}
                >
                  <span
                    style={{ display: 'inline-block', width: '100%', cursor: 'help' }}
                  >
                    Intent
                  </span>
                </TippyTooltip>
              }
              style={{ width: '8rem' }}
              body={(rowData) =>
                valueOrShimmer(
                  rowData,
                  rowData.intent,
                  (value) => (
                    <span className="capitalize">
                      {value}
                    </span>
                  ),
                  'w-20'
                )
              }
            />
            <Column field="position" header={
              <TippyTooltip content="Current organic rank position (1 = top)" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Position</span>
              </TippyTooltip>
            } sortable style={{ width: '7rem' }} body={positionBodyTemplate} />
            <Column
              field="localPackPosition"
              header={
                <TippyTooltip content="Local pack rank" placement="top" appendTo={document.body}>
                  <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>LP&nbsp;Rank</span>
                </TippyTooltip>
              }
              sortable
              body={localPackPositionBodyTemplate}
              style={{ width: '8rem' }}
            />
            <Column field="visibility" header={
              <TippyTooltip content="Estimated visibility score based on rank position" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Visibility</span>
              </TippyTooltip>
            } sortable style={{ width: '8rem' }} body={visibilityBodyTemplate} />
            <Column header={
              <TippyTooltip content="URL where this keyword ranks" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Ranking URL</span>
              </TippyTooltip>
            } style={{ width: '8rem' }} body={checkUrlBodyTemplate} />
            <Column header={
              <TippyTooltip content="AI Overview presence and description" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>AI&nbsp;Overview</span>
              </TippyTooltip>
            } style={{ width: '8rem' }} body={aiBodyTemplate} />
            <Column header={
              <TippyTooltip content="Keyword actions" placement="top" appendTo={document.body}>
                <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Actions</span>
              </TippyTooltip>
            } body={actionBodyTemplate} style={{ width: '5rem' }} />
          </DataTable>
        </div>

        {selectedIds.length > 0 && (
          <div className="flex flex-col gap-3 border-t border-slate-200 bg-surface-subtle px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm font-medium text-text-primary">{selectedIds.length} selected</span>
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" onClick={() => handleBulkStatus(true)} loading={bulkActionLoading} disabled={bulkActionLoading}>Activate</Button>
              <Button variant="outline" onClick={() => handleBulkStatus(false)} loading={bulkActionLoading} disabled={bulkActionLoading}>Deactivate</Button>
              <Button variant="outline" onClick={handleManualRefresh} loading={bulkActionLoading} disabled={bulkActionLoading || manualLocked || (manualUsage?.remaining ?? 0) < selectedIds.length} title={manualLocked ? 'This feature is available on paid plans. Upgrade to continue.' : '20 spendable credits per keyword'}>
                Manual Refresh ({manualRefreshCost != null ? selectedIds.length * manualRefreshCost : '—'} credits)
              </Button>
              <Button variant="danger" onClick={handleDeleteSelected}
                disabled={tableLoading}> <FontAwesomeIcon icon={faTrash} />Delete selected</Button>
            </div>
          </div>
        )}
        <div className="p-2">
          {manualLocked && <Alert variant="warning" message="Manual Refresh is available on paid plans. Upgrade to continue. Automatic tracking is not included on Free." />}
          {actionMessage && <Alert variant="success" message={actionMessage} />}
          {tableError && <Alert variant="error" message={tableError} />}
        </div>
      </section>

      <Modal
        open={isAddModalOpen}
        onClose={() => !isSubmitting && setIsAddModalOpen(false)}
        title="Add Keywords"
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setIsAddModalOpen(false)} disabled={isSubmitting} >Cancel</Button>
            <Button onClick={handleAddKeywords} disabled={!keywordText.trim() || isSubmitting || addCapacityExceeded || addCreditsInsufficient} loading={isSubmitting} >
              <FontAwesomeIcon icon={faPlus} /> {isSubmitting ? 'Adding...' : 'Add Keywords'}
            </Button>
          </>
        }
      >
        {isSubmitting && (
          <div className="flex items-center gap-2 rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-800 mb-4">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>Fetching keyword data. This may take a few seconds...</span>
          </div>
        )}
        <form onSubmit={handleAddKeywords} className="grid gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Keywords <span className="text-slate-400">(one per line, or comma separated)</span>
            </label>
            <textarea
              value={keywordText}
              onChange={(e) => setKeywordText(e.target.value)}
              placeholder="Enter keywords (one per line)"
              rows={6}
              disabled={isSubmitting}
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none disabled:bg-slate-50 disabled:cursor-not-allowed"
            />
            <p className="mt-2 text-xs text-slate-500">{addKeywordCost ?? '—'} spendable credits per keyword for both single and bulk add. Inactive existing keywords should be reactivated at no cost; deleted keywords remain subject to the 30-day re-add cooldown.</p>
            {pendingKeywordCount > 0 && <p className="mt-1 text-xs font-medium text-slate-700">This add requires {pendingAddCost ?? '—'} spendable credits and {pendingKeywordCount} keyword slot(s).</p>}
            {addCapacityExceeded && <p className="mt-1 text-sm font-medium text-rose-600">Keyword plan capacity exceeded. You have {remainingSlots} slot(s) remaining.</p>}
            {addCreditsInsufficient && <p className="mt-1 text-sm font-medium text-rose-600">Insufficient spendable credits. Automatic tracking credits cannot be used for keyword adds.</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Country</label>
              <div className="rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-700">
                {projectCountry} <span className="text-slate-400 text-xs ml-2">(from project)</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Device</label>
              <select
                value={device}
                onChange={(e) => setDevice(e.target.value)}
                disabled={isSubmitting}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none disabled:bg-slate-50 disabled:cursor-not-allowed"
              >
                <option value="desktop">Desktop</option>
                <option value="mobile">Mobile</option>
              </select>
            </div>
          </div>
          <div>
            <label className={`inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50 ${isSubmitting ? 'opacity-50 pointer-events-none' : ''}`}>
              <FontAwesomeIcon icon={faUpload} />
              <span>Upload CSV</span>
              <input type="file" accept=".csv" onChange={handleCsvChange} disabled={isSubmitting} className="hidden" />
            </label>
            <p className="mt-1 text-xs text-slate-400">
              CSV format: first column is keyword. One keyword per line.
            </p>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={confirmState.open}
        title={confirmState.title}
        message={confirmState.message}
        description={confirmState.description}
        confirmText={confirmState.confirmText}
        cancelText="Cancel"
        tone={confirmState.tone}
        icon={confirmState.icon}
        onConfirm={confirmState.onConfirm}
        onClose={() => setConfirmState((s) => ({ ...s, open: false }))}
      />

      {showCsvConfirm && (
        <ConfirmModal
          open={showCsvConfirm}
          title="Confirm CSV import"
          message={`Import ${csvPreview.length} keywords from CSV?`}
          description="This will add the keywords to the current project."
          confirmText="Import"
          cancelText="Cancel"
          tone="info"
          icon={faUpload}
          loading={isCsvSubmitting}
          onConfirm={handleCsvConfirm}
          onClose={() => {
            setShowCsvConfirm(false);
            setCsvPreview([]);
          }}
        />
      )}
    </div>
  );
}

export default KeywordsPage;
