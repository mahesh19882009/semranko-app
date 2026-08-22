'use client'
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api';

// Razorpay configuration - will be loaded from backend
let razorpayKey = null;

export function setRazorpayKey(key) {
  razorpayKey = key;
}

export function getRazorpayKey() {
  return razorpayKey;
}

async function parseJsonSafe(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export class ApiRequestError extends Error {
  constructor(message, normalized = {}) {
    super(message);
    this.name = 'ApiRequestError';
    Object.assign(this, normalizeApiError(normalized, message));
    this.message = message;
  }
}

const FIELD_LABELS = {
  email: 'Email', password: 'Password', name: 'Name', mobile: 'Mobile number',
  mobileNumber: 'Mobile number', otp: 'OTP', token: 'Verification token',
  newPassword: 'New password', currentPassword: 'Current password',
  domain: 'Domain', keyword: 'Keyword', keywords: 'Keywords', projectId: 'Project',
  planId: 'Plan', amount: 'Amount', paymentId: 'Payment',
};

const CODE_MESSAGES = {
  INVALID_CREDENTIALS: 'Invalid email or password.',
  EMAIL_VERIFICATION_REQUIRED: 'Please verify your email before logging in.',
  MOBILE_VERIFICATION_REQUIRED: 'Please verify your mobile number before logging in.',
  VERIFICATION_TOKEN_EXPIRED: 'This verification link is invalid or has expired.',
  MOBILE_VERIFICATION_SESSION_EXPIRED: 'Your mobile verification session is invalid or expired. Please log in again.',
  OTP_EXPIRED: 'The OTP has expired. Please request a new one.',
  OTP_INVALID: 'The OTP is incorrect. Please try again.',
  OTP_ATTEMPTS_EXCEEDED: 'Maximum OTP attempts exceeded. Please request a new OTP.',
  OTP_RESEND_COOLDOWN: 'Please wait before requesting another OTP.',
  OTP_SEND_LIMIT_EXCEEDED: 'Too many OTP requests. Please try again later.',
  INVALID_MOBILE_NUMBER: 'Enter a valid mobile number for the selected country.',
  TURNSTILE_REQUIRED: 'Complete the security check to continue.',
  TURNSTILE_REJECTED: 'The security check failed. Please try again.',
  CSRF_INVALID: 'Your security session is invalid. Refresh the page and try again.',
  SESSION_EXPIRED: 'Your session has expired. Please log in again.',
  upgrade_required: 'This feature is available on paid plans. Upgrade to continue.',
  feature_limit_exceeded: 'Your allowance for this feature is exhausted until the next billing-cycle reset.',
  KEYWORD_INACTIVE: 'Activate this keyword before refreshing it.',
  INSUFFICIENT_CREDITS: 'You do not have enough spendable credits for this action.',
  PROJECT_LIMIT_REACHED: 'Your project limit has been reached. Upgrade to add another project.',
  KEYWORD_LIMIT_REACHED: 'Your keyword limit has been reached.',
  DUPLICATE_KEYWORD: 'This keyword is already being tracked in the project.',
  KEYWORD_READD_COOLDOWN: 'This keyword was recently deleted and cannot be added again yet.',
  PAYMENT_VERIFICATION_FAILED: 'We could not verify this payment. Please try again or contact support.',
  PAYMENT_PLAN_MISMATCH: 'This payment does not match the selected plan. No subscription changes were made.',
};

function rateLimitMessage(endpoint) {
  if (endpoint === '/auth/register') return 'Too many registration attempts. Please try again later.';
  if (endpoint === '/auth/login') return 'Too many login attempts. Please try again shortly.';
  if (endpoint === '/auth/forgot-password') return 'Too many password reset requests. Please try again later.';
  if (endpoint === '/auth/send-otp' || endpoint === '/auth/resend-otp') {
    return 'Too many OTP requests. Please wait before trying again.';
  }
  return 'Too many requests. Please try again later.';
}

function retryAfterMessage(retryAfter) {
  const seconds = Number(retryAfter);
  if (!Number.isFinite(seconds) || seconds <= 0) return '';
  if (seconds < 60) return ` Try again in about ${Math.ceil(seconds)} seconds.`;
  const minutes = Math.ceil(seconds / 60);
  return ` Try again in about ${minutes} minute${minutes === 1 ? '' : 's'}.`;
}

function inferLegacyCode(message, status) {
  const text = String(message || '').toLowerCase();
  if (text.includes('insufficient credit')) return 'INSUFFICIENT_CREDITS';
  if (text.includes('domain limit') || text.includes('project limit')) return 'PROJECT_LIMIT_REACHED';
  if (text.includes('keyword limit')) return 'KEYWORD_LIMIT_REACHED';
  if (text.includes('recently deleted') || text.includes('cooldown')) return 'KEYWORD_READD_COOLDOWN';
  if (text.includes('already exists') && text.includes('keyword')) return 'DUPLICATE_KEYWORD';
  if (text.includes('activate this keyword')) return 'KEYWORD_INACTIVE';
  if (text.includes('invalid otp')) return 'OTP_INVALID';
  if (text.includes('otp has expired')) return 'OTP_EXPIRED';
  if (text.includes('maximum otp attempts')) return 'OTP_ATTEMPTS_EXCEEDED';
  if (text.includes('wait') && text.includes('otp')) return 'OTP_RESEND_COOLDOWN';
  if (text.includes('payment') && text.includes('mismatch')) return 'PAYMENT_PLAN_MISMATCH';
  if (status === 401) return 'UNAUTHORIZED';
  return null;
}

function sentence(value) {
  if (!value) return '';
  const text = String(value).trim().replace(/\.$/, '');
  return text ? `${text}.` : '';
}

function humanizeField(field) {
  if (!field) return 'This field';
  return FIELD_LABELS[field] || String(field)
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/^./, (char) => char.toUpperCase());
}

