const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:4000/api';

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
    throw new Error(data.message || 'Request failed');
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