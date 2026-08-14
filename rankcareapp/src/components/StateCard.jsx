'use client'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import Card from './ui/Card';

function StatCard({ title, value, hint, icon, tone = 'brand' }) {
  const toneClasses = {
    brand: 'bg-brand-50 text-brand-700',
    green: 'bg-success-light text-success-dark',
    amber: 'bg-warning-light text-warning-dark',
    red: 'bg-danger-light text-danger-dark',
    success: 'bg-success-light text-success-dark',
    warning: 'bg-warning-light text-warning-dark',
    danger: 'bg-danger-light text-danger-dark',
  };

  return (
    <Card padding="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <h3 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">{value}</h3>
          <p className="mt-2 text-sm text-slate-500">{hint}</p>
        </div>

        <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${toneClasses[tone]}`}>
          <FontAwesomeIcon icon={icon} aria-hidden="true" />
        </div>
      </div>
    </Card>
  );
}

export default StatCard;
