'use client'
import { apiRequest } from "../../lib/api";

export const fetchPlansApi = async () => {
  const response = await apiRequest("/pricing/plans");
  return response || { success: true, data: [], message: "Plans fetched" };
};

export const fetchCurrentPricingApi = async () => {
  const response = await apiRequest("/pricing/current");
  return response.data || null;
};

export const checkPlanChangeApi = async (plan) => {
  const response = await apiRequest(`/pricing/downgrade-check?plan=${encodeURIComponent(plan)}`);
  return response.data || null;
};

export const changePlanApi = async (plan) => {
  const response = await apiRequest("/pricing/change-plan", {
    method: "POST",
    body: JSON.stringify({ plan }),
  });
  return response.data || null;
};

// Payment APIs
export const createPaymentOrderApi = async (planId, amount) => {
  const response = await apiRequest(`/payments/create-order?plan_id=${planId}&amount=${amount}`, {
    method: "POST",
  });
  // Backend returns the order data directly (not wrapped in { success, message, data })
  return response || null;
};

export const verifyPaymentApi = async (orderId, paymentId, signature, planId, creditApplied = 0) => {
  const response = await apiRequest("/payments/verify-payment", {
    method: "POST",
    body: JSON.stringify({
      razorpay_order_id: orderId,
      razorpay_payment_id: paymentId,
      razorpay_signature: signature,
      plan_id: planId,
      credit_applied: creditApplied,
    }),
  });
  return response || null;
};

export const getSubscriptionStatusApi = async () => {
  const response = await apiRequest("/payments/subscription-status");
  return response.data || null;
};

export const fetchInvoicesApi = async () => {
  const response = await apiRequest("/payments/invoices");
  return response.data || { invoices: [], credit_balance: 0 };
};

export const markPaymentFailedApi = async (orderId) => {
  const response = await apiRequest("/payments/mark-failed", {
    method: "POST",
    body: JSON.stringify({ razorpay_order_id: orderId }),
  });
  return response || null;
};

export const createCreditPurchaseOrderApi = async (credits) => {
  const response = await apiRequest("/billing/credit-purchase-order", {
    method: "POST",
    body: JSON.stringify({ credits }),
  });
  return response.data || null;
};

export const fetchCreditBalanceApi = async () => {
  const response = await apiRequest("/billing/credits/balance");
  return response.data || null;
};

export const verifyCreditPaymentApi = async (orderId, paymentId, signature) => {
  const response = await apiRequest("/billing/verify-credit-payment", {
    method: "POST",
    body: JSON.stringify({
      razorpay_order_id: orderId,
      razorpay_payment_id: paymentId,
      razorpay_signature: signature,
    }),
  });
  return response.data || null;
};

export const getBillingHistoryApi = async () => {
  const response = await apiRequest("/billing/history");
  return response || { history: [] };
};

export const downloadInvoiceApi = async (ledgerId) => {
  const token = localStorage.getItem('accessToken');
  const url = `${API_BASE_URL}/billing/invoice/${encodeURIComponent(ledgerId)}/download`;
  const response = await fetch(url, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Failed to download invoice (${response.status})`);
  }

  return response.blob();
};

export const createTeamApi = async (name) => {
  const response = await apiRequest('/teams/', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
  return response.data || null;
};

export const listTeamsApi = async () => {
  const response = await apiRequest('/teams/');
  return response.data || { teams: [] };
};

export const getTeamApi = async (teamId) => {
  const response = await apiRequest(`/teams/${encodeURIComponent(teamId)}`);
  return response.data || null;
};

export const addTeamMemberApi = async (teamId, email, role = 'Viewer') => {
  const response = await apiRequest(`/teams/${encodeURIComponent(teamId)}/members`, {
    method: 'POST',
    body: JSON.stringify({ email, role }),
  });
  return response.data || null;
};

export const updateTeamMemberRoleApi = async (teamId, userId, role) => {
  const response = await apiRequest(`/teams/${encodeURIComponent(teamId)}/members/${encodeURIComponent(userId)}`, {
    method: 'PUT',
    body: JSON.stringify({ role }),
  });
  return response.data || null;
};

export const removeTeamMemberApi = async (teamId, userId) => {
  const response = await apiRequest(`/teams/${encodeURIComponent(teamId)}/members/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
  return response.data || null;
};

export const exportProjectReportApi = async (projectId, payload) => {
  const response = await apiRequest(`/projects/${projectId}/export-report`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return response.data || null;
};

export const toggleTrackedKeywordAioApi = async (keywordId) => {
  const response = await apiRequest(`/tracked-keywords/toggle-aio/${encodeURIComponent(keywordId)}`, {
    method: 'POST',
  });
  return response.data || null;
};

export const bulkToggleTrackedKeywordAioApi = async (keywordIds, targetAio) => {
  const response = await apiRequest('/tracked-keywords/toggle-aio-bulk', {
    method: 'POST',
    body: JSON.stringify({ keyword_ids: keywordIds, target_aio: targetAio }),
  });
  return response.data || null;
};

export const getUsageLogApi = async (page = 1, limit = 20, actionType = null) => {
  const params = new URLSearchParams();
  params.set('page', String(page));
  params.set('limit', String(limit));
  if (actionType) params.set('action_type', actionType);
  const response = await apiRequest(`/billing/usage-log?${params.toString()}`);
  return response.data || null;
};
