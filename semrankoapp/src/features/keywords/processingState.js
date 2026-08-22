import {
  effectiveKeywordLocationCode,
  keywordTargetKey,
  normalizeKeywordTargetDevice,
  normalizeKeywordTargetText,
} from './keywordTargetIdentity.js';

export const normalizeProcessingKeyword = normalizeKeywordTargetText;
const ACTIVE_PROCESSING_STATUSES = new Set(['pending', 'processing', 'retry']);
export const isActiveProcessingJob = (job) => ACTIVE_PROCESSING_STATUSES.has(job?.status);

const targetWithoutIdKey = (target, fallbackLocationCode = 2840) => [
  normalizeKeywordTargetText(target?.keyword),
  effectiveKeywordLocationCode(target, fallbackLocationCode),
  normalizeKeywordTargetDevice(target?.device),
].join(':');

const toTarget = (value, defaults = {}) => typeof value === 'string'
  ? { keyword: value, ...defaults }
  : { ...(value || {}), ...defaults };

export const processingTargetKey = (job) => keywordTargetKey(job);

export function buildActiveProcessingJobsByKeyword(processingJobs) {
  const active = (Array.isArray(processingJobs) ? processingJobs : [])
    .filter((job) => job?.keyword && isActiveProcessingJob(job));
  const result = new Map(active.map((job) => [processingTargetKey(job), job]));
  const counts = new Map();
  active.forEach((job) => {
    const text = normalizeKeywordTargetText(job.keyword);
    counts.set(text, (counts.get(text) || 0) + 1);
  });
  active.forEach((job) => {
    const text = normalizeKeywordTargetText(job.keyword);
    if (counts.get(text) === 1) result.set(text, job);
  });
  return result;
}
export const buildActiveProcessingJobsByTarget = buildActiveProcessingJobsByKeyword;

export function getKeywordFieldDisplayState(rowData, value) {
  const hasValue = value !== null && value !== undefined && value !== '';
  if (hasValue) return 'value';
  return rowData?.isProcessing === true ? 'shimmer' : 'empty';
}

const createOptimisticProcessingJob = (target, submissionId) => ({
  id: keywordTargetKey(target),
  keyword: target.keyword,
  locationCode: effectiveKeywordLocationCode(target),
  device: normalizeKeywordTargetDevice(target.device),
  status: 'processing',
  position: null,
  localPackPosition: null,
  localPackUrl: null,
  check_url: null,
  ai_badge: null,
  volume: null,
  kd: null,
  cpc: null,
  competition: null,
  backlinks: null,
  referring_domains: null,
  intent: null,
  submissionIds: [submissionId],
});

export function addOptimisticProcessingJobs(current, submittedTargets, submissionId, defaults = {}) {
  const result = [...(Array.isArray(current) ? current : [])];
  const indexByTarget = new Map(result.map((job, index) => [processingTargetKey(job), index]));
  for (const value of submittedTargets || []) {
    const target = toTarget(value, defaults);
    if (!normalizeKeywordTargetText(target.keyword)) continue;
    const key = keywordTargetKey(target);
    const existingIndex = indexByTarget.get(key);
    if (existingIndex !== undefined) {
      const existingJob = result[existingIndex];
      if (Array.isArray(existingJob.submissionIds) && !existingJob.submissionIds.includes(submissionId)) {
        result[existingIndex] = { ...existingJob, submissionIds: [...existingJob.submissionIds, submissionId] };
      }
      continue;
    }
    indexByTarget.set(key, result.length);
    result.push(createOptimisticProcessingJob(target, submissionId));
  }
  return result;
}

const acceptedTargetsFor = (responseData) => {
  if (Array.isArray(responseData?.accepted_targets)) return responseData.accepted_targets;
  if (Array.isArray(responseData?.targets)) return responseData.targets;
  return Array.isArray(responseData?.keywords) ? responseData.keywords.map((keyword) => ({ keyword })) : [];
};

const settleProcessingSubmission = (current, submissionId, acceptedTargets) => {
  const accepted = (acceptedTargets || []).map((target) => ({ ...target, keyword: typeof target === 'string' ? target : target?.keyword }));
  const acceptedKeys = new Set(accepted.filter((target) => target.keyword).map((target) => keywordTargetKey(target)));
  const acceptedTargetKeys = new Set(accepted.filter((target) => target.keyword).map((target) => targetWithoutIdKey(target)));
  const acceptedText = new Set(accepted.map((target) => normalizeKeywordTargetText(target.keyword)).filter(Boolean));
  return current.flatMap((job) => {
    if (!Array.isArray(job.submissionIds) || !job.submissionIds.includes(submissionId)) return [job];
    const exactAccepted = acceptedKeys.has(processingTargetKey(job));
    const targetAccepted = acceptedTargetKeys.has(targetWithoutIdKey(job));
    const textAccepted = acceptedText.has(normalizeKeywordTargetText(job.keyword));
    const ambiguous = current.some((candidate) => candidate !== job && candidate.submissionIds?.includes(submissionId)
      && normalizeKeywordTargetText(candidate.keyword) === normalizeKeywordTargetText(job.keyword));
    if (exactAccepted || targetAccepted || (textAccepted && !ambiguous)) return [job];
    const remaining = job.submissionIds.filter((id) => id !== submissionId);
    return remaining.length ? [{ ...job, submissionIds: remaining }] : [];
  });
};

export function reconcileBulkProcessingJobs(current, submissionId, responseData) {
  return settleProcessingSubmission(current, submissionId, acceptedTargetsFor(responseData));
}

export function reconcileProcessingJobsToServerTargets(current, submissionId, serverTargets) {
  const targets = Array.isArray(serverTargets) ? serverTargets : [];
  return current.map((job) => {
    if (!job.submissionIds?.includes(submissionId)) return job;
    const match = targets.find((target) => targetWithoutIdKey(target) === targetWithoutIdKey(job));
    return match?.id ? { ...job, id: keywordTargetKey(match), keywordId: match.id } : job;
  });
}

export function removeProcessingSubmission(current, submissionId) {
  return settleProcessingSubmission(current, submissionId, []);
}

export function completeProcessingTargets(current, completedTargets) {
  const list = Array.isArray(completedTargets) ? completedTargets : [];
  return current.filter((job) => !list.some((target) => {
    const exactId = target?.keyword_id || target?.keywordId || (target?.id && String(target.id).startsWith('id:') ? String(target.id).slice(3) : null);
    if (exactId) {
      const jobId = job.keywordId || (String(job.id || '').startsWith('id:') ? String(job.id).slice(3) : null);
      return String(exactId) === String(jobId || '').trim();
    }
    const text = normalizeKeywordTargetText(typeof target === 'string' ? target : target?.keyword);
    if (!text || normalizeKeywordTargetText(job.keyword) !== text) return false;
    const candidates = current.filter((candidate) => normalizeKeywordTargetText(candidate.keyword) === text);
    if (candidates.length === 1) return true;
    if (typeof target === 'string' || (!target?.locationCode && !target?.location_code && !target?.device)) return false;
    return targetWithoutIdKey(job) === targetWithoutIdKey(target)
      && candidates.filter((candidate) => targetWithoutIdKey(candidate) === targetWithoutIdKey(target)).length === 1;
  }));
}

export const completeProcessingKeyword = (current, target) => completeProcessingTargets(current, [target]);
export const completeProcessingKeywords = (current, targets) => completeProcessingTargets(current, targets);
