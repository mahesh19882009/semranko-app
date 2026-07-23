import { useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { faTrashCan, faTriangleExclamation } from '@fortawesome/free-solid-svg-icons';
import ConfirmModal from './ConfirmModal';
import {
  addKeywordToProject,
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
    error,
    actionMessage,
  } = useSelector((state) => state.keywords);

  const selectedProjectId = useSelector((state) => state.projects.selectedProjectId);

  const [formData, setFormData] = useState({
    keyword: '',
    location: 'India',
    device: 'desktop',
  });

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

  const filteredKeywords = useMemo(() => {
    return (keywords || []).filter((row) => {
      const keyword = (row.keyword || '').toLowerCase();
      const searchText = (search || '').toLowerCase();
      return keyword.includes(searchText);
    });
  }, [keywords, search]);

  const filteredRankings = useMemo(() => {
    return (rankings || [])
      .filter((row) => {
        const keyword = (row.keywordText || '').toLowerCase();
        const searchText = (search || '').toLowerCase();
        return keyword.includes(searchText);
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

  const isConfirmLoading = deletingKeyword || deletingRanking || clearingRankings;

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
    if (isConfirmLoading) return;

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

  const handleChange = (e) => {
    dispatch(clearKeywordMessage());
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleAddKeyword = async (e) => {
    e.preventDefault();

    if (!selectedProjectId || !formData.keyword.trim()) return;

    const resultAction = await dispatch(
      addKeywordToProject({
        projectId: selectedProjectId,
        payload: {
          keyword: formData.keyword.trim(),
          location: formData.location,
          device: formData.device,
        },
      })
    );

    if (addKeywordToProject.fulfilled.match(resultAction)) {
      setFormData((prev) => ({
        ...prev,
        keyword: '',
      }));
    }
  };

  const handleRunRankCheck = async () => {
    if (!selectedProjectId) return;
    dispatch(clearKeywordMessage());
    await dispatch(runRankCheck(selectedProjectId));
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

  if (!selectedProjectId) {
    return (
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
        <p className="text-sm text-slate-500">
          Select a project first to manage keywords and rankings.
        </p>
      </section>
    );
  }

  return (
    <>
      <div className="space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-white shadow-soft">
          <div className="border-b border-slate-200 p-5">
            <h3 className="text-lg font-semibold text-slate-900">Add keyword</h3>
            <p className="mt-1 text-sm text-slate-500">
              Add keywords for the selected project before running rank checks.
            </p>
          </div>

          <form
            onSubmit={handleAddKeyword}
            className="grid gap-4 p-5 lg:grid-cols-[2fr_1fr_1fr_auto]"
          >
            <input
              type="text"
              name="keyword"
              value={formData.keyword}
              onChange={handleChange}
              placeholder="Enter keyword"
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            />

            <input
              type="text"
              name="location"
              value={formData.location}
              onChange={handleChange}
              placeholder="Location"
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            />

            <select
              name="device"
              value={formData.device}
              onChange={handleChange}
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            >
              <option value="desktop">Desktop</option>
              <option value="mobile">Mobile</option>
            </select>

            <button
              type="submit"
              disabled={adding}
              className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
            >
              {adding ? 'Adding...' : 'Add Keyword'}
            </button>
          </form>

          {actionMessage && (
            <div className="border-t border-slate-200 rounded-b-3xl bg-emerald-50 px-5 py-3 text-sm text-emerald-700">
              {actionMessage}
            </div>
          )}

          {error && (
            <div className="border-t border-slate-200 bg-rose-50 px-5 py-3 text-sm text-rose-600">
              {error}
            </div>
          )}
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white shadow-soft">
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

          {loadingKeywords ? (
            <div className="p-5 text-sm text-slate-500">Loading keywords...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left">
                <thead className="bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                  <tr>
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
                        {row.createdAt ? new Date(row.createdAt).toLocaleString() : '-'}
                      </td>
                      <td className="px-5 py-4">
                        <button
                          onClick={() => handleDeleteKeyword(row)}
                          disabled={deletingKeyword}
                          className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-medium text-rose-600 disabled:opacity-60"
                        >
                          {deletingKeyword ? 'Deleting...' : 'Delete'}
                        </button>
                      </td>
                    </tr>
                  ))}

                  {filteredKeywords.length === 0 && (
                    <tr>
                      <td colSpan="5" className="px-5 py-10 text-center text-sm text-slate-500">
                        No keywords added yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white shadow-soft">
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

              <button
                onClick={handleClearRankings}
                disabled={clearingRankings || filteredRankings.length === 0}
                className="rounded-xl bg-rose-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
              >
                {clearingRankings ? 'Clearing...' : 'Clear Rankings'}
              </button>

              <button
                onClick={handleRunRankCheck}
                disabled={running}
                className="rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
              >
                {running ? 'Running...' : 'Run Rank Check'}
              </button>
            </div>
          </div>

          {loadingRankings ? (
            <div className="p-5 text-sm text-slate-500">
              Running rank check and waiting for results...
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left">
                <thead className="bg-slate-50 text-xs uppercase tracking-[0.2em] text-slate-400">
                  <tr>
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
                        {row.checkedAt ? new Date(row.checkedAt).toLocaleString() : '-'}
                      </td>
                      <td className="px-5 py-4">
                        <button
                          onClick={() => handleDeleteRanking(row)}
                          disabled={deletingRanking}
                          className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-medium text-rose-600 disabled:opacity-60"
                        >
                          {deletingRanking ? 'Deleting...' : 'Delete'}
                        </button>
                      </td>
                    </tr>
                  ))}

                  {filteredRankings.length === 0 && (
                    <tr>
                      <td colSpan="7" className="px-5 py-10 text-center text-sm text-slate-500">
                        No rankings available yet. Add a keyword and run rank check.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
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
        loading={isConfirmLoading}
        onConfirm={confirmState.onConfirm}
        onClose={closeConfirmModal}
      />
    </>
  );
}

export default KeywordTable;