export function normalizeValidationErrors(detail) {
  if (!Array.isArray(detail)) return { fieldErrors: {}, message: null };
  const fieldErrors = {};
  const messages = [];
  detail.forEach((item) => {
    const loc = Array.isArray(item?.loc) ? item.loc : [];
    const field = [...loc].reverse().find((part) => !['body', 'query', 'path'].includes(String(part)));
    const label = humanizeField(field);
    const raw = String(item?.msg || 'is invalid');
    let message;
    if (/field required|required/i.test(raw)) message = `${label} is required.`;
    else if (/valid email/i.test(raw)) message = 'Enter a valid email address.';
    else message = sentence(`${label} ${raw.replace(/^value /i, '').toLowerCase()}`);
    if (field) fieldErrors[field] = message;
    messages.push(message);
  });
  return { fieldErrors, message: messages.join(' ') || null };
}

export function getApiErrorMessage(data, fallback = 'Request failed') {
  const structured = data?.data || {};
  const code = structured.error || data?.error;
  if (code === 'upgrade_required' || structured.upgrade_required) {
    return 'This feature is available on paid plans. Upgrade to continue.';
  }
  if (code === 'feature_limit_exceeded') {
    return 'Your allowance for this feature is exhausted until the next billing-cycle reset.';
  }
  if (code === 'KEYWORD_INACTIVE') return 'Activate this keyword before refreshing it.';
  if (code === 'INSUFFICIENT_CREDITS') return data?.message || 'You do not have enough spendable credits for this action.';
  return data?.message
    || (typeof data?.detail === 'string' ? data.detail : null)
    || normalizeValidationErrors(data?.detail).message
    || fallback;
}

