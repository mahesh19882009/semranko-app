import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = async (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('public auth checks keep stable navigation dependencies across form rerenders', async () => {
  const navigation = await source('src/lib/navigation.jsx');
  const login = await source('src/views/LoginPage.jsx');
  const register = await source('src/views/RegisterPage.jsx');

  assert.match(navigation, /import \{ useCallback, useEffect/);
  assert.match(navigation, /return useCallback\(\(to, options\) => \{/);
  assert.match(navigation, /\}, \[router\]\)/);
  assert.match(login, /ensureNotAuthenticated/);
  assert.match(login, /\}, \[navigate, from\]\);/);
  assert.match(register, /ensureNotAuthenticated/);
  assert.match(register, /\}, \[navigate\]\);/);
});

test('registration and mobile verification communicate OTP dispatch failures truthfully', async () => {
  const register = await source('src/views/RegisterPage.jsx');
  const verifyMobile = await source('src/views/VerifyMobilePage.jsx');
  const api = await source('src/lib/api.js');

  assert.match(register, /mobileOtp\?\.requested === false/);
  assert.match(register, /mobileVerificationOtpError/);
  assert.match(verifyMobile, /initialOtpError/);
  assert.match(verifyMobile, /mobileVerificationOtpError/);
  assert.match(api, /OTP_PROVIDER_UNAVAILABLE/);
});

test('auth initialization is deduplicated through a shared module-level cache', async () => {
  const authInit = await source('src/lib/auth-init.js');
  assert.match(authInit, /let authInitPromise = null/);
  assert.match(authInit, /export async function ensureNotAuthenticated/);
  assert.match(authInit, /if \(authInitPromise\) \{/);
  assert.match(authInit, /authInitPromise = apiRequest\('\/auth\/me'\)/);
  assert.match(authInit, /export function clearAuthInitCache/);
});
