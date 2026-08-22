export const normalizeKeywordTargetText = (value) =>
  String(value || '').trim().toLowerCase();

export const normalizeKeywordTargetDevice = (value) => {
  const device = String(value || 'desktop').trim().toLowerCase();
  return device === 'mobile' ? 'mobile' : 'desktop';
};

export const effectiveKeywordLocationCode = (target, fallbackLocationCode = 2840) => {
  const value = target?.locationCode ?? target?.location_code ?? fallbackLocationCode;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : Number(fallbackLocationCode) || 2840;
};

export function keywordTargetKey(target, fallbackLocationCode = 2840) {
  const serverId = target?.id ?? target?.keyword_id ?? target?.keywordId;
  if (
    serverId !== undefined &&
    serverId !== null &&
    String(serverId).trim() &&
    !String(serverId).startsWith('target:') &&
    !String(serverId).startsWith('processing:')
  ) {
    if (String(serverId).startsWith('id:')) return String(serverId);
    return `id:${String(serverId)}`;
  }

  return [
    'target',
    normalizeKeywordTargetText(target?.keyword),
    effectiveKeywordLocationCode(target, fallbackLocationCode),
    normalizeKeywordTargetDevice(target?.device),
  ].join(':');
}

export const targetKeywordValue = (target) =>
  normalizeKeywordTargetText(typeof target === 'string' ? target : target?.keyword);