export function normalizeApiError(error, fallback = 'Request failed') {
  if (error && error.__normalizedApiError) return error;
  const payload = error?.responseData || error?.payload || error || {};
  const structured = payload?.data && typeof payload.data === 'object' ? payload.data : {};
  const detailData = payload?.detail && typeof payload.detail === 'object' && !Array.isArray(payload.detail)
    ? payload.detail
    : {};
  const validation = normalizeValidationErrors(payload?.detail);
  const status = Number(error?.status ?? payload?.status ?? 0) || 0;
  const retryAfter = error?.retryAfter ?? structured.retryAfter ?? detailData.retryAfter ?? payload?.retryAfter ?? null;
  const code = error?.code || structured.error || detailData.error || payload.error
    || (status === 429 ? 'RATE_LIMITED' : null)
    || inferLegacyCode(error?.message || getApiErrorMessage(payload, fallback), status);
  let message = CODE_MESSAGES[code]
    || error?.message
    || getApiErrorMessage(payload, fallback);
  if (status === 429 && code !== 'feature_limit_exceeded') {
    message = `${rateLimitMessage(error?.endpoint || '')}${retryAfterMessage(retryAfter)}`;
  }
  if (!status && (error instanceof TypeError || /failed to fetch|networkerror/i.test(message || ''))) {
    message = "We couldn't connect to Semranko. Check your connection and try again.";
  } else if (error?.name === 'AbortError' || code === 'REQUEST_TIMEOUT') {
    message = 'The request took too long. Please try again.';
  } else if (status >= 500) {
    message = 'Something went wrong while processing your request. Please try again.';
  }
  const usage = structured.usage || payload.usage || {};
  if (code === 'feature_limit_exceeded' && usage.limit != null) {
    message = `You've used ${usage.used ?? usage.limit} of ${usage.limit} for this billing cycle.`;
  }
  const structuredFieldErrors = structured.fieldErrors && typeof structured.fieldErrors === 'object'
    ? structured.fieldErrors
    : {};
  return {
    __normalizedApiError: true,
    status,
    code,
    message: message || fallback,
    data: structured,
    fieldErrors: { ...validation.fieldErrors, ...structuredFieldErrors },
    action: structured.action || payload.action || null,
    upgradeRequired: Boolean(structured.upgrade_required || code === 'upgrade_required'),
    resetAt: usage.resetAt || structured.resetAt || null,
    remaining: usage.remaining ?? structured.remaining ?? null,
    retryAfter: Number.isFinite(Number(retryAfter)) ? Number(retryAfter) : null,
  };
}

export function toRejectedValue(error, fallback, context = {}) {
  return { ...normalizeApiError(error, fallback), ...context };
}

export async function verifyEmailApi(token) {
  return apiRequest('/auth/verify-email', {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export async function resendVerificationApi(email) {
  return apiRequest('/auth/resend-verification', {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });

}

export async function forgotPasswordApi(email, turnstileToken = null) {
  return apiRequest('/auth/forgot-password', {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, turnstileToken }),
  });

}

export async function resetPasswordApi(token, newPassword) {
  return apiRequest('/auth/reset-password', {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token, newPassword }),
  });

}

export async function sendMobileOtpApi(verificationToken, mobile, mobileCountry = 'IN', turnstileToken = null) {
  return apiRequest('/auth/send-otp', {
    method: 'POST',
    body: JSON.stringify({ verificationToken, mobile, mobileCountry, turnstileToken }),
  });
}

export async function verifyMobileOtpApi(verificationToken, otp) {
  return apiRequest('/auth/verify-otp', {
    method: 'POST',
    body: JSON.stringify({ verificationToken, otp }),
  });
}

export async function resendMobileOtpApi(verificationToken, turnstileToken = null) {
  return apiRequest('/auth/resend-otp', {
    method: 'POST',
    body: JSON.stringify({ verificationToken, turnstileToken }),
  });
}

