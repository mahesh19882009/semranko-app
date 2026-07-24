import { apiRequest } from "../../lib/api";

export const fetchPlansApi = async () => {
  const response = await apiRequest("/pricing/plans");
  return response.data || { trialDays: 10, plans: [] };
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
  return response.data || null;
};

export const verifyPaymentApi = async (orderId, paymentId, signature, planId) => {
  const response = await apiRequest(
    `/payments/verify-payment?order_id=${encodeURIComponent(orderId)}&payment_id=${encodeURIComponent(paymentId)}&signature=${encodeURIComponent(signature)}&plan_id=${planId}`,
    {
      method: "POST",
    }
  );
  return response.data || null;
};

export const getSubscriptionStatusApi = async () => {
  const response = await apiRequest("/payments/subscription-status");
  return response.data || null;
};