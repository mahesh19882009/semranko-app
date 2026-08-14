'use client'
import { AlertCircle, Inbox, LoaderCircle } from 'lucide-react';
import Button from './Button';

function StateView({ icon: Icon, title, description, action, tone = 'neutral', className = '' }) {
  const toneClasses = {
    neutral: 'bg-surface-muted text-text-secondary',
    error: 'bg-danger-light text-danger-dark',
    loading: 'bg-brand-50 text-brand-700',
  };
  return (
    <div className={`rounded-xl border border-border bg-surface px-6 py-8 text-center ${className}`.trim()}>
      <div className={`mx-auto flex h-10 w-10 items-center justify-center rounded-full ${toneClasses[tone] || toneClasses.neutral}`}>
        <Icon className={`h-5 w-5 ${tone === 'loading' ? 'animate-spin' : ''}`} aria-hidden="true" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-text-primary">{title}</h3>
      {description ? <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-text-muted">{description}</p> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function EmptyState({ title = 'Nothing here yet', description, action, className }) {
  return <StateView icon={Inbox} title={title} description={description} action={action} className={className} />;
}

export function ErrorState({ title = 'Something went wrong', description = 'Please try again.', onRetry, retryLabel = 'Try again', action, className }) {
  return <StateView icon={AlertCircle} title={title} description={description} tone="error" action={action || (onRetry ? <Button type="button" variant="outline" onClick={onRetry}>{retryLabel}</Button> : null)} className={className} />;
}

export function LoadingState({ title = 'Loading', description, className }) {
  return <StateView icon={LoaderCircle} title={title} description={description} tone="loading" className={className} />;
}
