'use client'
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api';

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

export async function verifyEmailApi(token) {
  const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token }),
  });

  const result = await parseJsonSafe(response);

  if (!response.ok || !result?.success) {
    throw new Error(result?.message || "Email verification failed");
  }

  return result;
}

export async function resendVerificationApi(email) {
  const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });

  const result = await parseJsonSafe(response);

  if (!response.ok || !result?.success) {
    throw new Error(result?.message || "Failed to resend verification email");
  }

  return result;
}

export async function forgotPasswordApi(email) {
  const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });

  const result = await parseJsonSafe(response);

  if (!response.ok || !result?.success) {
    throw new Error(result?.message || "Failed to send password reset email");
  }

  return result;
}

export async function resetPasswordApi(token, newPassword) {
  const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token, newPassword }),
  });

  const result = await parseJsonSafe(response);

  if (!response.ok || !result?.success) {
    throw new Error(result?.message || "Failed to reset password");
  }

  return result;
}

export async function researchKeywordApi(keyword, location = "India") {
  return apiRequest(`/keyword-research/research?keyword=${encodeURIComponent(keyword)}&location=${encodeURIComponent(location)}`);
}

export async function competitorSpyApi(domain, location = "India", limit = 100) {
  return apiRequest(`/keyword-research/competitor-spy?domain=${encodeURIComponent(domain)}&location=${encodeURIComponent(location)}&limit=${limit}`);
}

export async function onboardProjectApi({ name, domain, location, keywords }) {
  const params = new URLSearchParams();
  params.set('name', name);
  params.set('domain', domain);
  params.set('location', location);
  keywords.forEach(kw => params.append('keywords', kw));
  return apiRequest(`/keyword-research/project/onboard?${params.toString()}`, {
    method: "POST",
  });
}

export async function createKeywordListApi(name) {
  return apiRequest('/keyword-lists/', {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function listKeywordListsApi() {
  return apiRequest('/keyword-lists/');
}

export async function addKeywordsToListApi(listId, keywords) {
  return apiRequest(`/keyword-lists/${listId}/items`, {
    method: "POST",
    body: JSON.stringify({ keywords }),
  });
}

export async function removeKeywordFromListApi(listId, itemId) {
  return apiRequest(`/keyword-lists/${listId}/items/${itemId}`, {
    method: "DELETE",
  });
}

export async function deleteKeywordListApi(listId) {
  return apiRequest(`/keyword-lists/${listId}`, {
    method: "DELETE",
  });
}

export async function exportKeywordListApi(listId) {
  return apiRequest(`/keyword-lists/${listId}/export`);
}

export async function trackCompetitorRankingsApi(projectId) {
  return apiRequest(`/competitor-rankings/${projectId}/track`, {
    method: "POST",
  });
}

export async function getCompetitorComparisonApi(projectId) {
  return apiRequest(`/competitor-rankings/${projectId}/comparison`);
}

export async function trackAioApi(projectId) {
  return apiRequest(`/aio/${projectId}/track`, {
    method: "POST",
  });
}

export async function getAioDashboardApi(projectId) {
  return apiRequest(`/aio/${projectId}/dashboard`);
}

export async function getAioCitationsApi(projectId) {
  return apiRequest(`/aio/${projectId}/citations`);
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

export async function createTeamApi(name) {
  return apiRequest('/teams/create', {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function listTeamsApi() {
  return apiRequest('/teams/list');
}

export async function getTeamApi(teamId) {
  return apiRequest(`/teams/${teamId}`);
}

export async function getTeamMembersApi(teamId) {
  return apiRequest(`/teams/${teamId}/members`);
}

export async function inviteTeamMemberApi(teamId, email, role) {
  return apiRequest(`/teams/${teamId}/invite`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

export async function updateTeamMemberRoleApi(teamId, userId, role) {
  return apiRequest(`/teams/${teamId}/members/${userId}/role`, {
    method: "PUT",
    body: JSON.stringify({ role }),
  });
}

export async function removeTeamMemberApi(teamId, userId) {
  return apiRequest(`/teams/${teamId}/members/${userId}`, {
    method: "DELETE",
  });
}

export async function deleteTeamApi(teamId) {
  return apiRequest(`/teams/${teamId}`, {
    method: "DELETE",
  });
}

export async function getTeamInvitesApi(teamId) {
  return apiRequest(`/teams/${teamId}/invites`);
}

export async function acceptTeamInviteApi(teamId, inviteId) {
  return apiRequest(`/teams/${teamId}/invites/${inviteId}/accept`, {
    method: "POST",
  });
}

export async function cancelTeamInviteApi(teamId, inviteId) {
  return apiRequest(`/teams/${teamId}/invites/${inviteId}`, {
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


export const apiRequest = async (endpoint, options = {}) => {
  let token = null;

  try {
    token = localStorage.getItem('accessToken');
  } catch {
    token = null;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  let data;

  if (isJson) {
    data = await response.json();
  } else {
    const text = await response.text();
    throw new Error(
      `API did not return JSON. Status: ${response.status}. Response: ${text.slice(0, 120)}`
    );
  }

  if (!response.ok) {
    const errorMessage = data.message || (typeof data.detail === 'string' ? data.detail : null) || 'Request failed';
    throw new Error(errorMessage);
  }

  return data;
};

export const searchGlobal = async ({ query, projectId }) => {
  const params = new URLSearchParams();
  params.set('q', query);

  if (projectId) {
    params.set('projectId', projectId);
  }

  return apiRequest(`/search?${params.toString()}`);
};

export async function registerApi(payload) {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const result = await parseJsonSafe(response);

  if (!response.ok || !result?.success) {
    throw new Error(result?.message || "Registration failed");
  }

  return result;
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
    name: 'RankCare',
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