export const normalizeProcessingKeyword = (keyword) =>
  String(keyword || '').trim().toLowerCase();

const ACTIVE_PROCESSING_STATUSES = new Set([
  'pending',
  'processing',
  'retry',
]);

export const isActiveProcessingJob = (job) =>
  ACTIVE_PROCESSING_STATUSES.has(job?.status);

export function buildActiveProcessingJobsByKeyword(processingJobs) {
  return new Map(
    (Array.isArray(processingJobs) ? processingJobs : [])
      .filter((job) => job?.keyword && isActiveProcessingJob(job))
      .map((job) => [normalizeProcessingKeyword(job.keyword), job])
  );
}

export function getKeywordFieldDisplayState(rowData, value) {
  const hasValue =
    value !== null &&
    value !== undefined &&
    value !== '';

  if (hasValue) return 'value';
  return rowData?.isProcessing === true ? 'shimmer' : 'empty';
}

const createOptimisticProcessingJob = (keyword, submissionId) => {
  const normalizedKeyword = normalizeProcessingKeyword(keyword);

  return {
    id: `processing:${normalizedKeyword}`,
    keyword,
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
  };
};

export function addOptimisticProcessingJobs(
  current,
  submittedKeywords,
  submissionId
) {
  const result = [...current];
  const indexByKeyword = new Map(
    result.map((job, index) => [
      normalizeProcessingKeyword(job.keyword),
      index,
    ])
  );

  for (const keyword of submittedKeywords) {
    const normalizedKeyword = normalizeProcessingKeyword(keyword);
    if (!normalizedKeyword) continue;

    const existingIndex = indexByKeyword.get(normalizedKeyword);
    if (existingIndex !== undefined) {
      const existingJob = result[existingIndex];
      if (
        Array.isArray(existingJob.submissionIds) &&
        !existingJob.submissionIds.includes(submissionId)
      ) {
        result[existingIndex] = {
          ...existingJob,
          submissionIds: [...existingJob.submissionIds, submissionId],
        };
      }
      continue;
    }

    indexByKeyword.set(normalizedKeyword, result.length);
    result.push(createOptimisticProcessingJob(keyword, submissionId));
  }

  return result;
}

const settleProcessingSubmission = (
  current,
  submissionId,
  acceptedKeywords
) => {
  const accepted = new Set(
    acceptedKeywords.map(normalizeProcessingKeyword).filter(Boolean)
  );

  return current.flatMap((job) => {
    if (
      !Array.isArray(job.submissionIds) ||
      !job.submissionIds.includes(submissionId)
    ) {
      return [job];
    }

    if (accepted.has(normalizeProcessingKeyword(job.keyword))) {
      return [job];
    }

    const remainingSubmissionIds = job.submissionIds.filter(
      (id) => id !== submissionId
    );

    if (remainingSubmissionIds.length === 0) {
      return [];
    }

    return [{ ...job, submissionIds: remainingSubmissionIds }];
  });
};

export function reconcileBulkProcessingJobs(
  current,
  submissionId,
  responseData
) {
  const acceptedKeywords = Array.isArray(responseData?.keywords)
    ? responseData.keywords
    : [];

  return settleProcessingSubmission(
    current,
    submissionId,
    acceptedKeywords
  );
}

export function removeProcessingSubmission(current, submissionId) {
  return settleProcessingSubmission(current, submissionId, []);
}

export function completeProcessingKeyword(current, completedKeyword) {
  const normalizedKeyword = normalizeProcessingKeyword(completedKeyword);
  if (!normalizedKeyword) return current;

  return current.filter(
    (job) =>
      normalizeProcessingKeyword(job.keyword) !== normalizedKeyword
  );
}

export function completeProcessingKeywords(current, completedKeywords) {
  const completed = new Set(
    (Array.isArray(completedKeywords) ? completedKeywords : [])
      .map(normalizeProcessingKeyword)
      .filter(Boolean)
  );

  if (completed.size === 0) return current;

  return current.filter(
    (job) => !completed.has(normalizeProcessingKeyword(job.keyword))
  );
}
