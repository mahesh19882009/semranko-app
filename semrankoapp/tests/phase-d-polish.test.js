import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = async (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('auth pages use shared accessible form primitives without stale commercial values or emoji controls', async () => {
  const login = await source('src/views/LoginPage.jsx');
  const register = await source('src/views/RegisterPage.jsx');

  for (const page of [login, register]) {
    assert.match(page, /import Input from '\.\.\/components\/ui\/Input'/);
    assert.match(page, /import Button from '\.\.\/components\/ui\/Button'/);
    assert.match(page, /EyeOff/);
    assert.doesNotMatch(page, /👁️|🙈/);
    assert.doesNotMatch(page, /style=\{\{/);
  }
  assert.match(register, /Current plan allowances are shown on the pricing page/);
  assert.doesNotMatch(register, /Includes 1 project, 5 keywords, and 100 spendable credits/);
});

test('canonical billing explains separated credit pools and renders only admin-backed top-up packages', async () => {
  const billing = await source('src/views/CreditManagementPage.jsx');
  const legacyBilling = await source('src/views/BillingPage.jsx');
  assert.match(billing, /fetchTopUpPackagesApi/);
  assert.match(billing, /fetchCurrentPricing/);
  assert.match(billing, /Plan spendable credits/);
  assert.match(billing, /Purchased top-up credits/);
  assert.match(billing, /Automatic tracking reserved/);
  assert.match(billing, /Only active packages configured by your account administrator are shown/);
  assert.doesNotMatch(billing, /600 credits per ₹100/);
  assert.match(legacyBilling, /import CreditManagementPage/);
  assert.doesNotMatch(legacyBilling, /600 credits per ₹100/);
});

test('shared alerts are dismissible when an onDismiss callback is supplied and research uses normalized errors', async () => {
  const alert = await source('src/components/ui/Alert.jsx');
  const research = await source('src/views/KeywordResearchPage.jsx');

  assert.match(alert, /const canDismiss = dismissible \|\| typeof onDismiss === 'function'/);
  assert.match(alert, /border-danger bg-danger-light/);
  assert.match(research, /normalizeApiError\(err, "Unable to research this keyword\."\)/);
  assert.match(research, /role="tablist"/);
  assert.match(research, /aria-selected=/);
});

test('phone country control has a labelled listbox relationship and uses the shared icon system', async () => {
  const phone = await source('src/components/PhoneInput.jsx');
  assert.match(phone, /ChevronDown/);
  assert.match(phone, /aria-controls=/);
  assert.match(phone, /id=\{listboxId\}/);
});
