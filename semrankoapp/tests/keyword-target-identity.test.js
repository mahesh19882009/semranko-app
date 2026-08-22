import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

import {
  keywordTargetKey,
  normalizeKeywordTargetDevice,
} from '../src/features/keywords/keywordTargetIdentity.js';
import {
  addOptimisticProcessingJobs,
  completeProcessingKeyword,
  reconcileBulkProcessingJobs,
  reconcileProcessingJobsToServerTargets,
  buildActiveProcessingJobsByTarget,
} from '../src/features/keywords/processingState.js';

test('Keyword.id is preferred and temporary keys include location and device', () => {
  assert.equal(keywordTargetKey({ id: 'kw-1', keyword: 'same', locationCode: 2840, device: 'desktop' }), 'id:kw-1');
  assert.notEqual(
    keywordTargetKey({ keyword: 'Same', locationCode: 2840, device: 'desktop' }),
    keywordTargetKey({ keyword: ' same ', locationCode: 2356, device: 'desktop' })
  );
  assert.notEqual(
    keywordTargetKey({ keyword: 'same', locationCode: 2840, device: 'desktop' }),
    keywordTargetKey({ keyword: 'same', locationCode: 2840, device: 'mobile' })
  );
  assert.equal(
    keywordTargetKey({ keyword: ' SAME ', locationCode: '2840', device: 'DESKTOP' }),
    keywordTargetKey({ keyword: 'same', locationCode: 2840, device: 'desktop' })
  );
  assert.equal(normalizeKeywordTargetDevice(' MOBILE '), 'mobile');
});

test('same-text targets maintain independent processing and shimmer identities', () => {
  let jobs = addOptimisticProcessingJobs([], [
    { keyword: 'seo company', locationCode: 2840, device: 'desktop' },
    { keyword: 'seo company', locationCode: 2356, device: 'desktop' },
    { keyword: 'seo company', locationCode: 2840, device: 'mobile' },
  ], 'bulk-1');
  assert.equal(jobs.length, 3);
  assert.equal(buildActiveProcessingJobsByTarget(jobs).size, 3);

  jobs = completeProcessingKeyword(jobs, { keyword: 'seo company', locationCode: 2840, device: 'desktop' });
  assert.equal(jobs.length, 2);
  assert.deepEqual(jobs.map((job) => job.locationCode), [2356, 2840]);
});

test('ambiguous legacy completion does not clear same-text targets', () => {
  const jobs = addOptimisticProcessingJobs([], [
    { keyword: 'seo company', locationCode: 2840, device: 'desktop' },
    { keyword: 'seo company', locationCode: 2356, device: 'desktop' },
  ], 'bulk-1');
  assert.equal(completeProcessingKeyword(jobs, 'seo company').length, 2);
});

test('bulk reconciliation and server-id promotion remain target-specific', () => {
  let jobs = addOptimisticProcessingJobs([], [
    { keyword: 'seo company', locationCode: 2840, device: 'desktop' },
    { keyword: 'seo company', locationCode: 2356, device: 'desktop' },
  ], 'bulk-1');
  jobs = reconcileBulkProcessingJobs(jobs, 'bulk-1', {
    keywords: ['seo company'],
    accepted_targets: [{ keyword: 'seo company', keyword_id: 'india-id', location_code: 2840, device: 'desktop' }],
  });
  assert.equal(jobs.length, 1);
  jobs = reconcileProcessingJobsToServerTargets(jobs, 'bulk-1', [
    { id: 'india-id', keyword: 'seo company', location_code: 2840, device: 'desktop' },
  ]);
  assert.equal(jobs[0].keywordId, 'india-id');
  assert.equal(jobs[0].id, 'id:india-id');
});

test('KeywordsPage keeps row and export selection identity on Keyword.id', async () => {
  const page = await readFile(new URL('../src/views/KeywordsPage.jsx', import.meta.url), 'utf8');
  assert.match(page, /dataKey="id"/);
  assert.match(page, /selectedIds\.map\(\(row\) => row\.id\)/);
  assert.match(page, /keywordTargetKey\(row\)/);
});
