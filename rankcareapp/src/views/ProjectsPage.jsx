'use client'
import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import ProjectCard from '../components/ProjectCard';
import ConfirmModal from '../components/ConfirmModal';
import CountrySelector from '../components/CountrySelector';
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
import { COUNTRY_LOCATION_CODES } from '../data/locations';

function ProjectsPage() {
  const dispatch = useDispatch();

  const { list: projects, loading, creating, updating, deleting, error, actionMessage } = useSelector((state) => state.projects);
  const pricingCurrent = useSelector((state) => state.pricing.current);
  const projectCount = pricingCurrent?.usage?.projects || 0;

  const [showForm, setShowForm] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState(null);
  const [projectToEdit, setProjectToEdit] = useState(null);

  const [form, setForm] = useState({
    name: '',
    domain: '',
    device: 'desktop',
    country: 'India',
    countryCode: 2356,
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleCountryChange = (country) => {
    setForm((prev) => ({
      ...prev,
      country,
      countryCode: COUNTRY_LOCATION_CODES[country] || 2840,
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
        country: 'India',
        countryCode: 2356,
      });
      setShowForm(false);
    }
  };

  const handleEditProject = (project) => {
    setProjectToEdit(project);
    let country = 'India';
    let countryCode = 2840;
    if (project.location) {
      try {
        const parsed = JSON.parse(project.location);
        if (parsed && typeof parsed === 'object') {
          country = parsed.country || 'India';
          countryCode = parsed.locationCode || parsed.countryCode || getCountryCode(country) || project.locationCode || 2840;
        }
      } catch {
        country = project.location || 'India';
        countryCode = project.locationCode || getCountryCode(country);
      }
    } else if (project.locationCode) {
      countryCode = project.locationCode;
    }
    setForm({
      name: project.name,
      domain: project.domain,
      device: project.device || 'desktop',
      country,
      countryCode,
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
          location: form.country,
          locationCode: form.countryCode,
          device: form.device,
        },
      })
    );

    if (updateProject.fulfilled.match(resultAction)) {
      setProjectToEdit(null);
      setForm({
        name: '',
        domain: '',
        device: 'desktop',
        country: 'India',
        countryCode: 2356,
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
          >
            {showForm ? 'Close form' : 'Add project'}
          </Button>
        </div>

        {projectCount > 0 ? (
          <Alert
            variant="info"
            message="Project creation is free. Create as many projects as you need within your plan's limits."
          />
        ) : (
          <Alert
            variant="success"
            message="Your first project is free! Create it now."
          />
        )}

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

            <div className="md:col-span-4 block gap-3">
              <label className="text-sm font-bold !mb-5 text-slate-700 !mb-5">Location</label>
              <CountrySelector value={form.country} onChange={handleCountryChange} disabled={creating || updating} />
            </div>

            <div className="md:col-span-2 flex gap-3">
              <Button
                type="submit"
                disabled={creating || updating}
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
                    country: 'India',
                    countryCode: 2356,
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
                <ProjectCard project={project} />
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