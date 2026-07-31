import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import ProjectCard from '../components/ProjectCard';
import ConfirmModal from '../components/ConfirmModal';
import {
  createProject,
  deleteProjectById,
  updateProject,
} from '../features/projects/projectsSlice';
import { fetchCurrentPricing } from "../features/pricing/pricingSlice";
import Alert from '../components/ui/Alert';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPencil, faTrash } from '@fortawesome/free-solid-svg-icons';

function ProjectsPage() {
  const dispatch = useDispatch();

  const { list: projects, loading, creating, updating, deleting, error, actionMessage } = useSelector((state) => state.projects);
  const pricingCurrent = useSelector((state) => state.pricing.current);
  const projectLimitReached = (pricingCurrent?.usage?.projects || 0) >= (pricingCurrent?.limits?.projects || 0);

  const [showForm, setShowForm] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState(null);
  const [projectToEdit, setProjectToEdit] = useState(null);

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

  const handleEditProject = (project) => {
    setProjectToEdit(project);
    setForm({
      name: project.name,
      domain: project.domain,
      device: 'desktop',
      location: 'India',
    });
    setShowForm(true);
  };

  const handleUpdateProject = async (e) => {
    e.preventDefault();

    const resultAction = await dispatch(
      updateProject({
        projectId: projectToEdit.id,
        payload: {
          name: form.name,
          domain: form.domain,
        },
      })
    );

    if (updateProject.fulfilled.match(resultAction)) {
      setProjectToEdit(null);
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

          <Button
            onClick={() => setShowForm((prev) => !prev)}
            disabled={projectLimitReached}
          >
            {showForm ? 'Close form' : 'Add project'}
          </Button>
        </div>

        {projectLimitReached ? (
          <Alert
            variant="warning"
            message="You have reached your current project limit. Upgrade your plan to add more projects."
          />
        ) : null}

        {showForm && (
          <form
            onSubmit={projectToEdit ? handleUpdateProject : handleSubmit}
            className="grid gap-4 rounded-xs border border-slate-200 bg-white p-5 md:grid-cols-2"
          >
            <Input
              label="Project name"
              name="name"
              placeholder="Project name"
              value={form.name}
              onChange={handleChange}
              required
            />

            <Input
              label="Domain"
              name="domain"
              placeholder="Domain (example.com)"
              value={form.domain}
              onChange={handleChange}
              required
            />

            <Input.Select
              label="Device"
              name="device"
              value={form.device}
              onChange={handleChange}
            >
              <option value="desktop">Desktop</option>
              <option value="mobile">Mobile</option>
            </Input.Select>

            <Input
              label="Location"
              name="location"
              placeholder="Location"
              value={form.location}
              onChange={handleChange}
            />

            <div className="md:col-span-2 flex gap-3">
              <Button
                type="submit"
                disabled={creating || updating || (projectLimitReached && !projectToEdit)}
                loading={creating || updating}
              >
                {creating ? 'Creating...' : updating ? 'Updating...' : projectToEdit ? 'Update project' : 'Create project'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowForm(false);
                  setProjectToEdit(null);
                  setForm({
                    name: '',
                    domain: '',
                    device: 'desktop',
                    location: 'India',
                  });
                }}
              >
                Cancel
              </Button>
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
                <ProjectCard project={project}/>
                <div className="inline-flex gap-2">
                  <Button
                    onClick={() => handleDeleteProject(project)}
                    disabled={deleting}
                    variant="danger"
                    fullWidth
                  >
                    <FontAwesomeIcon icon={faTrash} />
                  </Button>
                  <Button
                    onClick={() => handleEditProject(project)}>
                    <FontAwesomeIcon icon={faPencil} />
                  </Button>
                </div>
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