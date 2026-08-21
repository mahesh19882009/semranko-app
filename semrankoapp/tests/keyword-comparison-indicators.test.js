import test from 'node:test';
import assert from 'node:assert/strict';

import { getComparisonIndicator } from '../src/features/keywords/comparisonState.js';

test('position and visibility comparisons retain semantic improvement direction', () => {
  assert.deepEqual(
    getComparisonIndicator(
      { previous: 9, current: 7, difference: -2, direction: 'up', isPositive: true },
      { scale: 1, semantic: true }
    ),
    { text: '↑2', tone: 'positive' }
  );

  assert.deepEqual(
    getComparisonIndicator(
      { previous: 0.6, current: 0.8, difference: 0.2, direction: 'up', isPositive: true },
      { scale: 100, suffix: '%', semantic: true }
    ),
    { text: '↑20%', tone: 'positive' }
  );
});

test('KD uses inverse semantic colors while CPC and competition remain neutral', () => {
  assert.deepEqual(
    getComparisonIndicator(
      { previous: 31, current: 34, difference: 3, direction: 'up', isPositive: false }
    ),
    { text: '↑3', tone: 'negative' }
  );

  assert.deepEqual(
    getComparisonIndicator(
      { previous: 34, current: 31, difference: -3, direction: 'down', isPositive: true }
    ),
    { text: '↓3', tone: 'positive' }
  );

  for (const change of [
    { previous: 0, current: 2.5, difference: 2.5, direction: 'up', isPositive: true },
    { previous: 0, current: 0.65, difference: 0.65, direction: 'up', isPositive: true },
  ]) {
    assert.deepEqual(
      getComparisonIndicator(change, { semantic: false }),
      { text: `↑${change.difference}`, tone: 'neutral' }
    );
  }
});

test('missing or unchanged history never renders a zero comparison', () => {
  assert.equal(getComparisonIndicator(null), null);
  assert.equal(
    getComparisonIndicator(
      { previous: null, current: 7, difference: 7, direction: 'up', isPositive: true }
    ),
    null
  );
  assert.equal(
    getComparisonIndicator(
      { previous: 7, current: 7, difference: 0, direction: 'same', isPositive: false }
    ),
    null
  );
});

test('position, volume, backlinks, and referring domains use positive growth semantics', () => {
  for (const change of [
    { previous: 9, current: 7, difference: -2, direction: 'up', isPositive: true },
    { previous: 720, current: 880, difference: 160, direction: 'up', isPositive: true },
    { previous: 10, current: 12, difference: 2, direction: 'up', isPositive: true },
  ]) {
    assert.equal(getComparisonIndicator(change).tone, 'positive');
  }

  assert.deepEqual(
    getComparisonIndicator(
      { previous: 5, current: 7, difference: 2, direction: 'down', isPositive: false }
    ),
    { text: '↓2', tone: 'negative' }
  );
});

test('keyword table consumes additive comparison fields inside existing columns', async () => {
  const { readFile } = await import('node:fs/promises');
  const page = await readFile(
    new URL('../src/views/KeywordsPage.jsx', import.meta.url),
    'utf8'
  );

  assert.match(page, /rowData\.positionChange/);
  assert.match(page, /rowData\.visibilityChange/);
  for (const field of ['volume', 'kd', 'cpc', 'competition', 'backlinks', 'referring_domains']) {
    assert.match(page, new RegExp(`rowData\\.changes\\?\\.${field}`));
  }
  assert.doesNotMatch(page, /localPackPositionChange/);
  assert.doesNotMatch(page, /changes\?\.intent/);
});
