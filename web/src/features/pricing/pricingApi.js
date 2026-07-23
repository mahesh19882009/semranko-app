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