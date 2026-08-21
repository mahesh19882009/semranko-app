import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

import {
  addOptimisticProcessingJobs,
  completeProcessingKeyword,
  reconcileBulkProcessingJobs,
  removeProcessingSubmission,
} from '../src/features/keywords/processingState.js';

const responseData = ({ accepted = [], skipped = [], failed = [] } = {}) => ({
  added: accepted.length,
  skipped: skipped.length,
  skipped_details: skipped,
  keywords: accepted,
  processed: accepted.length,
  failed_tracking: failed.length,
  tracking_errors: failed,
});

const keywords = (jobs) => jobs.map((job) => job.keyword);

test('all duplicate or skipped keywords are removed after fulfillment', () => {
  const optimistic = addOptimisticProcessingJobs(
    [],
    ['Existing Keyword', 'SECOND DUPLICATE'],
    'bulk-1'
  );

  const reconciled = reconcileBulkProcessingJobs(
    optimistic,
    'bulk-1',
    responseData({
      skipped: [
        { keyword: 'existing keyword', reason: 'duplicate' },
        { keyword: 'second duplicate', reason: 'duplicate' },
      ],
    })
  );

  assert.deepEqual(reconciled, []);
});

test('mixed accepted and duplicate response keeps only the accepted keyword', () => {
  const optimistic = addOptimisticProcessingJobs(
    [],
    ['Accepted Keyword', 'Existing Keyword'],
    'bulk-1'
  );

  const reconciled = reconcileBulkProcessingJobs(
    optimistic,
    'bulk-1',
    responseData({
      accepted: ['accepted keyword'],
      skipped: [{ keyword: 'existing keyword', reason: 'duplicate' }],
    })
  );

  assert.deepEqual(keywords(reconciled), ['Accepted Keyword']);
});

test('cooldown skips and tracking failures are removed immediately', () => {
  const optimistic = addOptimisticProcessingJobs(
    [],
    ['Cooldown Keyword', 'Failed Keyword'],
    'bulk-1'
  );

  const reconciled = reconcileBulkProcessingJobs(
    optimistic,
    'bulk-1',
    responseData({
      skipped: [
        { keyword: 'cooldown keyword', reason: 'cooldown_active' },
      ],
      failed: [
        { keyword: 'failed keyword', error: 'tracking submission failed' },
      ],
    })
  );

  assert.deepEqual(reconciled, []);
});

test('partial provider acceptance preserves accepted cached and uncached keywords only', () => {
  const optimistic = addOptimisticProcessingJobs(
    [],
    ['Cached Accepted', 'Uncached Accepted', 'Provider Failed'],
    'bulk-1'
  );

  const reconciled = reconcileBulkProcessingJobs(
    optimistic,
    'bulk-1',
    responseData({
      accepted: ['cached accepted', 'uncached accepted'],
      failed: [
        { keyword: 'provider failed', error: 'tracking submission failed' },
      ],
    })
  );

  assert.deepEqual(
    keywords(reconciled),
    ['Cached Accepted', 'Uncached Accepted']
  );
});

test('CSV partial success uses normalized matching and keeps unrelated rows', () => {
  const unrelated = {
    id: 'processing:unrelated',
    keyword: 'Unrelated Pending',
    status: 'processing',
  };
  const optimistic = addOptimisticProcessingJobs(
    [unrelated],
    ['SEO Agency', 'Duplicate Keyword'],
    'csv-1'
  );

  const reconciled = reconcileBulkProcessingJobs(
    optimistic,
    'csv-1',
    responseData({
      accepted: ['  seo AGENCY  '],
      skipped: [{ keyword: 'duplicate keyword', reason: 'duplicate' }],
    })
  );

  assert.deepEqual(
    keywords(reconciled),
    ['Unrelated Pending', 'SEO Agency']
  );
  assert.equal(reconciled[0], unrelated);
});

test('overlapping submissions cannot clear another submission claim', () => {
  let current = addOptimisticProcessingJobs(
    [],
    ['Shared Keyword'],
    'bulk-1'
  );
  current = addOptimisticProcessingJobs(
    current,
    ['shared keyword'],
    'bulk-2'
  );

  current = removeProcessingSubmission(current, 'bulk-1');
  assert.deepEqual(keywords(current), ['Shared Keyword']);

  current = reconcileBulkProcessingJobs(
    current,
    'bulk-2',
    responseData({ accepted: ['SHARED KEYWORD'] })
  );
  assert.deepEqual(keywords(current), ['Shared Keyword']);
});

test('an existing unrelated processing keyword is never re-owned or removed', () => {
  const existing = {
    id: 'server-pending-1',
    keyword: 'Already Processing',
    status: 'pending',
  };
  let current = addOptimisticProcessingJobs(
    [existing],
    ['already processing', 'New Duplicate'],
    'bulk-1'
  );

  current = reconcileBulkProcessingJobs(
    current,
    'bulk-1',
    responseData({
      skipped: [
        { keyword: 'already processing', reason: 'duplicate' },
        { keyword: 'new duplicate', reason: 'duplicate' },
      ],
    })
  );

  assert.deepEqual(current, [existing]);
  assert.equal(current[0], existing);
});

test('accepted keywords remain until SSE completes only the matching keyword', () => {
  const unrelated = {
    id: 'server-pending-1',
    keyword: 'Unrelated Pending',
    status: 'pending',
  };
  let current = addOptimisticProcessingJobs(
    [unrelated],
    ['First Accepted', 'Second Accepted'],
    'bulk-1'
  );
  current = reconcileBulkProcessingJobs(
    current,
    'bulk-1',
    responseData({ accepted: ['first accepted', 'second accepted'] })
  );

  assert.deepEqual(
    keywords(current),
    ['Unrelated Pending', 'First Accepted', 'Second Accepted']
  );

  current = completeProcessingKeyword(current, ' FIRST ACCEPTED ');
  assert.deepEqual(
    keywords(current),
    ['Unrelated Pending', 'Second Accepted']
  );
});

test('Redux and modal/CSV handlers retain and consume backend reconciliation data', async () => {
  const slice = await readFile(
    new URL('../src/features/keywords/keywordsSlice.js', import.meta.url),
    'utf8'
  );
  const page = await readFile(
    new URL('../src/views/KeywordsPage.jsx', import.meta.url),
    'utf8'
  );

  assert.match(slice, /data: response\.data \|\| \{\}/);
  assert.match(page, /reconcileBulkProcessingJobs/);
  assert.match(page, /addOptimisticProcessingJobs/);
  assert.match(page, /completeProcessingKeyword/);
});
