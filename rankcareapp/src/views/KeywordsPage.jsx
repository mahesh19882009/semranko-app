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
import { apiRequest } from '../lib/api';
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
        if (res.ok && json.success) {
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

  const filteredData = useMemo(() => {
    let rows = [...tableData];
    if (globalFilter.trim()) {
      const q = globalFilter.toLowerCase();
      rows = rows.filter((r) => r.keyword.toLowerCase().includes(q));
    }
    if (rankFilter === 'top3') rows = rows.filter((r) => r.position !== null && r.position <= 3);
    if (rankFilter === 'top10') rows = rows.filter((r) => r.position !== null && r.position <= 10);
    if (rankFilter === 'not-ranking') rows = rows.filter((r) => r.position === null || r.position === undefined);
    return rows;
  }, [tableData, globalFilter, rankFilter]);

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

    setIsSubmitting(true);
    try {
      let resultAction;
      if (parsed.length === 1) {
        resultAction = await dispatch(
          addKeywordToProject({
            projectId: selectedProjectId,
            payload: { keyword: parsed[0], location_code: projectCountryCode, location: projectCountry, device },
          })
        );
      } else {
        resultAction = await dispatch(
          bulkAddKeywords({
            projectId: selectedProjectId,
            keywords: parsed,
            location_code: projectCountryCode,
            location: projectCountry,
            device,
          })
        );
      }

      if (
        (parsed.length === 1
          ? addKeywordToProject.fulfilled.match(resultAction)
          : bulkAddKeywords.fulfilled.match(resultAction))
      ) {
        setKeywordText('');
        setIsAddModalOpen(false);
        setTimeout(fetchTableData, 500);
      }
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

  const positionBodyTemplate = (rowData) => {
    if (!rowData.position) return <span title="Not ranking">—</span>;
    return <span title={`Ranked at position #${rowData.position}`}>#{rowData.position}</span>;
  };

  const actionBodyTemplate = (rowData) => {
    return (
      <Button variant="danger" onClick={() => handleDeleteOne(rowData)} title="Delete keyword">
        <FontAwesomeIcon icon={faTrash} />
      </Button>
    );
  };

  const aiBodyTemplate = (rowData) => {
    const hasAI = rowData.hasAIOverview;
    const description = rowData.ai_description;
    if (!hasAI) {
      return <span className="text-slate-400 text-xs">—</span>;
    }
    return (
      <TippyTooltip content={description || 'AI Overview'} placement="left" appendTo={document.body}>
        <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700 cursor-pointer">
          AIO
        </span>
      </TippyTooltip>
    );
  };

  const visibilityBodyTemplate = (rowData) => {
    const vis = rowData.visibility;
    if (vis === null || vis === undefined) return <span title="No visibility data">—</span>;
    return <span title={`${(vis * 100).toFixed(0)}% visibility score`}>{(vis * 100).toFixed(0)}%</span>;
  };

  const checkUrlBodyTemplate = (rowData) => {
    if (!rowData.check_url) return <span title="No ranking URL">—</span>;
    return (
      <a href={rowData.check_url} target="_blank" rel="noreferrer" title={rowData.check_url} className="text-blue-600 hover:underline truncate block max-w-[200px]">
        {rowData.check_url}
      </a>
    );
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
          <Column field="volume" header="Volume" sortable style={{ width: '8rem' }} />
          <Column field="kd" header={
            <TippyTooltip content="Keyword Difficulty (0-100) — how hard it is to rank" placement="top" appendTo={document.body}>
              <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>KD</span>
            </TippyTooltip>
          } sortable style={{ width: '6rem' }} />
          <Column field="cpc" header={
            <TippyTooltip content="Cost per click in INR" placement="top" appendTo={document.body}>
              <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>CPC</span>
            </TippyTooltip>
          } sortable style={{ width: '7rem' }} body={(rowData) => (rowData.cpc != null ? `₹${rowData.cpc}` : '—')} />
          <Column field="competition" header={
            <TippyTooltip content="Competition level (0-1) for paid search" placement="top" appendTo={document.body}>
              <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Competition</span>
            </TippyTooltip>
          } sortable style={{ width: '8rem' }} body={(rowData) => (rowData.competition != null ? rowData.competition.toFixed(2) : '—')} />
          <Column field="backlinks" header={
            <TippyTooltip content="Total backlinks pointing to this page" placement="top" appendTo={document.body}>
              <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Backlinks</span>
            </TippyTooltip>
          } sortable style={{ width: '8rem' }} body={(rowData) => (rowData.backlinks != null ? Math.round(rowData.backlinks).toLocaleString('en-US') : '—')} />
          <Column field="domains" header={
            <TippyTooltip content="Number of referring domains" placement="top" appendTo={document.body}>
              <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Domains</span>
            </TippyTooltip>
          } sortable style={{ width: '8rem' }} body={(rowData) => (rowData.domains != null ? Math.round(rowData.domains).toLocaleString('en-US') : '—')} />
          <Column field="intent" header={
            <TippyTooltip content="Search intent: informational, navigational, commercial, transactional" placement="top" appendTo={document.body}>
              <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Intent</span>
            </TippyTooltip>
          } style={{ width: '8rem' }} body={(rowData) => <span className="capitalize">{rowData.intent || '—'}</span>} />
          <Column field="position" header={
            <TippyTooltip content="Current organic rank position (1 = top)" placement="top" appendTo={document.body}>
              <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Position</span>
            </TippyTooltip>
          } sortable style={{ width: '7rem' }} body={positionBodyTemplate} />
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
              <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>AI Overview</span>
            </TippyTooltip>
          } style={{ width: '8rem' }} body={aiBodyTemplate} />
          <Column header={
            <TippyTooltip content="Keyword actions" placement="top" appendTo={document.body}>
              <span style={{ display: 'inline-block', width: '100%', cursor: 'help' }}>Actions</span>
            </TippyTooltip>
          } body={actionBodyTemplate} style={{ width: '5rem' }} />
        </DataTable>

        {selectedIds.length > 0 && (
          <div className="border-t border-slate-200 bg-rose-50 px-5 py-3 flex items-center justify-between">
            <span className="text-sm font-medium text-rose-700">{selectedIds.length} selected</span>
            <div className="flex items-center gap-2">
              <Button variant="danger" onClick={handleDeleteSelected}
                disabled={tableLoading}> <FontAwesomeIcon icon={faTrash} />Delete selected</Button>
            </div>
          </div>
        )}

        {tableError && <Alert variant="error" message={tableError} />}
      </section>

      <Modal
        open={isAddModalOpen}
        onClose={() => !isSubmitting && setIsAddModalOpen(false)}
        title="Add Keywords"
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setIsAddModalOpen(false)} disabled={isSubmitting} >Cancel</Button>
            <Button onClick={handleAddKeywords} disabled={!keywordText.trim() || isSubmitting} loading={isSubmitting} >
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
