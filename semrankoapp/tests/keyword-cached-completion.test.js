import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

import {
  addOptimisticProcessingJobs,
  completeProcessingKeywords,
} from '../src/features/keywords/processingState.js';

const names = (jobs) => jobs.map((job) => job.keyword);

test('fully cached completion clears only its processing keyword', () => {
  const unrelated = {
    id: 'unrelated',
    keyword: 'Unrelated Pending',
    status: 'pending',
  };
  const current = addOptimisticProcessingJobs(
    [unrelated],
    ['Fully Cached'],
    'add-1'
  );

  const completed = completeProcessingKeywords(
    current,
    [' fully CACHED ']
  );

  assert.deepEqual(names(completed), ['Unrelated Pending']);
  assert.equal(completed[0], unrelated);
});

test('mixed bulk clears cached keywords and preserves async keyword', () => {
  const current = addOptimisticProcessingJobs(
    [],
    ['Cached A', 'Async B', 'Cached C'],
    'bulk-1'
  );

  const completed = completeProcessingKeywords(
    current,
    ['cached a', 'CACHED C']
  );

  assert.deepEqual(names(completed), ['Async B']);
});

test('duplicate cached completion is idempotent', () => {
  const current = addOptimisticProcessingJobs(
    [],
    ['Cached Keyword', 'Async Keyword'],
    'bulk-1'
  );

  const once = completeProcessingKeywords(current, ['cached keyword']);
  const twice = completeProcessingKeywords(once, ['CACHED KEYWORD']);

  assert.deepEqual(twice, once);
  assert.deepEqual(names(twice), ['Async Keyword']);
});

test('single, modal bulk, and CSV consume committed completion metadata', async () => {
  const slice = await readFile(
    new URL('../src/features/keywords/keywordsSlice.js', import.meta.url),
    'utf8'
  );
  const page = await readFile(
    new URL('../src/views/KeywordsPage.jsx', import.meta.url),
    'utf8'
  );

  assert.match(slice, /message: response\.message \|\| 'Keyword added successfully',[\s\S]*data: response\.data \|\| \{\}/);
  assert.match(page, /resultAction\.payload\?\.data\?\.completed_keywords/);
  assert.match(page, /completeProcessingKeywords/);
});
