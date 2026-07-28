function Skeleton({ className = '' }) {
  return (
    <div className={`animate-pulse rounded-full bg-slate-200 ${className}`} />
  );
}

function SkeletonText({ lines = 3, className = '' }) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          className={`h-4 w-full ${index === lines - 1 ? 'w-4/5' : ''}`}
        />
      ))}
    </div>
  );
}

function SkeletonCard() {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-3">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-4 w-40" />
        </div>
        <Skeleton className="h-12 w-12 shrink-0 rounded-2xl" />
      </div>
    </article>
  );
}

function SkeletonTable({ rows = 5, columns = 6 }) {
  return (
    <div className="w-full">
      <div className="flex gap-4 border-b border-slate-200 bg-slate-50 px-5 py-4">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={index} className={`h-4 ${index === 0 ? 'w-10' : 'flex-1'}`} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="flex gap-4 border-b border-slate-100 px-5 py-4 last:border-b-0"
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={colIndex}
              className={`h-4 ${colIndex === 0 ? 'w-10' : 'flex-1'}`}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function SkeletonButton() {
  return <Skeleton className="h-12 w-full rounded-xl" />;
}

export { Skeleton, SkeletonText, SkeletonCard, SkeletonTable, SkeletonButton };
