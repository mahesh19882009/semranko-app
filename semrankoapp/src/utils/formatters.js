const DEFAULT_LOCALE = 'en-IN';

function numberOrNull(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export function formatNumber(value, options = {}) {
  const numeric = numberOrNull(value);
  return numeric === null ? '—' : new Intl.NumberFormat(DEFAULT_LOCALE, options).format(numeric);
}

export function formatInr(value, options = {}) {
  const numeric = numberOrNull(value);
  if (numeric === null) return '—';
  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0, ...options,
  }).format(numeric);
}

export function formatCredits(value, options = {}) {
  const formatted = formatNumber(value, { maximumFractionDigits: 2, ...options });
  return formatted === '—' ? formatted : `${formatted} credits`;
}

export function formatPercent(value, options = {}) {
  const numeric = numberOrNull(value);
  return numeric === null ? '—' : new Intl.NumberFormat(DEFAULT_LOCALE, {
    style: 'percent', maximumFractionDigits: 1, ...options,
  }).format(numeric > 1 ? numeric / 100 : numeric);
}

export function formatRankingPosition(value) {
  const numeric = numberOrNull(value);
  return numeric === null || numeric <= 0 ? '—' : `#${Math.round(numeric)}`;
}

export function formatResetDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat(DEFAULT_LOCALE, { day: 'numeric', month: 'short', year: 'numeric' }).format(date);
}
