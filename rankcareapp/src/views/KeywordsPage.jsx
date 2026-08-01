'use client'
import { useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faTrashCan,
  faUpload,
  faFilter,
  faXmark,
  faTriangleExclamation,
  faPlus,
} from '@fortawesome/free-solid-svg-icons';
import ConfirmModal from '../components/ConfirmModal';
import Modal from '../components/ui/Modal';
import Button from '../components/ui/Button';
import Alert from '../components/ui/Alert';
import Input from '../components/ui/Input';
import {
  bulkAddKeywords,
  bulkDeleteKeywords,
  clearKeywordMessage,
  deleteKeywordById,
} from '../features/keywords/keywordsSlice';

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
  const [searchQuery, setSearchQuery] = useState('');
  const [aioFilter, setAioFilter] = useState('all'); // all, yes, no
  const [rankFilter, setRankFilter] = useState('all'); // all, top3, top10, not-ranking
  const [sortField, setSortField] = useState('keyword');
  const [sortDir, setSortDir] = useState('asc');
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

  const filteredRows = useMemo(() => {
    let rows = [...tableData];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      rows = rows.filter((r) => r.keyword.toLowerCase().includes(q));
    }
    if (aioFilter === 'yes') rows = rows.filter((r) => r.hasAIOverview);
    if (aioFilter === 'no') rows = rows.filter((r) => !r.hasAIOverview);
    if (rankFilter === 'top3') rows = rows.filter((r) => r.position !== null && r.position <= 3);
    if (rankFilter === 'top10') rows = rows.filter((r) => r.position !== null && r.position <= 10);
    if (rankFilter === 'not-ranking') rows = rows.filter((r) => r.position === null || r.position === undefined);

    rows.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      if (sortField === 'keyword') return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      if (sortField === 'volume' || sortField === 'kd' || sortField === 'cpc' || sortField === 'competition' || sortField === 'backlinks' || sortField === 'referring_domains' || sortField === 'position') {
        const aN = Number(aVal) || 9999;
        const bN = Number(bVal) || 9999;
        return sortDir === 'asc' ? aN - bN : bN - aN;
      }
      return 0;
    });
    return rows;
  }, [tableData, searchQuery, aioFilter, rankFilter, sortField, sortDir]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

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

    const resultAction = await dispatch(
      bulkAddKeywords({
        projectId: selectedProjectId,
        keywords: parsed,
        location: location,
      })
    );

    if (bulkAddKeywords.fulfilled.match(resultAction)) {
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

  const toggleSelect = (id) => {
    setSelectedIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const toggleSelectAll = () => {
    const allIds = filteredRows.map((r) => r.id);
    const allSelected = allIds.length > 0 && allIds.every((id) => selectedIds.includes(id));
    setSelectedIds(allSelected ? [] : allIds);
  };

  const handleDeleteSelected = () => {
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

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <span className="ml-1 text-slate-400">↕</span>;
    return <span className="ml-1 text-brand-600">{sortDir === 'asc' ? '↑' : '↓'}</span>;
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
            Tracked keywords with rank, volume, difficulty, CPC, and AIO status.
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
        <div className="flex flex-col gap-4 border-b border-slate-200 p-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Keyword Overview</h3>
            <p className="mt-1 text-sm text-slate-500">
              Rank tracking, volume, difficulty, CPC, and AIO status in one place.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search keywords..."
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            />
            <select
              value={aioFilter}
              onChange={(e) => setAioFilter(e.target.value)}
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            >
              <option value="all">All AIO</option>
              <option value="yes">Has AIO</option>
              <option value="no">No AIO</option>
            </select>
            <select
              value={rankFilter}
              onChange={(e) => setRankFilter(e.target.value)}
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            >
              <option value="all">All Ranks</option>
              <option value="top3">Top 3</option>
              <option value="top10">Top 10</option>
              <option value="not-ranking">Not Ranking</option>
            </select>
            <Button variant="secondary" onClick={fetchTableData} disabled={tableLoading}>
              <FontAwesomeIcon icon={faFilter} /> Refresh
            </Button>
          </div>
          {nextRefresh && (
            <div className="text-xs text-slate-400 mt-2">
              Next data refresh: {new Date(nextRefresh).toLocaleString()}
            </div>
          )}
        </div>

        {selectedIds.length > 0 && (
          <div className="border-b border-slate-200 bg-rose-50 px-5 py-3 flex items-center justify-between">
            <span className="text-sm font-medium text-rose-700">{selectedIds.length} selected</span>
            <Button onClick={handleDeleteSelected} variant="danger" disabled={tableLoading}>
              Delete selected
            </Button>
          </div>
        )}

        {tableError && <Alert variant="error" message={tableError} />}

        {tableLoading ? (
          <div className="p-5 text-sm text-slate-500">Loading keyword data...</div>
        ) : (
          <div className="overflow-x-auto">
            <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
              <table className="min-w-full text-left">
                <thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                  <tr>
                    <th className="px-4 py-3 w-10">
                      <input
                        type="checkbox"
                        checked={filteredRows.length > 0 && selectedIds.length === filteredRows.length}
                        onChange={toggleSelectAll}
                        className="h-4 w-4 rounded border-slate-300"
                      />
                    </th>
                    <th className="px-4 py-3 cursor-pointer" onClick={() => handleSort('keyword')}>
                      Keyword <SortIcon field="keyword" />
                    </th>
                    <th className="px-4 py-3 cursor-pointer" onClick={() => handleSort('volume')}>
                      Volume <SortIcon field="volume" />
                    </th>
                    <th className="px-4 py-3 cursor-pointer" onClick={() => handleSort('kd')}>
                      KD <SortIcon field="kd" />
                    </th>
                    <th className="px-4 py-3 cursor-pointer" onClick={() => handleSort('cpc')}>
                      CPC <SortIcon field="cpc" />
                    </th>
                    <th className="px-4 py-3 cursor-pointer" onClick={() => handleSort('competition')}>
                      Competition <SortIcon field="competition" />
                    </th>
                    <th className="px-4 py-3 cursor-pointer" onClick={() => handleSort('backlinks')}>
                      Backlinks <SortIcon field="backlinks" />
                    </th>
                    <th className="px-4 py-3 cursor-pointer" onClick={() => handleSort('referring_domains')}>
                      Domains <SortIcon field="referring_domains" />
                    </th>
                    <th className="px-4 py-3">Intent</th>
                    <th className="px-4 py-3 cursor-pointer" onClick={() => handleSort('position')}>
                      Position <SortIcon field="position" />
                    </th>
                    <th className="px-4 py-3">AIO</th>
                    <th className="px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row) => (
                    <tr key={row.id} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-3 w-10">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(row.id)}
                          onChange={() => toggleSelect(row.id)}
                          className="h-4 w-4 rounded border-slate-300"
                        />
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900">{row.keyword}</td>
                      <td className="px-4 py-3 text-sm text-slate-700">{row.volume ?? '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-700">{row.kd ?? '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-700">{row.cpc != null ? `₹${row.cpc}` : '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-700">{row.competition != null ? row.competition.toFixed(2) : '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-700">{row.backlinks != null ? Math.round(row.backlinks).toLocaleString() : '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-700">{row.referring_domains != null ? Math.round(row.referring_domains).toLocaleString() : '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-700 capitalize">{row.intent || '—'}</td>
                      <td className="px-4 py-3 text-sm font-semibold text-slate-900">
                        {row.position ? `#${row.position}` : '—'}
                      </td>
                      <td className="px-4 py-3">
                        {row.hasAIOverview ? (
                          <span className="inline-flex rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">AIO</span>
                        ) : (
                          <span className="text-slate-400 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Button onClick={() => handleDeleteOne(row)} disabled={false} variant="ghost" className="!text-red-600 hover:!text-red-700">
                          <FontAwesomeIcon icon={faTrashCan} />
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {filteredRows.length === 0 && (
                    <tr>
                      <td colSpan="12" className="px-4 py-10 text-center text-sm text-slate-500">
                        No keywords found. Add keywords to get started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {filteredRows.length > 0 && (
          <div className="border-t border-slate-200 px-5 py-3 text-center text-xs text-slate-400">
            Showing {filteredRows.length} keyword{filteredRows.length === 1 ? '' : 's'}
          </div>
        )}
      </section>

      <Modal
        open={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Keywords"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddKeywords} disabled={!keywordText.trim()}>
              Add Keywords
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
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none w-full"
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
                className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Device</label>
              <select
                value={device}
                onChange={(e) => setDevice(e.target.value)}
                className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none w-full"
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
    </div>
  );
}

export default KeywordsPage;
