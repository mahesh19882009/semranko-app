const formatAmount = (value) => {
  const rounded = Math.round(Math.abs(value) * 100) / 100;
  return String(rounded);
};

export function getComparisonIndicator(
  change,
  { scale = 1, suffix = '', semantic = true } = {}
) {
  const hasHistoricalValues =
    change?.previous !== null &&
    change?.previous !== undefined &&
    change?.current !== null &&
    change?.current !== undefined;
  const difference = Number(change?.difference);

  if (
    !hasHistoricalValues ||
    !Number.isFinite(difference) ||
    difference === 0 ||
    change.direction === 'same'
  ) {
    return null;
  }

  const direction = change.direction || 'same';
  const symbol = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→';
  const scaledDifference = difference * scale;
  const tone = !semantic || direction === 'same'
    ? 'neutral'
    : change.isPositive
      ? 'positive'
      : 'negative';

  return {
    text: `${symbol}${formatAmount(scaledDifference)}${suffix}`,
    tone,
  };
}
