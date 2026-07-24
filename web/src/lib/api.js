const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:4000/api';

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

  const razorpayOptions = {
    key: key_id,
    amount: amount,
    currency: currency,
    name: 'RankCare',
    description: 'SEO Rank Tracking Subscription',
    order_id: order_id,
    handler: function (response) {
      // Payment successful
      onPaymentSuccess(response);
    },
    prefill: {
      name: '',
      email: '',
      contact: '',
    },
    theme: {
      color: '#4F46E5',
    },
    modal: {
      ondismiss: function () {
        if (onPaymentError) {
          onPaymentError({ error: { description: 'Payment cancelled by user' } });
        }
      },
    },
  };

  const rzp = new window.Razorpay(razorpayOptions);
  
  rzp.on('payment.failed', function (response) {
    if (onPaymentError) {
      onPaymentError(response.error);
    }
  });

  rzp.open();
  
  return rzp;
}