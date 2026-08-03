'use client'
import { useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import Button from '../components/ui/Button';
import { Tag } from 'primereact/tag';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faTrashCan,
  faUpload,
  faTriangleExclamation,
  faPlus,
  faTrash,
  faRefresh,
} from '@fortawesome/free-solid-svg-icons';
import ConfirmModal from '../components/ConfirmModal';
import Modal from '../components/ui/Modal';
import Alert from '../components/ui/Alert';
import {
  addKeywordToProject,
  bulkAddKeywords,
  bulkDeleteKeywords,
  clearKeywordMessage,
  deleteKeywordById,
} from '../features/keywords/keywordsSlice';
import { toggleTrackedKeywordAioApi, bulkToggleTrackedKeywordAioApi } from '../features/pricing/pricingApi';

const aioOptions = [
  { label: 'All AIO', value: 'all' },
  { label: 'Has AIO', value: 'yes' },
  { label: 'No AIO', value: 'no' },
];

const rankOptions = [
  { label: 'All Ranks', value: 'all' },
  { label: 'Top 3', value: 'top3' },
  { label: 'Top 10', value: 'top10' },
  { label: 'Not Ranking', value: 'not-ranking' },
];

function KeywordsPage() {
  const dispatch = useDispatch();
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);
  const projectsLoading = useSelector((state) => state.projects.loading);
  const pricingCurrent = useSelector((state) => state.pricing.current);

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [keywordText, setKeywordText] = useState('');
  const [location, setLocation] = useState('India');
  const [device, setDevice] = useState('desktop');
  const [csvPreview, setCsvPreview] = useState([]);
  const [showCsvConfirm, setShowCsvConfirm] = useState(false);
  const [tableData, setTableData] = useState([]);
  const [tableLoading, setTableLoading] = useState(false);
  const [tableError, setTableError] = useState('');
  const [globalFilter, setGlobalFilter] = useState('');
  const [aioFilter, setAioFilter] = useState('all');
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
  const [aioConfirm, setAioConfirm] = useState({
    open: false,
    keywordId: null,
    keywordText: null,
    currentTrackAio: false,
  });
  const [aioLoading, setAioLoading] = useState({});
  const [bulkAioConfirm, setBulkAioConfirm] = useState({
    open: false,
    targetAio: false,
  });
  const [bulkAioLoading, setBulkAioLoading] = useState(false);

  const keywordLimitRemaining = (pricingCurrent?.limits?.keywords || 0) - (pricingCurrent?.usage?.keywords || 0);

  const fetchTableData = async () => {
    if (!selectedProjectId) return;
    setTableLoading(true);
    setTableError('');
    try {
      const token = localStorage.getItem('accessToken');
      const res = await fetch(`/api/keywords/${selectedProjectId}/table`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      if (!res.ok || !json.success) throw new Error(json.message || 'Failed to load keywords');
      setTableData(json.data?.rows || []);
    } catch (err) {
      setTableError(err.message);
    } finally {
      setTableLoading(false);
    }
  };

  useEffect(() => {
    const fetchSchedule = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        const res = await fetch('/api/rankings/schedule', {
          headers: { Authorization: `Bearer ${token}` },
        });
        const json = await res.json();
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
    if (aioFilter === 'yes') rows = rows.filter((r) => r.hasAIOverview);
    if (aioFilter === 'no') rows = rows.filter((r) => !r.hasAIOverview);
    if (rankFilter === 'top3') rows = rows.filter((r) => r.position !== null && r.position <= 3);
    if (rankFilter === 'top10') rows = rows.filter((r) => r.position !== null && r.position <= 10);
    if (rankFilter === 'not-ranking') rows = rows.filter((r) => r.position === null || r.position === undefined);
    return rows;
  }, [tableData, globalFilter, aioFilter, rankFilter]);

  const hasAioEnabled = useMemo(() => tableData.some((row) => row.trackAio), [tableData]);

  const parseKeywords = (text) => {
    return text
      .split(/[\n,]+/)
      .map((kw) => kw.trim())
      .filter((kw) => kw.length > 0);
  };

  const handleAddKeywords = async (e) => {
    e.preventDefault();
    if (!selectedProjectId || !keywordText.trim()) return;

    const parsed = parseKeywords(keywordText);
    if (parsed.length === 0) return;

    if (parsed.length + (pricingCurrent?.usage?.keywords || 0) > (pricingCurrent?.limits?.keywords || 0)) {
      dispatch(clearKeywordMessage());
      setConfirmState({
        open: true,
        title: 'Keyword limit exceeded',
        message: `You can only add ${keywordLimitRemaining} more keywords.`,
        description: 'Upgrade your plan to add more keywords.',
        confirmText: 'Upgrade plan',
        tone: 'warning',
        icon: faTriangleExclamation,
        onConfirm: () => {
          setConfirmState((s) => ({ ...s, open: false }));
          setIsAddModalOpen(false);
          window.location.href = '/pricing';
        },
      });
      return;
    }

    let resultAction;
    if (parsed.length === 1) {
      resultAction = await dispatch(
        addKeywordToProject({
          projectId: selectedProjectId,
          payload: { keyword: parsed[0], location },
        })
      );
    } else {
      resultAction = await dispatch(
        bulkAddKeywords({
          projectId: selectedProjectId,
          keywords: parsed,
          location: location,
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

    if (csvPreview.length + (pricingCurrent?.usage?.keywords || 0) > (pricingCurrent?.limits?.keywords || 0)) {
      dispatch(clearKeywordMessage());
      setConfirmState({
        open: true,
        title: 'Keyword limit exceeded',
        message: `You can only add ${keywordLimitRemaining} more keywords.`,
        description: 'Upgrade your plan to add more keywords.',
        confirmText: 'Upgrade plan',
        tone: 'warning',
        icon: faTriangleExclamation,
        onConfirm: () => {
          setConfirmState((s) => ({ ...s, open: false }));
          setIsAddModalOpen(false);
          window.location.href = '/pricing';
        },
      });
      return;
    }

    const resultAction = await dispatch(
      bulkAddKeywords({
        projectId: selectedProjectId,
        keywords: csvPreview,
        location: location,
      })
    );

    if (bulkAddKeywords.fulfilled.match(resultAction)) {
      setCsvPreview([]);
      setTimeout(fetchTableData, 500);
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
        const resultAction = await dispatch(
          bulkDeleteKeywords({
            projectId: selectedProjectId,
            keywordIds: selectedIds,
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
      icon: faTrashCan,
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

  const handleAioToggle = (row) => {
    setAioConfirm({
      open: true,
      keywordId: row.id,
      keywordText: row.keyword,
      currentTrackAio: row.trackAio || false,
    });
  };

  const handleAioConfirm = async () => {
    const keywordId = aioConfirm.keywordId;
    const newTrackAio = !aioConfirm.currentTrackAio;
    
    // Optimistic UI update
    setTableData((prev) =>
      prev.map((row) =>
        row.id === keywordId ? { ...row, trackAio: newTrackAio } : row
      )
    );
    
    setAioLoading((prev) => ({ ...prev, [keywordId]: true }));
    setAioConfirm((s) => ({ ...s, open: false }));
    
    try {
      await toggleTrackedKeywordAioApi(keywordId);
      // Success - the optimistic update is already applied
    } catch (err) {
      console.error('AIO toggle failed:', err);
      // Revert optimistic update on error
      setTableData((prev) =>
        prev.map((row) =>
          row.id === keywordId ? { ...row, trackAio: aioConfirm.currentTrackAio } : row
        )
      );
      
      const message = err.message || 'Failed to update AI tracking.';
      let title = 'AI Tracking Update Failed';
      let description = 'Please try again later.';

      if (message.includes('Insufficient credits')) {
        title = 'Insufficient Credits';
        description = message;
      } else if (message.includes('paid plan') || message.includes('trial')) {
        title = 'Paid Plan Required';
        description = 'AI tracking is available on paid plans only. Please upgrade to continue.';
      } else if (message === 'Failed to fetch' || message.includes('NetworkError') || message.includes('fetch')) {
        title = 'Connection Error';
        description = 'Could not reach the server. Please check your internet connection and try again.';
      }

      setConfirmState({
        open: true,
        title,
        message: description,
        confirmText: 'Close',
        tone: 'danger',
        icon: faTriangleExclamation,
        onConfirm: () => setConfirmState((s) => ({ ...s, open: false })),
      });
    } finally {
      setAioLoading((prev) => ({ ...prev, [keywordId]: false }));
    }
  };

  const handleBulkAioToggle = (targetAio) => {
    if (selectedIds.length === 0) return;
    setBulkAioConfirm({ open: true, targetAio });
  };

  const handleBulkAioConfirm = async () => {
    const targetAio = bulkAioConfirm.targetAio;
    const previouslySelectedIds = [...selectedIds];
    
    // Optimistic UI update
    setTableData((prev) =>
      prev.map((row) =>
        selectedIds.includes(row.id) ? { ...row, trackAio: targetAio } : row
      )
    );
    
    setBulkAioLoading(true);
    setBulkAioConfirm((s) => ({ ...s, open: false }));
    
    try {
      await bulkToggleTrackedKeywordAioApi(selectedIds, targetAio);
      setSelectedIds([]);
      // Success - the optimistic update is already applied
    } catch (err) {
      console.error('Bulk AIO toggle failed:', err);
      // Revert optimistic update on error
      setTableData((prev) =>
        prev.map((row) =>
          previouslySelectedIds.includes(row.id) 
            ? { ...row, trackAio: !targetAio } 
            : row
        )
      );
      
      const message = err.message || 'Failed to update AI tracking for selected keywords.';
      let title = 'Bulk AI Tracking Update Failed';
      let description = 'Please try again later.';

      if (message.includes('Insufficient credits')) {
        title = 'Insufficient Credits';
        description = message;
      } else if (message.includes('paid plan') || message.includes('trial')) {
        title = 'Paid Plan Required';
        description = 'AI tracking is available on paid plans only. Please upgrade to continue.';
      } else if (message === 'Failed to fetch' || message.includes('NetworkError') || message.includes('fetch')) {
        title = 'Connection Error';
        description = 'Could not reach the server. Please check your internet connection and try again.';
      }

      setConfirmState({
        open: true,
        title,
        message: description,
        confirmText: 'Close',
        tone: 'danger',
        icon: faTriangleExclamation,
        onConfirm: () => setConfirmState((s) => ({ ...s, open: false })),
      });
    } finally {
      setBulkAioLoading(false);
    }
  };

  const aioBodyTemplate = (rowData) => {
    return rowData.hasAIOverview ? (
      <Tag value="AIO" severity="info" />
    ) : (
      <span className="text-slate-400 text-xs">—</span>
    );
  };

  const positionBodyTemplate = (rowData) => {
    return rowData.position ? `#${rowData.position}` : '—';
  };

  const actionBodyTemplate = (rowData) => {
    return (
      <Button variant="danger" onClick={() => handleDeleteOne(rowData)}>
        <FontAwesomeIcon icon={faTrash} />
      </Button>
    );
  };

  const aioToggleBodyTemplate = (rowData) => {
    const isActive = rowData.trackAio;
    const isLoading = aioLoading[rowData.id];
    return (
      <button
        type="button"
        onClick={() => handleAioToggle(rowData)}
        disabled={isLoading}
        className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition ${
          isActive
            ? 'bg-purple-50 text-purple-700 border border-purple-200'
            : 'bg-slate-100 text-slate-500 border border-transparent hover:bg-slate-200'
        }`}
        title={isActive ? 'Disable premium AI tracking' : 'Enable premium AI tracking'}
      >
        {isLoading ? (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current/30 border-t-current" />
        ) : (
          <span aria-hidden="true">✨</span>
        )}
        {isActive ? 'AI Active' : 'AIO'}
      </button>
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
          {hasAioEnabled && (
            <Dropdown
              value={aioFilter}
              onChange={(e) => setAioFilter(e.value)}
              options={aioOptions}
              optionLabel="label"
              optionValue="value"
              placeholder="All AIO"
              className="w-full sm:w-auto"
            />
          )}
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
            Next data refresh: {new Date(nextRefresh).toLocaleString('en-US')}
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
          <p className="text-sm text-slate-500">
            Usage: {pricingCurrent?.usage?.keywords || 0} / {pricingCurrent?.limits?.keywords || 0} keywords used.
          </p>
        </div>
        <Button onClick={() => setIsAddModalOpen(true)}>
          <FontAwesomeIcon icon={faPlus} /> Add Keywords
        </Button>
      </div>
      <section className="rounded-xs border border-slate-200 bg-white shadow-soft">
        <DataTable
          value={filteredData}
          paginator
          rows={20}
          rowsPerPageOptions={[20, 50, 100]}
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
          rowClassName={(rowData) => (rowData.trackAio ? 'bg-purple-50/40' : '')}
        >
          <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} frozen style={{ width: '3rem' }} />
          <Column field="keyword" header="Keyword" sortable frozen style={{ fontWeight: 600, minWidth: '14rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} />
          <Column field="volume" header="Volume" sortable style={{ width: '8rem' }} />
          <Column field="kd" header="KD" sortable style={{ width: '6rem' }} />
          <Column field="cpc" header="CPC" sortable style={{ width: '7rem' }} body={(rowData) => (rowData.cpc != null ? `₹${rowData.cpc}` : '—')} />
          <Column field="competition" header="Competition" sortable style={{ width: '8rem' }} body={(rowData) => (rowData.competition != null ? rowData.competition.toFixed(2) : '—')} />
          <Column field="backlinks" header="Backlinks" sortable style={{ width: '8rem' }} body={(rowData) => (rowData.backlinks != null ? Math.round(rowData.backlinks).toLocaleString('en-US') : '—')} />
          <Column field="referring_domains" header="Domains" sortable style={{ width: '8rem' }} body={(rowData) => (rowData.referring_domains != null ? Math.round(rowData.referring_domains).toLocaleString('en-US') : '—')} />
          <Column field="intent" header="Intent" style={{ width: '8rem' }} body={(rowData) => <span className="capitalize">{rowData.intent || '—'}</span>} />
          <Column field="position" header="Position" sortable style={{ width: '7rem' }} body={positionBodyTemplate} />
          {hasAioEnabled && <Column header="AIO" style={{ width: '6rem' }} body={aioBodyTemplate} />}
          <Column header="✨ AI" style={{ width: '7rem' }} body={aioToggleBodyTemplate} />
          <Column header="Actions" body={actionBodyTemplate} style={{ width: '5rem' }} />
        </DataTable>

        {selectedIds.length > 0 && (
          <div className="border-t border-slate-200 bg-rose-50 px-5 py-3 flex items-center justify-between">
            <span className="text-sm font-medium text-rose-700">{selectedIds.length} selected</span>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={() => handleBulkAioToggle(true)}
                disabled={tableLoading || bulkAioLoading}
              >
                ✨ Enable AIO
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleBulkAioToggle(false)}
                disabled={tableLoading || bulkAioLoading}
              >
                Disable AIO
              </Button>
              <Button variant="danger" onClick={handleDeleteSelected}
                disabled={tableLoading || bulkAioLoading}> <FontAwesomeIcon icon={faTrash} />Delete selected</Button>
            </div>
          </div>
        )}

        {tableError && <Alert variant="error" message={tableError} />}
      </section>

      <Modal
        open={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Keywords"
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setIsAddModalOpen(false)} >Cancel</Button>
            <Button onClick={handleAddKeywords} disabled={!keywordText.trim()} >
              <FontAwesomeIcon icon={faPlus} /> Add Keywords
            </Button>
          </>
        }
      >
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
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Location</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Location"
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Device</label>
              <select
                value={device}
                onChange={(e) => setDevice(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
              >
                <option value="desktop">Desktop</option>
                <option value="mobile">Mobile</option>
              </select>
            </div>
          </div>
          <div>
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
              <FontAwesomeIcon icon={faUpload} />
              <span>Upload CSV</span>
              <input type="file" accept=".csv" onChange={handleCsvChange} className="hidden" />
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
          description={
            keywordLimitRemaining < csvPreview.length
              ? `Warning: You can only add ${keywordLimitRemaining} more keywords.`
              : 'This will add the keywords to the current project.'
          }
          confirmText="Import"
          cancelText="Cancel"
          tone={keywordLimitRemaining < csvPreview.length ? 'warning' : 'info'}
          icon={faUpload}
          loading={false}
          onConfirm={handleCsvConfirm}
          onClose={() => {
            setShowCsvConfirm(false);
            setCsvPreview([]);
          }}
        />
      )}

      <ConfirmModal
        open={aioConfirm.open}
        title={aioConfirm.currentTrackAio ? 'Disable Premium AI Tracking?' : '✨ Enable Premium AI Tracking?'}
        message={aioConfirm.currentTrackAio
          ? `Stop monitoring Google AI Overviews for "${aioConfirm.keywordText}"? No refund will be issued.`
          : `Monitoring real-time Google AI Overviews for "${aioConfirm.keywordText}" will deduct 20 additional credits from your balance. Proceed?`
        }
        description="This setting applies to your tracked keywords and will be used in the next tracking cycle."
        confirmText={aioConfirm.currentTrackAio ? 'Disable' : 'Enable AI Tracking'}
        cancelText="Cancel"
        tone={aioConfirm.currentTrackAio ? 'danger' : 'info'}
        icon={faTriangleExclamation}
        loading={aioLoading[aioConfirm.keywordId]}
        onConfirm={handleAioConfirm}
        onClose={() => setAioConfirm((s) => ({ ...s, open: false }))}
      />

      <ConfirmModal
        open={bulkAioConfirm.open}
        title={bulkAioConfirm.targetAio ? '✨ Enable Premium AI Tracking for Selected?' : 'Disable Premium AI Tracking for Selected?'}
        message={bulkAioConfirm.targetAio
          ? `Enable AI tracking for ${selectedIds.length} selected keywords? This will deduct 20 credits per keyword from your balance.`
          : `Disable AI tracking for ${selectedIds.length} selected keywords? No refund will be issued.`
        }
        description="This change will apply to all selected keywords in the next tracking cycle."
        confirmText={bulkAioConfirm.targetAio ? 'Enable AI Tracking' : 'Disable AI Tracking'}
        cancelText="Cancel"
        tone={bulkAioConfirm.targetAio ? 'info' : 'danger'}
        icon={faTriangleExclamation}
        loading={bulkAioLoading}
        onConfirm={handleBulkAioConfirm}
        onClose={() => setBulkAioConfirm((s) => ({ ...s, open: false }))}
      />
    </div>
  );
}

export default KeywordsPage;
