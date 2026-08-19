'use client';

export default function Shimmer({
  width = 'w-12',
  height = 'h-4',
  rounded = 'rounded',
  className = '',
}) {
  return (
    <span
      className={`inline-block ${width} ${height} ${rounded} animate-pulse bg-slate-200 ${className}`}
      aria-label="Loading"
    />
  );
}