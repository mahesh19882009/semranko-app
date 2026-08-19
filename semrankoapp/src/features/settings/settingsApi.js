'use client'
import { apiRequest, API_BASE_URL } from "../../lib/api";

export const getProfileApi = async () => {
  const response = await apiRequest("/settings/profile");
  return response.data || null;
};

export const updateProfileApi = async (name) => {
  const response = await apiRequest("/settings/profile", {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
  return response.data || null;
};

export const getGstInfoApi = async () => {
  const response = await apiRequest("/settings/gst");
  return response.data || null;
};

export const updateGstInfoApi = async (payload) => {
  const response = await apiRequest("/settings/gst", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.data || null;
};

export const changePasswordApi = async (currentPassword, newPassword) => {
  const response = await apiRequest("/settings/change-password", {
    method: "POST",
    body: JSON.stringify({ currentPassword, newPassword }),
  });
  return response.data || null;
};
