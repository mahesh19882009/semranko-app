'use client'
import { useDispatch, useSelector } from 'react-redux';
import { setSelectedProjectId } from '../features/projects/projectsSlice';
import { formatDate } from '../utils/date';
import Card from './ui/Card';
import Badge from './ui/Badge';

function ProjectCard({ project }) {
  const dispatch = useDispatch();
  const selectedId = useSelector((state) => state.projects.selectedProjectId);
  const isSelected = selectedId === project.id;

  const handleCardClick = (e) => {
    if (e.target.closest('button')) return;
    dispatch(setSelectedProjectId(project.id));
  };

  return (
    <Card
      as="article"
      onClick={handleCardClick}
      className="cursor-pointer transition"
      padding="p-5"
      {...(isSelected
        ? { border: 'border-brand-200', className: 'bg-brand-50' }
        : { className: 'hover:border-slate-300' })}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{project.name}</h3>
          <p className="mt-1 text-sm text-slate-500">{project.domain}</p>
        </div>

        <div className="flex items-center gap-2">
          <Badge tone="secondary" size="sm" rounded="rounded-full">
            Active
          </Badge>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
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
    </Card>
  );
}

export default ProjectCard;
