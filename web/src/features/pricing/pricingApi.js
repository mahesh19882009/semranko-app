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
  // Backend returns the order data directly (not wrapped in { success, message, data })
  return response || null;
};

export const verifyPaymentApi = async (orderId, paymentId, signature, planId) => {
  const response = await apiRequest("/payments/verify-payment", {
    method: "POST",
    body: JSON.stringify({
      razorpay_order_id: orderId,
      razorpay_payment_id: paymentId,
      razorpay_signature: signature,
      plan_id: planId,
    }),
  });
  return response || null;
};

export const getSubscriptionStatusApi = async () => {
  const response = await apiRequest("/payments/subscription-status");
  return response.data || null;
};