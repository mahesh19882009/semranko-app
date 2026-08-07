'use client'
import { useEffect, useMemo, useState, useRef } from 'react';
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
  faStars,
  faWandSparkles,
} from '@fortawesome/free-solid-svg-icons';
import ConfirmModal from '../components/ConfirmModal';
import Modal from '../components/ui/Modal';
import Alert from '../components/ui/Alert';
import { formatDateTime } from '../utils/date';
import {
  addKeywordToProject,
  bulkAddKeywords,
  bulkDeleteKeywords,
  clearKeywordMessage,
  deleteKeywordById,
} from '../features/keywords/keywordsSlice';
import { getAioDetailApi } from '../lib/api';

const rankOptions = [
  { label: 'All Ranks', value: 'all' },
  { label: 'Top 3', value: 'top3' },
  { label: 'Top 10', value: 'top10' },
  { label: 'Not Ranking', value: 'not-ranking' },
];

function KeywordsPage() {
  const dispatch = useDispatch();
  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);
  const projects = useSelector((state) => state.projects.list);
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
  const [aioModalOpen, setAioModalOpen] = useState(false);
  const [aioModalKeyword, setAioModalKeyword] = useState(null);
  const [aioModalData, setAioModalData] = useState(null);
  const [aioModalLoading, setAioModalLoading] = useState(false);
  const [aioModalError, setAioModalError] = useState('');

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
      const token = localStorage.getItem('accessToken');
      const res = await fetch(`/api/keywords/${selectedProjectId}/table`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      if (!res.ok || !json.success) throw new Error(json.message || 'Failed to load keywords');
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
    if (rankFilter === 'top3') rows = rows.filter((r) => r.position !== null && r.position <= 3);
    if (rankFilter === 'top10') rows = rows.filter((r) => r.position !== null && r.position <= 10);
    if (rankFilter === 'not-ranking') rows = rows.filter((r) => r.position === null || r.position === undefined);
    return rows;
  }, [tableData, globalFilter, rankFilter]);

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

  const handleAioBadgeClick = async (rowData) => {
    if (!rowData.hasAIOverview) return;
    setAioModalKeyword(rowData);
    setAioModalOpen(true);
    setAioModalLoading(true);
    setAioModalError('');
    setAioModalData(null);
    try {
      const result = await getAioDetailApi(selectedProjectId, rowData.keyword);
      setAioModalData(result.data);
    } catch (err) {
      setAioModalError(err?.message || 'Failed to load AIO details');
    } finally {
      setAioModalLoading(false);
    }
  };

  const aiBodyTemplate = (rowData) => {
    const hasAI = rowData.hasAIOverview;
    return (
      <button
        onClick={() => handleAioBadgeClick(rowData)}
        disabled={!hasAI}
        className={`inline-flex items-center gap-1 rounded-full px-3 py-3 text-xs font-medium transition-colors ${hasAI
          ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 cursor-pointer'
          : 'bg-slate-100 text-slate-500 cursor-default'
          }`}
      >
        <FontAwesomeIcon icon={faWandSparkles} /> AI
      </button>
    );
  };

  const visibilityBodyTemplate = (rowData) => {
    const vis = rowData.visibility;
    if (vis === null || vis === undefined) return '—';
    return `${(vis * 100).toFixed(0)}%`;
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
        >
          <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} frozen style={{ width: '3rem' }} />
          <Column field="keyword" header="Keyword" sortable frozen style={{ fontWeight: 600, minWidth: '14rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} />
          <Column field="volume" header="Volume" sortable style={{ width: '8rem' }} />
          <Column field="kd" header="KD" sortable style={{ width: '6rem' }} />
          <Column field="cpc" header="CPC" sortable style={{ width: '7rem' }} body={(rowData) => (rowData.cpc != null ? `₹${rowData.cpc}` : '—')} />
          <Column field="competition" header="Competition" sortable style={{ width: '8rem' }} body={(rowData) => (rowData.competition != null ? rowData.competition.toFixed(2) : '—')} />
          <Column field="backlinks" header="Backlinks" sortable style={{ width: '8rem' }} body={(rowData) => (rowData.backlinks != null ? Math.round(rowData.backlinks).toLocaleString('en-US') : '—')} />
          <Column field="domains" header="Domains" sortable style={{ width: '8rem' }} body={(rowData) => (rowData.domains != null ? Math.round(rowData.domains).toLocaleString('en-US') : '—')} />
          <Column field="intent" header="Intent" style={{ width: '8rem' }} body={(rowData) => <span className="capitalize">{rowData.intent || '—'}</span>} />
          <Column field="position" header="Position" sortable style={{ width: '7rem' }} body={positionBodyTemplate} />
          <Column field="visibility" header="Visibility" sortable style={{ width: '8rem' }} body={visibilityBodyTemplate} />
          <Column header="AIO" style={{ width: '8rem' }} body={aiBodyTemplate} />
          <Column header="Actions" body={actionBodyTemplate} style={{ width: '5rem' }} />
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
          description="This will add the keywords to the current project."
          confirmText="Import"
          cancelText="Cancel"
          tone="info"
          icon={faUpload}
          loading={false}
          onConfirm={handleCsvConfirm}
          onClose={() => {
            setShowCsvConfirm(false);
            setCsvPreview([]);
          }}
        />
      )}

      <Modal
        open={aioModalOpen}
        onClose={() => setAioModalOpen(false)}
        title={aioModalKeyword ? `AIO Overview: ${aioModalKeyword.keyword}` : 'AIO Overview'}
        size="lg"
      >
        {aioModalLoading && (
          <div className="flex items-center justify-center py-10">
            <p className="text-sm text-slate-500">Loading AIO details...</p>
          </div>
        )}
        {aioModalError && <Alert variant="error" className="mb-4" message={aioModalError} />}
        {!aioModalLoading && !aioModalError && aioModalData && (
          <div className="space-y-4">
            {aioModalData.aiOverviewTitle && (
              <div>
                <h3 className="text-lg font-semibold text-slate-900">{aioModalData.aiOverviewTitle}</h3>
              </div>
            )}
            {aioModalData.aiOverviewType && (
              <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                {aioModalData.aiOverviewType}
              </span>
            )}
            {aioModalData.aiOverviewMarkdown ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <pre className="whitespace-pre-wrap text-sm text-slate-700">{aioModalData.aiOverviewMarkdown}</pre>
              </div>
            ) : aioModalData.aiOverviewText ? (
              <p className="text-sm text-slate-700">{aioModalData.aiOverviewText}</p>
            ) : (
              <p className="text-sm text-slate-500">No AI Overview content available for this keyword.</p>
            )}
            {aioModalData.references && Array.isArray(aioModalData.references) && aioModalData.references.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-slate-900 mb-2">References</h4>
                <ul className="space-y-1">
                  {aioModalData.references.map((ref, idx) => (
                    <li key={idx} className="text-sm text-blue-600">
                      {ref.url || ref.domain || JSON.stringify(ref)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {aioModalData.images && Array.isArray(aioModalData.images) && aioModalData.images.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-slate-900 mb-2">Images</h4>
                <div className="flex flex-wrap gap-2">
                  {aioModalData.images.map((img, idx) => (
                    <img key={idx} src={img.url || img} alt={img.title || `Image ${idx + 1}`} className="h-24 w-24 rounded-lg object-cover border border-slate-200" />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        {!aioModalLoading && !aioModalError && !aioModalData && (
          <p className="text-sm text-slate-500">No AI Overview data available for this keyword.</p>
        )}
      </Modal>
    </div>
  );
}

export default KeywordsPage;
