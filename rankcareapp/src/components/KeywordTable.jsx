'use client'
import { useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faTrash,
  faTrashCan,
  faTriangleExclamation,
  faUpload,
} from '@fortawesome/free-solid-svg-icons';
import ConfirmModal from './ConfirmModal';
import Button from './ui/Button';
import Alert from './ui/Alert';
import {
  addKeywordToProject,
  bulkAddKeywords,
  bulkDeleteKeywords,
  bulkDeleteRankings,
  clearKeywordMessage,
  clearProjectRankings,
  deleteKeywordById,
  deleteRankingById,
  runRankCheck,
  setKeywordSearch,
  setSortBy,
} from '../features/keywords/keywordsSlice';

function KeywordTable() {
  const dispatch = useDispatch();

  const {
    keywords,
    rankings,
    search,
    sortBy,
    loadingKeywords,
    loadingRankings,
    adding,
    running,
    deletingKeyword,
    deletingRanking,
    clearingRankings,
    deletingBulkKeywords,
    deletingBulkRankings,
    error,
    actionMessage,
  } = useSelector((state) => state.keywords);

  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);
  const pricingCurrent = useSelector((state) => state.pricing.current);

  const [keywordText, setKeywordText] = useState('');
  const [location, setLocation] = useState('India');
  const [device, setDevice] = useState('desktop');
  const [csvPreview, setCsvPreview] = useState([]);
  const [showCsvConfirm, setShowCsvConfirm] = useState(false);

  const [selectedKeywords, setSelectedKeywords] = useState([]);
  const [selectedRankings, setSelectedRankings] = useState([]);

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

  const isBulkLoading = deletingBulkKeywords || deletingBulkRankings || clearingRankings;

  const filteredKeywords = useMemo(() => {
    return (keywords || []).filter((row) => {
      const kw = (row.keyword || '').toLowerCase();
      return kw.includes((search || '').toLowerCase());
    });
  }, [keywords, search]);

  const filteredRankings = useMemo(() => {
    return (rankings || [])
      .filter((row) => {
        const kw = (row.keywordText || '').toLowerCase();
        return kw.includes((search || '').toLowerCase());
      })
      .sort((a, b) => {
        if (sortBy === 'position') return (a.position ?? 9999) - (b.position ?? 9999);
        if (sortBy === 'checkedAt') {
          return new Date(b.checkedAt || 0) - new Date(a.checkedAt || 0);
        }
        if (sortBy === 'keyword') {
          return (a.keywordText || '').localeCompare(b.keywordText || '');
        }
        return 0;
      });
  }, [rankings, search, sortBy]);

  const openConfirmModal = ({
    title,
    message,
    description = '',
    confirmText = 'Confirm',
    tone = 'danger',
    icon = null,
    onConfirm,
  }) => {
    setConfirmState({
      open: true,
      title,
      message,
      description,
      confirmText,
      tone,
      icon,
      onConfirm,
    });
  };

  const closeConfirmModal = () => {
    if (isBulkLoading) return;
    setConfirmState({
      open: false,
      title: '',
      message: '',
      description: '',
      confirmText: 'Confirm',
      tone: 'danger',
      icon: null,
      onConfirm: null,
    });
  };

  const handleBulkKeywordConfirm = async () => {
    if (!selectedProjectId) return;
    dispatch(clearKeywordMessage());
    const resultAction = await dispatch(
      bulkDeleteKeywords({
        projectId: selectedProjectId,
        keywordIds: selectedKeywords,
      })
    );

    if (bulkDeleteKeywords.fulfilled.match(resultAction)) {
      setSelectedKeywords([]);
      closeConfirmModal();
    }
  };

  const handleBulkRankingConfirm = async () => {
    if (!selectedProjectId) return;
    dispatch(clearKeywordMessage());
    const resultAction = await dispatch(
      bulkDeleteRankings({
        projectId: selectedProjectId,
        rankingIds: selectedRankings,
      })
    );

    if (bulkDeleteRankings.fulfilled.match(resultAction)) {
      setSelectedRankings([]);
      closeConfirmModal();
    }
  };

  const handleDeleteKeyword = (keywordRow) => {
    if (!selectedProjectId) return;

    openConfirmModal({
      title: 'Delete keyword',
      message: `Delete "${keywordRow.keyword}"?`,
      description: 'Any related ranking results for this keyword may also be affected.',
      confirmText: 'Delete keyword',
      tone: 'danger',
      icon: faTrashCan,
      onConfirm: async () => {
        dispatch(clearKeywordMessage());
        const resultAction = await dispatch(
          deleteKeywordById({
            keywordId: keywordRow.id,
            projectId: selectedProjectId,
          })
        );

        if (deleteKeywordById.fulfilled.match(resultAction)) {
          closeConfirmModal();
        }
      },
    });
  };

  const handleDeleteRanking = (rankingRow) => {
    if (!selectedProjectId) return;

    openConfirmModal({
      title: 'Delete ranking result',
      message: `Delete ranking result for "${rankingRow.keywordText}"?`,
      description: 'This action cannot be undone.',
      confirmText: 'Delete result',
      tone: 'danger',
      icon: faTrashCan,
      onConfirm: async () => {
        dispatch(clearKeywordMessage());
        const resultAction = await dispatch(
          deleteRankingById({
            rankingId: rankingRow.id,
            projectId: selectedProjectId,
          })
        );

        if (deleteRankingById.fulfilled.match(resultAction)) {
          closeConfirmModal();
        }
      },
    });
  };

  const handleClearRankings = () => {
    if (!selectedProjectId) return;

    openConfirmModal({
      title: 'Clear rankings',
      message: 'Clear all ranking results for this project?',
      description: 'Keywords will stay saved, but all ranking history will be removed.',
      confirmText: 'Clear rankings',
      tone: 'warning',
      icon: faTriangleExclamation,
      onConfirm: async () => {
        dispatch(clearKeywordMessage());
        const resultAction = await dispatch(clearProjectRankings(selectedProjectId));

        if (clearProjectRankings.fulfilled.match(resultAction)) {
          closeConfirmModal();
        }
      },
    });
  };

  const handleAddKeywords = async (e) => {
    e.preventDefault();
    if (!selectedProjectId || !keywordText.trim()) return;

    const parsed = keywordText
      .split(',')
      .map((kw) => kw.trim())
      .filter((kw) => kw.length > 0);

    if (parsed.length === 0) return;

    const resultAction = await dispatch(
      parsed.length === 1
        ? addKeywordToProject({
            projectId: selectedProjectId,
            payload: { keyword: parsed[0], location: location },
          })
        : bulkAddKeywords({
            projectId: selectedProjectId,
            keywords: parsed,
          })
    );

    if (
      parsed.length === 1
        ? addKeywordToProject.fulfilled.match(resultAction)
        : bulkAddKeywords.fulfilled.match(resultAction)
    ) {
      setKeywordText('');
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
      })
    );

    if (bulkAddKeywords.fulfilled.match(resultAction)) {
      setCsvPreview([]);
    }
  };

  const handleRunRankCheck = async () => {
    if (!selectedProjectId) return;
    dispatch(clearKeywordMessage());
    await dispatch(runRankCheck(selectedProjectId));
  };

  const toggleKeyword = (id) => {
    setSelectedKeywords((prev) =>
      prev.includes(id) ? prev.filter((k) => k !== id) : [...prev, id]
    );
  };

  const toggleAllKeywords = () => {
    const allFilteredIds = filteredKeywords.map((k) => k.id);
    const allSelected = allFilteredIds.length > 0 && allFilteredIds.every((id) => selectedKeywords.includes(id));

    if (allSelected) {
      setSelectedKeywords([]);
    } else {
      setSelectedKeywords(allFilteredIds);
    }
  };

  const toggleRanking = (id) => {
    setSelectedRankings((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const toggleAllRankings = () => {
    const allFilteredIds = filteredRankings.map((r) => r.id);
    const allSelected = allFilteredIds.length > 0 && allFilteredIds.every((id) => selectedRankings.includes(id));

    if (allSelected) {
      setSelectedRankings([]);
    } else {
      setSelectedRankings(allFilteredIds);
    }
  };

  if (!selectedProjectId) {
    return (
      <section className="rounded-xs border border-slate-200 bg-white p-6 shadow-soft">
        <p className="text-sm text-slate-500">
          Select a project first to manage keywords and rankings.
        </p>
      </section>
    );
  }

  return (
    <>
      <div className="space-y-6">
        <section className="rounded-xs border border-slate-200 bg-white shadow-soft">
          <div className="border-b border-slate-200 p-5">
            <h3 className="text-lg font-semibold text-slate-900">Add keywords</h3>
            <p className="mt-1 text-sm text-slate-500">
              Add keywords for the selected project before running rank checks.
            </p>
          </div>

          <form onSubmit={handleAddKeywords} className="grid gap-4 p-5">
            <textarea
              value={keywordText}
              onChange={(e) => setKeywordText(e.target.value)}
              placeholder="Enter keywords separated by commas"
              rows={3}
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            />

            <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Location"
                className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
              />

              <select
                value={device}
                onChange={(e) => setDevice(e.target.value)}
                className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
              >
                <option value="desktop">Desktop</option>
                <option value="mobile">Mobile</option>
              </select>

              <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
                <FontAwesomeIcon icon={faUpload} />
                <span>CSV</span>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleCsvChange}
                  className="hidden"
                />
              </label>

              <Button
                type="submit"
                disabled={adding || !keywordText.trim()}
                loading={adding}
              >
                Add Keywords
              </Button>
            </div>
          </form>

          {actionMessage && <Alert variant="success" message={actionMessage} />}
          {error && <Alert variant="error" message={error} />}
        </section>

        <section className="rounded-xs border border-slate-200 bg-white shadow-soft">
          <div className="flex flex-col gap-4 border-b border-slate-200 p-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Tracked keywords</h3>
              <p className="mt-1 text-sm text-slate-500">
                Keywords saved for this project.
              </p>
            </div>

            <input
              type="text"
              value={search}
              onChange={(e) => dispatch(setKeywordSearch(e.target.value))}
              placeholder="Search keyword..."
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            />
          </div>

          {selectedKeywords.length > 0 && (
            <div className="border-b border-slate-200 bg-rose-50 px-5 py-3 flex items-center justify-between">
              <span className="text-sm font-medium text-rose-700">
                {selectedKeywords.length} selected
              </span>
              <Button
                onClick={() => {
                  openConfirmModal({
                    title: 'Delete selected keywords',
                    message: `Delete ${selectedKeywords.length} selected keywords?`,
                    description: 'This action cannot be undone.',
                    confirmText: 'Delete selected',
                    tone: 'danger',
                    icon: faTrashCan,
                    onConfirm: handleBulkKeywordConfirm,
                  });
                }}
                disabled={isBulkLoading}
                variant="danger"
              >
                Delete selected
              </Button>
            </div>
          )}

          {loadingKeywords ? (
            <div className="p-5 text-sm text-slate-500">Loading keywords...</div>
          ) : (
            <div className="overflow-x-auto">
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table className="min-w-full text-left">
                  <thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                    <tr>
                    <th className="px-5 py-4 w-12">
                      <input
                        type="checkbox"
                        checked={filteredKeywords.length > 0 && selectedKeywords.length === filteredKeywords.length}
                        onChange={toggleAllKeywords}
                        className="h-4 w-4 rounded border-slate-300"
                      />
                    </th>
                    <th className="px-5 py-4">Keyword</th>
                    <th className="px-5 py-4">Device</th>
                    <th className="px-5 py-4">Location</th>
                    <th className="px-5 py-4">Created at</th>
                    <th className="px-5 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredKeywords.map((row) => (
                    <tr key={row.id} className="border-t border-slate-100">
                      <td className="px-5 py-4 w-12">
                        <input
                          type="checkbox"
                          checked={selectedKeywords.includes(row.id)}
                          onChange={() => toggleKeyword(row.id)}
                          className="h-4 w-4 rounded border-slate-300"
                        />
                      </td>
                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {row.keyword || '-'}
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-700">
                        {row.device || '-'}
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-700">
                        {row.location || '-'}
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-700">
                        {row.createdAt ? new Date(row.createdAt).toLocaleString('en-US') : '-'}
                      </td>
                      <td className="px-5 py-4">
                        <Button
                          onClick={() => handleDeleteKeyword(row)}
                          disabled={deletingKeyword}
                          variant="ghost"
                          className="!text-red-600 hover:!text-red-700"
                        >
                          <FontAwesomeIcon icon={faTrash} />
                        </Button>
                      </td>
                    </tr>
                  ))}

                  {filteredKeywords.length === 0 && (
                    <tr>
                      <td colSpan="6" className="px-5 py-10 text-center text-sm text-slate-500">
                        No keywords added yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
          )}
          {filteredRankings.length > 0 && (
            <div className="border-t border-slate-200 px-5 py-3 text-center text-xs text-slate-400">
              Showing {filteredRankings.length} ranking{filteredRankings.length === 1 ? '' : 's'}
            </div>
          )}
        </section>

        <section className="rounded-xs border border-slate-200 bg-white shadow-soft">
          <div className="flex flex-col gap-4 border-b border-slate-200 p-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Rankings</h3>
              <p className="mt-1 text-sm text-slate-500">
                Run a rank check to fetch the latest positions.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <select
                value={sortBy}
                onChange={(e) => dispatch(setSortBy(e.target.value))}
                className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
              >
                <option value="position">Sort by Position</option>
                <option value="checkedAt">Sort by Last Checked</option>
                <option value="keyword">Sort by Keyword</option>
              </select>

              <Button
                onClick={handleClearRankings}
                disabled={clearingRankings || filteredRankings.length === 0}
                variant="danger"
              >
                {clearingRankings ? 'Clearing...' : 'Clear Rankings'}
              </Button>

              <Button
                onClick={handleRunRankCheck}
                disabled={running}
                variant="primary"
              >
                {running ? 'Running...' : 'Run Rank Check'}
              </Button>
            </div>
          </div>

          {selectedRankings.length > 0 && (
            <div className="border-b border-slate-200 bg-rose-50 px-5 py-3 flex items-center justify-between">
              <span className="text-sm font-medium text-rose-700">
                {selectedRankings.length} selected
              </span>
              <Button
                onClick={() => {
                  openConfirmModal({
                    title: 'Delete selected rankings',
                    message: `Delete ${selectedRankings.length} selected ranking results?`,
                    description: 'This action cannot be undone.',
                    confirmText: 'Delete selected',
                    tone: 'danger',
                    icon: faTrashCan,
                    onConfirm: handleBulkRankingConfirm,
                  });
                }}
                disabled={isBulkLoading}
                variant="danger"
              >
                Delete selected
              </Button>
            </div>
          )}

          {loadingRankings ? (
            <div className="p-5 text-sm text-slate-500">
              Running rank check and waiting for results...
            </div>
          ) : (
            <div className="overflow-x-auto">
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table className="min-w-full text-left">
                  <thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                    <tr>
                    <th className="px-5 py-4 w-12">
                      <input
                        type="checkbox"
                        checked={filteredRankings.length > 0 && selectedRankings.length === filteredRankings.length}
                        onChange={toggleAllRankings}
                        className="h-4 w-4 rounded border-slate-300"
                      />
                    </th>
                    <th className="px-5 py-4">Keyword</th>
                    <th className="px-5 py-4">URL</th>
                    <th className="px-5 py-4">Position</th>
                    <th className="px-5 py-4">Device</th>
                    <th className="px-5 py-4">Location</th>
                    <th className="px-5 py-4">Checked at</th>
                    <th className="px-5 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRankings.map((row) => (
                    <tr key={row.id} className="border-t border-slate-100">
                      <td className="px-5 py-4 w-12">
                        <input
                          type="checkbox"
                          checked={selectedRankings.includes(row.id)}
                          onChange={() => toggleRanking(row.id)}
                          className="h-4 w-4 rounded border-slate-300"
                        />
                      </td>
                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {row.keywordText || '-'}
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-500">{row.url || '-'}</td>
                      <td className="px-5 py-4 text-sm font-semibold text-slate-900">
                        {row.position ? `#${row.position}` : '-'}
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-700">
                        {row.device || '-'}
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-700">
                        {row.location || '-'}
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-700">
                        {row.checkedAt ? new Date(row.checkedAt).toLocaleString('en-US') : '-'}
                      </td>
                      <td className="px-5 py-4">
                        <Button
                          onClick={() => handleDeleteRanking(row)}
                          disabled={deletingRanking}
                          variant="ghost"
                          className="!text-red-600 hover:!text-red-700"
                        >
                          <FontAwesomeIcon icon={faTrash} />
                        </Button>
                      </td>
                    </tr>
                  ))}

                  {filteredRankings.length === 0 && (
                    <tr>
                      <td colSpan="8" className="px-5 py-10 text-center text-sm text-slate-500">
                        No rankings available yet. Add a keyword and run rank check.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
          )}
          {filteredRankings.length > 0 && (
            <div className="border-t border-slate-200 px-5 py-3 text-center text-xs text-slate-400">
              Showing {filteredRankings.length} ranking{filteredRankings.length === 1 ? '' : 's'}
            </div>
          )}
        </section>
      </div>

      <ConfirmModal
        open={confirmState.open}
        title={confirmState.title}
        message={confirmState.message}
        description={confirmState.description}
        confirmText={confirmState.confirmText}
        cancelText="Cancel"
        tone={confirmState.tone}
        icon={confirmState.icon}
        loading={isBulkLoading}
        onConfirm={confirmState.onConfirm}
        onClose={closeConfirmModal}
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
          loading={adding}
          onConfirm={handleCsvConfirm}
          onClose={() => {
            setShowCsvConfirm(false);
            setCsvPreview([]);
          }}
        />
      )}
    </>
  );
}

export default KeywordTable;
