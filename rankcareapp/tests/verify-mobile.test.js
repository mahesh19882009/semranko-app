import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = async (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('VerifyMobile uses state-backed masked mobile and initial OTP error', async () => {
  const page = await source('src/views/VerifyMobilePage.jsx');

  assert.match(page, /const \[maskedMobile, setMaskedMobile\] = useState\(/);
  assert.match(page, /const \[initialOtpError, setInitialOtpError\] = useState\(/);
  assert.match(page, /sessionStorage\.getItem\('mobileVerificationMasked'\)/);
  assert.match(page, /sessionStorage\.getItem\('mobileVerificationOtpError'\)/);
});

test('VerifyMobile starts server-authoritative cooldown on mount and on resend success', async () => {
  const page = await source('src/views/VerifyMobilePage.jsx');

  assert.match(page, /const \[resendCooldown, setResendCooldown\] = useState\(0\)/);
  assert.match(page, /RESEND_COOLDOWN_SECONDS = 60/);
  assert.match(page, /RESEND_COOLDOWN_KEY = 'mobileResendCooldownUntil'/);
  assert.match(page, /function formatCountdown\(seconds\)/);
  assert.match(page, /Resend code in \${formatCountdown\(resendCooldown\)}/);
  assert.match(page, /const resendDisabled = loading \|\| resendCooldown > 0/);
  assert.match(page, /startCooldown\(RESEND_COOLDOWN_SECONDS\)/);
  assert.match(page, /Number\(normalized\.retryAfter\) \|\| RESEND_COOLDOWN_SECONDS/);
});

test('VerifyMobile resend success updates masked mobile without runtime errors', async () => {
  const page = await source('src/views/VerifyMobilePage.jsx');

  assert.match(page, /const refreshedMask = result\?\.data\?\.masked_mobile;/);
  assert.match(page, /if \(refreshedMask\) \{/);
  assert.match(page, /setMaskedMobile\(refreshedMask\);/);
  assert.match(page, /sessionStorage\.setItem\('mobileVerificationMasked', refreshedMask\);/);
  assert.match(page, /sessionStorage\.removeItem\('mobileVerificationOtpError'\);/);
  assert.match(page, /setInitialOtpError\(null\);/);
});

test('VerifyMobile verification success clears cooldown and session state', async () => {
  const page = await source('src/views/VerifyMobilePage.jsx');

  assert.match(page, /sessionStorage\.removeItem\('mobileVerificationToken'\);/);
  assert.match(page, /sessionStorage\.removeItem\('mobileVerificationMasked'\);/);
  assert.match(page, /clearCooldown\(\);/);
});

test('RegisterPage stores masked mobile from the actual registration response shape', async () => {
  const page = await source('src/views/RegisterPage.jsx');

  assert.match(page, /result\?\.data\?\.mobileOtp\?\.maskedMobile/);
  assert.ok(!/result\?\.data\?\.mobileMasked/.test(page), 'RegisterPage should not read result.data.mobileMasked');
});