export async function createMobileVerificationSessionApi(email, password) {
  return apiRequest('/auth/mobile-verification-session', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function researchKeywordApi(keyword, locationCode = 2840, location = "India") {
  return apiRequest(`/keyword-research/research?keyword=${encodeURIComponent(keyword)}&location_code=${encodeURIComponent(locationCode)}&location=${encodeURIComponent(location)}`);
}

export async function competitorSpyApi(domain, locationCode = 2840, location = "India", limit = 100) {
  return apiRequest(`/keyword-research/competitor-spy?domain=${encodeURIComponent(domain)}&location_code=${encodeURIComponent(locationCode)}&location=${encodeURIComponent(location)}&limit=${limit}`);
}

export async function onboardProjectApi({ name, domain, locationCode, location = "India", keywords }) {
  const params = new URLSearchParams();
  params.set('name', name);
  params.set('domain', domain);
  params.set('location_code', locationCode);
  params.set('location', location);
  keywords.forEach(kw => params.append('keywords', kw));
  return apiRequest(`/keyword-research/project/onboard?${params.toString()}`, {
    method: "POST",
  });
}

export async function getKeywordHistoryApi(projectId, keywordId) {
  return apiRequest(`/keywords/${projectId}/history/${keywordId}`);
}

export async function getWeeklyComparisonApi(projectId) {
  return apiRequest(`/keywords/${projectId}/weekly-comparison`);
}

export async function getLHFOpportunitiesApi(projectId, limit = 20) {
  return apiRequest(`/lhf/opportunities?project_id=${projectId}&limit=${limit}`);
}

export async function getLHFSummaryApi(projectId) {
  return apiRequest(`/lhf/summary?project_id=${projectId}`);
}

export async function getSerpFeaturesForKeywordApi(projectId, keyword) {
  return apiRequest(`/serp-features/keyword?project_id=${projectId}&keyword=${encodeURIComponent(keyword)}`);
}

export async function getSerpFeaturesSummaryApi(projectId) {
  return apiRequest(`/serp-features/summary?project_id=${projectId}`);
}

export async function getKeywordsWithSerpFeaturesApi(projectId, limit = 50) {
  return apiRequest(`/serp-features/keywords?project_id=${projectId}&limit=${limit}`);
}

export async function syncSerpFeaturesApi(projectId) {
  return apiRequest(`/serp-features/sync?project_id=${projectId}`, {
    method: "POST",
  });
}

export async function createApiKeyApi(name, expiresInDays) {
  return apiRequest('/api-keys/create', {
    method: "POST",
    body: JSON.stringify({ name, expires_in_days: expiresInDays }),
  });
}

export async function listApiKeysApi() {
  return apiRequest('/api-keys/list');
}

export async function deactivateApiKeyApi(apiKeyId) {
  return apiRequest(`/api-keys/${apiKeyId}/deactivate`, {
    method: "POST",
  });
}

export async function deleteApiKeyApi(apiKeyId) {
  return apiRequest(`/api-keys/${apiKeyId}`, {
    method: "DELETE",
  });
}

export async function createScheduledReportApi(projectId, name, frequency, format, recipients, startDate) {
  const body = { project_id: projectId, name, frequency, format, recipients };
  if (startDate) {
    body.start_date = startDate;
  }
  return apiRequest('/scheduled-reports/create', {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listScheduledReportsApi() {
  return apiRequest('/scheduled-reports/list');
}

export async function updateScheduledReportApi(reportId, updates) {
  return apiRequest(`/scheduled-reports/${reportId}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function deleteScheduledReportApi(reportId) {
  return apiRequest(`/scheduled-reports/${reportId}`, {
    method: "DELETE",
  });
}



export async function getAgencyOverviewApi() {
  return apiRequest('/agency-dashboard/overview');
}

export async function getProjectComparisonApi() {
  return apiRequest('/agency-dashboard/comparison');
}

export async function getRoiMetricsApi() {
  return apiRequest('/agency-dashboard/roi');
}


function handleUnauthenticated() {
  try {
    localStorage.removeItem('user');
  } catch {
    // ignore storage errors
  }
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    const returnTo = `${window.location.pathname}${window.location.search}`;
    window.location.assign(`/login?sessionExpired=true&returnTo=${encodeURIComponent(returnTo)}`);
  }
}

export const apiRequest = async (endpoint, options = {}) => {
  const method = String(options.method || 'GET').toUpperCase();
  const csrfToken = typeof document !== 'undefined'
    ? document.cookie.split('; ').find((entry) => entry.startsWith('semranko_csrf='))?.split('=').slice(1).join('=')
    : null;

  const headers = {
    'Content-Type': 'application/json',
    ...(!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken ? { 'X-CSRF-Token': decodeURIComponent(csrfToken) } : {}),
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers, credentials: 'include' });
  } catch (error) {
    throw new ApiRequestError(normalizeApiError(error).message, normalizeApiError(error));
  }

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  let data;

  if (isJson) {
    data = await parseJsonSafe(response);
  } else {
    data = null;
  }

  if (!response.ok) {
    const errorData = data?.data || null;
    const code = errorData?.error || data?.error || null;
    const normalized = normalizeApiError({
      status: response.status,
      responseData: data,
      code,
      message: getApiErrorMessage(data, response.status >= 500 ? 'Server error' : 'Request failed'),
      endpoint,
      retryAfter: response.headers.get('retry-after'),
    });
    const publicAuthRoute = endpoint.startsWith('/auth/') && endpoint !== '/auth/logout';
    if (response.status === 401 && !publicAuthRoute) {
      normalized.code = normalized.code || 'SESSION_EXPIRED';
      normalized.message = CODE_MESSAGES.SESSION_EXPIRED;
      handleUnauthenticated();
    }
    throw new ApiRequestError(normalized.message, normalized);
  }

  return data;
};

export async function exportProjectKeywordsApi(projectId, format, keywordIds = []) {
  const csrfToken = typeof document !== 'undefined'
    ? document.cookie.split('; ').find((entry) => entry.startsWith('semranko_csrf='))?.split('=').slice(1).join('=')
    : null;
  const endpoint = `/keywords/${projectId}/export`;
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRF-Token': decodeURIComponent(csrfToken) } : {}),
      },
      body: JSON.stringify({ format, keyword_ids: keywordIds }),
    });
  } catch (error) {
    const normalized = normalizeApiError(error, 'Export failed');
    throw new ApiRequestError(normalized.message, normalized);
  }

  if (!response.ok) {
    const data = await parseJsonSafe(response);
    const normalized = normalizeApiError({
      status: response.status,
      responseData: data,
      message: getApiErrorMessage(data, 'Export failed'),
      endpoint,
    });
    if (response.status === 401) handleUnauthenticated();
    throw new ApiRequestError(normalized.message, normalized);
  }

  return {
    blob: await response.blob(),
    filename: response.headers.get('content-disposition')?.match(/filename="?([^";]+)"?/)?.[1] || null,
  };
}

export async function logoutApi() {
  try {
    await apiRequest('/auth/logout', { method: 'POST' });
    return true;
  } finally {
    localStorage.removeItem('user');
  }
}

export async function registerApi(payload) {
  return apiRequest('/auth/register', {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

}

/**
 * Initialize Razorpay checkout
 * @param {Object} options - Checkout options
 * @param {string} options.order_id - Razorpay order ID
 * @param {number} options.amount - Amount in paise
 * @param {string} options.currency - Currency code
 * @param {string} options.key_id - Razorpay key ID
 * @param {Function} options.onPaymentSuccess - Callback on successful payment
 * @param {Function} options.onPaymentError - Callback on payment error
 */
export async function initRazorpayCheckout(options) {
  const {
    order_id,
    amount,
    currency,
    key_id,
    onPaymentSuccess,
    onPaymentError,
  } = options;

  // Store the key for later use
  setRazorpayKey(key_id);

  // Check if Razorpay script is loaded
  if (typeof window.Razorpay === 'undefined') {
    // Load Razorpay script dynamically
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = resolve;
      script.onerror = () => reject(new Error('Failed to load Razorpay SDK'));
      document.body.appendChild(script);
    });
  }

  // Track whether payment was already handled to prevent ondismiss from firing error
  let paymentHandled = false;

  const razorpayOptions = {
    key: key_id,
    amount: amount,
    currency: currency,
    name: 'Semranko',
    description: 'SEO Rank Tracking Subscription',
    order_id: order_id,
    handler: function (response) {
      // Mark payment as handled so ondismiss doesn't trigger error
      paymentHandled = true;
      // Payment successful - call the success callback
      onPaymentSuccess(response);
    },
    prefill: {
      name: options.prefill?.name || '',
      email: options.prefill?.email || '',
      contact: options.prefill?.contact || '',
    },
    theme: {
      color: '#4F46E5',
    },
    modal: {
      ondismiss: function () {
        // Only call error callback if payment wasn't already handled
        if (!paymentHandled && onPaymentError) {
          onPaymentError({ error: { description: 'Payment cancelled by user' } });
        }
      },
    },
  };

  const rzp = new window.Razorpay(razorpayOptions);
  
  rzp.on('payment.failed', function (response) {
    paymentHandled = true;
    if (onPaymentError) {
      onPaymentError(response.error);
    }
  });

  rzp.open();
  
  return rzp;
}
