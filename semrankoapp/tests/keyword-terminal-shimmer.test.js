import test from 'node:test';
import assert from 'node:assert/strict';

import {
  addOptimisticProcessingJobs,
  buildActiveProcessingJobsByKeyword,
  completeProcessingKeyword,
  completeProcessingKeywords,
  getKeywordFieldDisplayState,
} from '../src/features/keywords/processingState.js';

const decorate = (rows, jobs) => {
  const activeByKeyword = buildActiveProcessingJobsByKeyword(jobs);

  return rows.map((row) => ({
    ...row,
    isProcessing: activeByKeyword.has(row.keyword.trim().toLowerCase()),
  }));
};

const state = (row, value) => getKeywordFieldDisplayState(row, value);

test('pending keyword with no metrics shimmers missing fields', () => {
  const [row] = decorate(
    [{ keyword: 'Pending Empty', volume: null, kd: null, cpc: null }],
    [{ keyword: 'pending empty', status: 'processing' }]
  );

  assert.equal(state(row, row.volume), 'shimmer');
  assert.equal(state(row, row.kd), 'shimmer');
  assert.equal(state(row, row.cpc), 'shimmer');
});

test('pending keyword with partial metrics keeps values and shimmers only gaps', () => {
  const [row] = decorate(
    [{ keyword: 'Partial Pending', volume: 10, kd: null, intent: 'commercial' }],
    [{ keyword: 'partial pending', status: 'pending' }]
  );

  assert.equal(state(row, row.volume), 'value');
  assert.equal(state(row, row.kd), 'shimmer');
  assert.equal(state(row, row.intent), 'value');
});

test('terminal keyword with all metrics null renders empty state despite stale row status', () => {
  const [row] = decorate(
    [{ keyword: 'Terminal Empty', status: 'processing', volume: null, kd: null, cpc: null }],
    []
  );

  assert.equal(row.isProcessing, false);
  assert.equal(state(row, row.volume), 'empty');
  assert.equal(state(row, row.kd), 'empty');
  assert.equal(state(row, row.cpc), 'empty');
});

test('terminal keyword with partial metrics keeps values and renders gaps empty', () => {
  const [row] = decorate(
    [{ keyword: 'Terminal Partial', volume: 10, kd: null, cpc: null, intent: 'commercial' }],
    []
  );

  assert.equal(state(row, row.volume), 'value');
  assert.equal(state(row, row.kd), 'empty');
  assert.equal(state(row, row.cpc), 'empty');
  assert.equal(state(row, row.intent), 'value');
});

test('position available before metrics remains visible while metrics shimmer', () => {
  const [row] = decorate(
    [{ keyword: 'Rank First', position: 7, volume: null }],
    [{ keyword: 'rank first', status: 'retry' }]
  );

  assert.equal(state(row, row.position), 'value');
  assert.equal(state(row, row.volume), 'shimmer');
});

test('metrics available before SERP remain visible while missing SERP fields shimmer', () => {
  const [row] = decorate(
    [{ keyword: 'Metrics First', position: null, volume: 50, intent: 'informational' }],
    [{ keyword: 'metrics first', status: 'processing' }]
  );

  assert.equal(state(row, row.volume), 'value');
  assert.equal(state(row, row.intent), 'value');
  assert.equal(state(row, row.position), 'shimmer');
});

test('SSE completion removes shimmer only for the completed keyword', () => {
  let jobs = addOptimisticProcessingJobs([], ['First', 'Second'], 'bulk-1');
  jobs = completeProcessingKeyword(jobs, ' first ');

  const [first, second] = decorate(
    [
      { keyword: 'First', volume: null },
      { keyword: 'Second', volume: null },
    ],
    jobs
  );

  assert.equal(state(first, first.volume), 'empty');
  assert.equal(state(second, second.volume), 'shimmer');
});

test('completed_keywords reconciliation immediately makes the completed row terminal', () => {
  let jobs = addOptimisticProcessingJobs([], ['Cached', 'Async'], 'bulk-1');
  jobs = completeProcessingKeywords(jobs, [' CACHED ']);

  const [cached, pending] = decorate(
    [
      { keyword: 'Cached', volume: null },
      { keyword: 'Async', volume: null },
    ],
    jobs
  );

  assert.equal(state(cached, cached.volume), 'empty');
  assert.equal(state(pending, pending.volume), 'shimmer');
});

test('mixed bulk keeps completed values and empty states while sibling stays pending', () => {
  const jobs = [{ keyword: 'Pending Sibling', status: 'processing' }];
  const [completed, pending] = decorate(
    [
      { keyword: 'Completed Sibling', position: 36, volume: 10, kd: null },
      { keyword: 'Pending Sibling', position: null, volume: null, kd: null },
    ],
    jobs
  );

  assert.equal(state(completed, completed.position), 'value');
  assert.equal(state(completed, completed.volume), 'value');
  assert.equal(state(completed, completed.kd), 'empty');
  assert.equal(state(pending, pending.position), 'shimmer');
  assert.equal(state(pending, pending.volume), 'shimmer');
});

test('terminal jobs and unrelated processing rows do not affect another keyword', () => {
  const jobs = [
    { keyword: 'Finished', status: 'success' },
    { keyword: 'Unrelated', status: 'processing' },
  ];
  const [finished, unrelated, untouched] = decorate(
    [
      { keyword: 'Finished', volume: null },
      { keyword: 'Unrelated', volume: null },
      { keyword: 'Untouched', volume: null },
    ],
    jobs
  );

  assert.equal(state(finished, finished.volume), 'empty');
  assert.equal(state(unrelated, unrelated.volume), 'shimmer');
  assert.equal(state(untouched, untouched.volume), 'empty');
});
