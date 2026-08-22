import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { KEYWORD_LOCATION_CATALOG, resolveKeywordLocation } from '../src/data/locations.js';

const keywordsPage = fs.readFileSync(new URL('../src/views/KeywordsPage.jsx', import.meta.url), 'utf8');

test('static catalog resolves country, state, and city codes', () => {
  assert.deepEqual(resolveKeywordLocation({ country: 'India' }), {
    country: 'India', state: null, city: null, locationCode: 2356, label: 'India',
  });
  assert.deepEqual(resolveKeywordLocation({ country: 'India', state: 'Maharashtra' }), {
    country: 'India', state: 'Maharashtra', city: null, locationCode: 20359, label: 'Maharashtra, India',
  });
  assert.deepEqual(resolveKeywordLocation({ country: 'India', state: 'Maharashtra', city: 'Mumbai' }), {
    country: 'India', state: 'Maharashtra', city: 'Mumbai', locationCode: 9062115, label: 'Mumbai, Maharashtra, India',
  });
  assert.deepEqual(resolveKeywordLocation({ country: 'United States', state: 'California', city: 'Los Angeles' }).locationCode, 1013962);
  assert.deepEqual(resolveKeywordLocation({ country: 'Australia', state: 'New South Wales', city: 'Sydney' }).locationCode, 1000256);
  assert.equal(KEYWORD_LOCATION_CATALOG.find((entry) => entry.name === 'India').states.length, 4);
  assert.throws(() => resolveKeywordLocation({ country: 'India', state: 'Unknown' }), /not available/);
});

test('keyword table exports all or selected rows through the backend export path', () => {
  assert.match(keywordsPage, /exportProjectKeywordsApi/);
  assert.match(keywordsPage, /aria-label="Export keywords"/);
  assert.match(keywordsPage, /faFileCsv/);
  assert.match(keywordsPage, /faFileExcel/);
  assert.match(keywordsPage, /handleExport\('csv'\)/);
  assert.match(keywordsPage, /handleExport\('xlsx'\)/);
  assert.match(keywordsPage, /CSV \{exportScopeLabel\}/);
  assert.match(keywordsPage, /XLSX \{exportScopeLabel\}/);
  assert.match(keywordsPage, /selectionPageOnly=\{false\}/);
  assert.match(keywordsPage, /field="location" header="Location"/);
});

test('country selection is enabled and dependent fields clear on changes', () => {
  assert.match(keywordsPage, /value=\{locationCountry\}/);
  assert.match(keywordsPage, /setLocationState\('\'\)/);
  assert.match(keywordsPage, /setLocationCity\('\'\)/);
  assert.match(keywordsPage, /required\s*\n\s*disabled=\{isSubmitting\}/);
});
