import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import ProjectCard from '../components/ProjectCard';
import ConfirmModal from '../components/ConfirmModal';
import {
  createProject,
  deleteProjectById,
} from '../features/projects/projectsSlice';
import { fetchCurrentPricing } from "../features/pricing/pricingSlice";
import Alert from '../components/ui/Alert';

function ProjectsPage() {
  const dispatch = useDispatch();

  const { list: projects, loading, creating, deleting, error, actionMessage } = useSelector((state) => state.projects);
  const pricingCurrent = useSelector((state) => state.pricing.current);
  const projectLimitReached = (pricingCurrent?.usage?.projects || 0) >= (pricingCurrent?.limits?.projects || 0);

  const [showForm, setShowForm] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState(null);

  const [form, setForm] = useState({
    name: '',
    domain: '',
    device: 'desktop',
    location: 'India',
  });

  const handleChange = (e) => {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const resultAction = await dispatch(createProject(form));

    if (createProject.fulfilled.match(resultAction)) {
      await dispatch(fetchCurrentPricing());
      setForm({
        name: '',
        domain: '',
        device: 'desktop',
        location: 'India',
      });
      setShowForm(false);
    }
  };

  const handleDeleteProject = (project) => {
    setProjectToDelete(project);
  };

  const handleConfirmDelete = async () => {
    if (!projectToDelete) return;

    const resultAction = await dispatch(deleteProjectById(projectToDelete.id));

    if (deleteProjectById.fulfilled.match(resultAction)) {
      await dispatch(fetchCurrentPricing());
      setProjectToDelete(null);
    }
  };

  const handleCloseModal = () => {
    if (deleting) return;
    setProjectToDelete(null);
  };

  return (
    <>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Projects</h2>
            <p className="mt-1 text-sm text-slate-500">
              Manage tracked websites, devices, and locations.
            </p>
          </div>

          <button
            onClick={() => setShowForm((prev) => !prev)}
            disabled={projectLimitReached}
            className="rounded-2xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {showForm ? 'Close form' : 'Add project'}
          </button>
        </div>

        {projectLimitReached ? (
          <Alert
            variant="warning"
            message="You have reached your current project limit. Upgrade your plan to add more projects."
          />
        ) : null}

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="grid gap-4 rounded-3xl border border-slate-200 bg-white p-5 md:grid-cols-2"
          >
            <input
              type="text"
              name="name"
              placeholder="Project name"
              value={form.name}
              onChange={handleChange}
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
              required
            />

            <input
              type="text"
              name="domain"
              placeholder="Domain (example.com)"
              value={form.domain}
              onChange={handleChange}
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
              required
            />

            <select
              name="device"
              value={form.device}
              onChange={handleChange}
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            >
              <option value="desktop">Desktop</option>
              <option value="mobile">Mobile</option>
            </select>

            <input
              type="text"
              name="location"
              placeholder="Location"
              value={form.location}
              onChange={handleChange}
              className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none"
            />

            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={creating || projectLimitReached}
                className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
              >
                {creating ? 'Creating...' : 'Create project'}
              </button>
            </div>
          </form>
        )}

        {error ? (
          <Alert
            variant="error"
            message={error}
          />
        ) : null}

        {actionMessage ? (
          <Alert
            variant="success"
            message={actionMessage}
          />
        ) : null}

        {loading ? (
          <Alert
            variant="plain"
            message="Loading projects..."
          />
        ) : projects.length === 0 ? (
          <Alert
            variant="plain"
            message="No projects found. Create your first project."
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {projects.map((project) => (
              <div key={project.id} className="space-y-3">
                <ProjectCard project={project} />
                <button
                  onClick={() => handleDeleteProject(project)}
                  disabled={deleting}
                  className="w-full rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-60"
                >
                  Delete project
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <ConfirmModal
        open={Boolean(projectToDelete)}
        title="Delete project"
        message={
          projectToDelete
            ? `Delete "${projectToDelete.name}"? This will also delete all keywords and ranking results linked to this project.`
            : ''
        }
        confirmText="Delete project"
        cancelText="Keep project"
        tone="danger"
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onClose={handleCloseModal}
      />
    </>
  );
}

export default ProjectsPage;