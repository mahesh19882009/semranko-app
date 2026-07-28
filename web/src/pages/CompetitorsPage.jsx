import { useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import ConfirmModal from '../components/ConfirmModal';
import { formatDate } from '../utils/date';
import {
  addCompetitorToProject,
  clearCompetitorMessage,
  deleteCompetitorById,
  fetchCompetitorsByProject,
  resetCompetitorsForProjectChange,
  updateCompetitorById,
} from '../features/competitors/competitorsSlice';
import { Check, Globe, Pencil, Trash2, X } from 'lucide-react';
import Alert from '../components/ui/Alert';

const normalizeDomain = (value = '') =>
  value
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/+$/, '');

const getDomainUrl = (domain = '') => {
  const cleanDomain = normalizeDomain(domain);
  return cleanDomain ? `https://${cleanDomain}` : '#';
};

export default function Competitors() {
  const dispatch = useDispatch();

  const { list: projects, selectedProjectId, loading: projectsLoading } = useSelector((state) => state.projects);
  const pricingCurrent = useSelector((state) => state.pricing.current);

  const { list: competitors, loading, adding, updating, deleting, error, actionMessage } = useSelector((state) => state.competitors);

  const { keywords } = useSelector((state) => state.keywords);

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const selectedProject = useMemo(() => {
    if (!selectedProjectId) return null;

    return (
      projects.find(
        (project) => String(project.id) === String(selectedProjectId)
      ) || null
    );
  }, [projects, selectedProjectId]);

  const projectKeywords = useMemo(() => {
    return keywords.filter(
      (item) => String(item.projectId) === String(selectedProjectId)
    );
  }, [keywords, selectedProjectId]);

  const competitorLimit = pricingCurrent?.limits?.competitorsPerProject || 0;
  const competitorCount = competitors.length;
  const competitorLimitReached = competitorLimit > 0 && competitorCount >= competitorLimit;


  const [form, setForm] = useState({
    name: '',
    domain: '',
  });

  const [localError, setLocalError] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editingForm, setEditingForm] = useState({
    name: '',
    domain: '',
  });

  useEffect(() => {
    if (!selectedProjectId) {
      dispatch(resetCompetitorsForProjectChange(null));
      return;
    }

    if (projectsLoading) return;
    if (!selectedProject) return;

    dispatch(resetCompetitorsForProjectChange(selectedProjectId));
    dispatch(fetchCompetitorsByProject(selectedProjectId));
  }, [dispatch, selectedProjectId, selectedProject, projectsLoading]);

  useEffect(() => {
    return () => {
      dispatch(clearCompetitorMessage());
    };
  }, [dispatch]);

  useEffect(() => {
    setEditingId(null);
    setEditingForm({
      name: '',
      domain: '',
    });
    setLocalError('');
    setDeleteTarget(null);
    setDeleteModalOpen(false);
  }, [selectedProjectId]);

  const validateDuplicateDomain = (domain, ignoreId = null) => {
    const cleanDomain = normalizeDomain(domain);

    return competitors.some(
      (item) =>
        String(item.id) !== String(ignoreId) &&
        normalizeDomain(item.domain) === cleanDomain
    );
  };

  const isBusy = adding || updating || deleting;

  const handleAddCompetitor = (e) => {
    e.preventDefault();

    if (!selectedProjectId || isBusy) return;

    if (competitorLimitReached) {
      setLocalError('You have reached the competitor limit for your current plan.');
      return;
    }

    const cleanName = form.name.trim();
    const cleanDomain = normalizeDomain(form.domain);

    setLocalError('');

    if (!cleanName || !cleanDomain) {
      setLocalError('Competitor name and domain are required.');
      return;
    }

    if (validateDuplicateDomain(cleanDomain)) {
      setLocalError('This competitor domain already exists for the selected project.');
      return;
    }

    dispatch(
      addCompetitorToProject({
        projectId: selectedProjectId,
        payload: {
          name: cleanName,
          domain: cleanDomain,
        },
      })
    );

    setForm({
      name: '',
      domain: '',
    });
  };

  const startEdit = (item) => {
    if (isBusy) return;

    setEditingId(item.id);
    setEditingForm({
      name: item.name || '',
      domain: item.domain || '',
    });
    setLocalError('');
  };

  const cancelEdit = () => {
    if (updating) return;

    setEditingId(null);
    setEditingForm({
      name: '',
      domain: '',
    });
    setLocalError('');
  };

  const handleSaveEdit = () => {
    if (!selectedProjectId || !editingId || isBusy) return;

    const cleanName = editingForm.name.trim();
    const cleanDomain = normalizeDomain(editingForm.domain);

    setLocalError('');

    if (!cleanName || !cleanDomain) {
      setLocalError('Competitor name and domain are required.');
      return;
    }

    if (validateDuplicateDomain(cleanDomain, editingId)) {
      setLocalError('Another competitor with this domain already exists.');
      return;
    }

    dispatch(
      updateCompetitorById({
        competitorId: editingId,
        projectId: selectedProjectId,
        payload: {
          name: cleanName,
          domain: cleanDomain,
        },
      })
    );

    cancelEdit();
  };

  const handleDelete = (competitor) => {
    if (isBusy) return;

    setDeleteTarget(competitor);
    setDeleteModalOpen(true);
  };

  const handleConfirmDelete = () => {
    if (!selectedProjectId || !deleteTarget?.id) return;

    dispatch(
      deleteCompetitorById({
        competitorId: deleteTarget.id,
        projectId: selectedProjectId,
      })
    );

    setDeleteModalOpen(false);
    setDeleteTarget(null);
  };

  const handleCloseDeleteModal = () => {
    if (deleting) return;

    setDeleteModalOpen(false);
    setDeleteTarget(null);
  };

  if (!selectedProjectId) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h1 className="text-xl font-semibold text-slate-900">No project selected</h1>
        <p className="mt-2 text-sm text-slate-500">
          Please select a project first to manage competitors.
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
    <>
      <div className="space-y-6">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-500">Competitor module</p>
              <h1 className="mt-1 text-2xl font-semibold text-slate-900">
                {selectedProject.name}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
                <span>Project domain:</span>
                <a
                  href={getDomainUrl(selectedProject.domain)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-slate-700 underline underline-offset-2 hover:text-slate-900"
                >
                  {selectedProject.domain}
                </a>
              </div>
              <p className="mt-2 text-sm text-slate-500">
                Add competitor domains for this project and prepare comparison data.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <div className="rounded-xl bg-slate-100 px-4 py-3 text-sm">
                <span className="font-semibold text-slate-900">{competitors.length}</span>
                <span className="ml-2 text-slate-500">Competitors</span>
              </div>
              <div className="rounded-xl bg-slate-100 px-4 py-3 text-sm">
                <span className="font-semibold text-slate-900">{projectKeywords.length}</span>
                <span className="ml-2 text-slate-500">Keywords</span>
              </div>
            </div>
          </div>
        </section>

        { competitorLimitReached ? (
          <Alert
            variant="warning"
            message="You have reached the competitor limit for this project. Upgrade your plan to add more competitors."
          />
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Add competitor</h2>
              <p className="mt-1 text-sm text-slate-500">
                Use a unique domain for each competitor in this project.
              </p>
            </div>

            <p className="mt-2 text-sm text-slate-500">
              Usage: {competitorCount} / {competitorLimit} competitors for this project.
            </p>

            {(form.name || form.domain) && !adding ? (
              <button
                type="button"
                onClick={() => {
                  setForm({ name: '', domain: '' });
                  setLocalError('');
                }}
                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Reset
              </button>
            ) : null}
          </div>

          <form onSubmit={handleAddCompetitor} className="mt-5 grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label
                htmlFor="competitor-name"
                className="text-sm font-medium text-slate-700"
              >
                Competitor name
              </label>
              <input
                id="competitor-name"
                type="text"
                placeholder="Example: Amazon"
                value={form.name}
                onChange={(e) => {
                  setForm((prev) => ({ ...prev, name: e.target.value }));
                  if (localError) setLocalError('');
                }}
                disabled={isBusy || competitorLimitReached}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-900 disabled:cursor-not-allowed disabled:bg-slate-50"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="competitor-domain"
                className="text-sm font-medium text-slate-700"
              >
                Competitor domain
              </label>
              <input
                id="competitor-domain"
                type="text"
                placeholder="example.com"
                value={form.domain}
                onChange={(e) => {
                  setForm((prev) => ({ ...prev, domain: e.target.value }));
                  if (localError) setLocalError('');
                }}
                disabled={isBusy || competitorLimitReached}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-900 disabled:cursor-not-allowed disabled:bg-slate-50"
              />
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                disabled={isBusy || competitorLimitReached}
                className="w-full rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {adding ? 'Adding...' : competitorLimitReached ? 'Limit reached' : 'Add competitor'}
              </button>
            </div>
          </form>

          {localError ? (
            <p className="mt-3 text-sm font-medium text-rose-600">{localError}</p>
          ) : null}

          {error ? (
            <p className="mt-3 text-sm font-medium text-rose-600">{error}</p>
          ) : null}

          {actionMessage ? (
            <p className="mt-3 text-sm font-medium text-emerald-600">{actionMessage}</p>
          ) : null}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Competitor list</h2>
              <p className="mt-1 text-sm text-slate-500">
                Edit details, review domains, or remove competitors from this project.
              </p>
            </div>
            {loading ? <span className="text-sm text-slate-500">Loading...</span> : null}
          </div>

          {!loading && competitors.length === 0 ? (
            <div className="mt-6 rounded-xl border border-dashed border-slate-300 p-10 text-center">
              <p className="text-sm font-medium text-slate-700">
                No competitors added yet.
              </p>
              <p className="mt-2 text-sm text-slate-500">
                Add your first competitor domain above to start comparison tracking for this project.
              </p>
            </div>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-sm text-slate-500 sticky top-0 bg-slate-50">
                      <th className="py-3 pr-4 font-medium">Name</th>
                      <th className="py-3 pr-4 font-medium">Domain</th>
                      <th className="py-3 pr-4 font-medium">Updated</th>
                      <th className="py-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {competitors.map((item) => {
                      const isEditing = String(editingId) === String(item.id);

                      return (
                        <tr key={item.id} className="border-b border-slate-100 text-sm">
                          <td className="py-3 pr-4 align-top">
                            {isEditing ? (
                              <div className="space-y-2">
                                <label
                                  htmlFor={`edit-name-${item.id}`}
                                  className="sr-only"
                                >
                                  Edit competitor name
                                </label>
                                <input
                                  id={`edit-name-${item.id}`}
                                  type="text"
                                  value={editingForm.name}
                                  onChange={(e) =>
                                    setEditingForm((prev) => ({
                                      ...prev,
                                      name: e.target.value,
                                    }))
                                  }
                                  disabled={updating}
                                  className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-slate-900 disabled:cursor-not-allowed disabled:bg-slate-50"
                                />
                              </div>
                            ) : (
                              <span className="font-medium text-slate-900">{item.name}</span>
                            )}
                          </td>

                          <td className="py-3 pr-4 align-top">
                            {isEditing ? (
                              <div className="space-y-2">
                                <label
                                  htmlFor={`edit-domain-${item.id}`}
                                  className="sr-only"
                                >
                                  Edit competitor domain
                                </label>
                                <input
                                  id={`edit-domain-${item.id}`}
                                  type="text"
                                  value={editingForm.domain}
                                  onChange={(e) =>
                                    setEditingForm((prev) => ({
                                      ...prev,
                                      domain: e.target.value,
                                    }))
                                  }
                                  disabled={updating}
                                  className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-slate-900 disabled:cursor-not-allowed disabled:bg-slate-50"
                                />
                              </div>
                            ) : (
                              <a
                                href={getDomainUrl(item.domain)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-slate-700 hover:text-slate-900"
                              >
                                <Globe size={16} className="text-slate-400" />
                                <span className="underline underline-offset-2">
                                  {item.domain}
                                </span>
                              </a>
                            )}
                          </td>

                          <td className="py-3 pr-4 align-top text-slate-500">
                            {formatDate(item.updatedAt)}
                          </td>

                          <td className="py-3 align-top">
                            <div className="flex flex-wrap items-center gap-2">
                              {isEditing ? (
                                <>
                                  <button
                                    type="button"
                                    onClick={handleSaveEdit}
                                    disabled={updating || deleting || adding}
                                    className="inline-flex items-center gap-1 rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    <Check size={15} />
                                    {updating ? 'Saving...' : 'Save'}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={cancelEdit}
                                    disabled={updating}
                                    className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    <X size={15} />
                                    Cancel
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => startEdit(item)}
                                    disabled={isBusy}
                                    className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    <Pencil size={15} />
                                    Edit
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleDelete(item)}
                                    disabled={isBusy}
                                    className="inline-flex items-center gap-1 rounded-lg border border-rose-300 px-3 py-2 text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    <Trash2 size={15} />
                                    Delete
                                  </button>
                                </>
                              )}
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
      </div>

      <ConfirmModal
        open={deleteModalOpen}
        title="Delete competitor"
        message={
          deleteTarget
            ? `Are you sure you want to delete "${deleteTarget.name}" from this project?`
            : 'Are you sure you want to delete this competitor?'
        }
        description={
          deleteTarget ? (
            <div>
              <p>
                <span className="font-medium text-slate-700">Name:</span> {deleteTarget.name}
              </p>
              <p>
                <span className="font-medium text-slate-700">Domain:</span> {deleteTarget.domain}
              </p>
              <p className="mt-2 text-rose-600">
                This action cannot be undone.
              </p>
            </div>
          ) : null
        }
        confirmText="Delete competitor"
        cancelText="Cancel"
        tone="danger"
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onClose={handleCloseDeleteModal}
      />
    </>
  );
}