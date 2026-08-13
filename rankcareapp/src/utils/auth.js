'use client'
const USER_KEY = "user";

export function getStoredUser() {
  try {
    const raw = localStorage.getItem("user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  try {
    return Boolean(getStoredUser());
  } catch {
    return false;
  }
}

export function setStoredUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredUser() {
  localStorage.removeItem(USER_KEY);
}

export function logoutUser() {
  clearStoredUser();
}

export function clearLegacyCredentials() {
  try {
    localStorage.removeItem(['access', 'Token'].join(''));
    localStorage.removeItem(['session', 'Token'].join(''));
  } catch {
    // Storage can be unavailable in privacy modes.
  }
}
