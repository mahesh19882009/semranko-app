import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = async (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('keyword research and competitor spy do not persist cross-account payloads in browser storage', async () => {
  const page = await source('src/views/KeywordResearchPage.jsx');

  assert.doesNotMatch(page, /rankcare_keyword_research_cache/);
  assert.doesNotMatch(page, /rankcare_competitor_spy_cache/);
  assert.doesNotMatch(page, /localStorage\.getItem/);
  assert.doesNotMatch(page, /localStorage\.setItem/);
});

test('keyword research and competitor spy render explicit empty states until the user submits a query', async () => {
  const page = await source('src/views/KeywordResearchPage.jsx');

  assert.match(page, /run your first research report/i);
  assert.match(page, /No data is shown until you submit a query/i);
});
