import { useDispatch, useSelector } from 'react-redux';
import { setSelectedProjectId } from '../features/projects/projectsSlice';
import { formatDate } from '../utils/date';

function ProjectCard({ project, onEdit }) {
  const dispatch = useDispatch();
  const selectedId = useSelector((state) => state.projects.selectedProjectId);
  const isSelected = selectedId === project.id;

  const handleCardClick = (e) => {
    // Don't select project if clicking the edit button
    if (e.target.closest('button')) return;
    dispatch(setSelectedProjectId(project.id));
  };

  return (
    <article
      onClick={handleCardClick}
      className={`cursor-pointer rounded-3xl border p-5 shadow-soft transition ${
        isSelected
          ? 'border-brand-200 bg-brand-50'
          : 'border-slate-200 bg-white hover:border-slate-300'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{project.name}</h3>
          <p className="mt-1 text-sm text-slate-500">{project.domain}</p>
        </div>

        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
            Active
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit(project);
            }}
            className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-200"
          >
            Edit
          </button>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
        {/* <div>
          <p className="text-slate-400">Project ID</p>
          <p className="mt-1 break-all font-semibold text-slate-900">{project.id}</p>
        </div>

        <div>
          <p className="text-slate-400">Owner</p>
          <p className="mt-1 break-all font-semibold text-slate-900">{project.userId}</p>
        </div> */}

        <div>
          <p className="text-slate-400">Created</p>
          <p className="mt-1 font-semibold text-slate-900">
            {formatDate(project.createdAt)}
          </p>
        </div>

        <div>
          <p className="text-slate-400">Updated</p>
          <p className="mt-1 font-semibold text-slate-900">
            {formatDate(project.updatedAt)}
          </p>
        </div>
      </div>
    </article>
  );
}

export default ProjectCard;