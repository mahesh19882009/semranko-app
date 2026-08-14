import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

import {
  formatCredits,
  formatInr,
  formatNumber,
  formatPercent,
  formatRankingPosition,
  formatResetDate,
} from '../src/utils/formatters.js';

const source = async (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('formatters preserve values while applying RankCare display conventions', () => {
  assert.equal(formatNumber(1234567), '12,34,567');
  assert.equal(formatInr(999), '₹999');
  assert.equal(formatCredits(20), '20 credits');
  assert.equal(formatPercent(0.125), '12.5%');
  assert.equal(formatPercent(12.5), '12.5%');
  assert.equal(formatRankingPosition(3), '#3');
  assert.equal(formatRankingPosition(null), '—');
  assert.match(formatResetDate('2026-08-14T00:00:00Z'), /14 Aug 2026/);
});

test('theme adapter delegates visual values to CSS custom properties', async () => {
  const theme = await source('src/config/theme.js');
  assert.match(theme, /export const cssVar/);
  assert.match(theme, /var\(--\$\{name\}\)/);
  assert.doesNotMatch(theme, /#[0-9a-f]{3,8}/i);
});

test('Button supports semantic variants and forwards refs for dialog focus', async () => {
  const button = await source('src/components/ui/Button.jsx');
  assert.match(button, /forwardRef\(function Button/);
  assert.match(button, /ref=\{ref\}/);
  assert.match(button, /destructive:/);
  assert.match(button, /aria-busy=\{loading \|\| undefined\}/);
});

test('shared fields generate ids and associate required hints and errors', async () => {
  const input = await source('src/components/ui/Input.jsx');
  assert.match(input, /useId/);
  assert.match(input, /aria-describedby=\{describedBy\}/);
  assert.match(input, /aria-invalid=\{Boolean\(error\) \|\| undefined\}/);
  assert.match(input, /required \? <span/);
  assert.match(input, /role="alert"/);
});

test('dialog foundation handles initial focus, focus restoration, Escape, Tab trapping, and backdrop close', async () => {
  const dialog = await source('src/components/ui/Dialog.jsx');
  assert.match(dialog, /initialFocusRef/);
  assert.match(dialog, /previouslyFocusedRef\.current/);
  assert.match(dialog, /event\.key === 'Escape'/);
  assert.match(dialog, /event\.key !== 'Tab'/);
  assert.match(dialog, /aria-modal="true"/);
  assert.match(dialog, /onMouseDown=\{closeOnBackdrop \? onClose : undefined\}/);

  const modal = await source('src/components/ui/Modal.jsx');
  const confirm = await source('src/components/ConfirmModal.jsx');
  assert.match(modal, /import Dialog/);
  assert.match(confirm, /import Dialog/);
  assert.match(confirm, /initialFocusRef=\{cancelButtonRef\}/);
  assert.match(confirm, /FontAwesomeIcon/);
});

test('shared semantic states and PrimeReact styling contract are available', async () => {
  const badge = await source('src/components/ui/Badge.jsx');
  for (const tone of ['active:', 'inactive:', 'deleted:', 'locked:']) assert.match(badge, new RegExp(tone));

  const stateView = await source('src/components/ui/StateView.jsx');
  for (const component of ['EmptyState', 'ErrorState', 'LoadingState']) assert.match(stateView, new RegExp(`export function ${component}`));

  const css = await source('app/globals.css');
  assert.match(css, /--primary-color: var\(--color-brand-600\)/);
  assert.match(css, /\.compact-datatable/);
  assert.match(css, /\.p-datatable-tbody > tr\.p-highlight/);
});

test('international phone input defaults to India and carries selected country to registration', async () => {
  const phoneInput = await source('src/components/PhoneInput.jsx');
  const register = await source('src/views/RegisterPage.jsx');
  const verifyMobile = await source('src/views/VerifyMobilePage.jsx');
  const api = await source('src/lib/api.js');

  assert.match(phoneInput, /react-international-phone/);
  assert.match(phoneInput, /defaultCountry: 'in'/);
  assert.match(phoneInput, /type="search"/);
  assert.match(phoneInput, /Search country or code/);
  assert.match(phoneInput, /FlagImage/);
  assert.match(phoneInput, /selectedCountry\.iso2\.toUpperCase\(\)/);
  assert.match(register, /mobileCountry/);
  assert.match(register, /<PhoneInput/);
  assert.match(verifyMobile, /mobileVerificationMasked/);
  assert.match(api, /INVALID_MOBILE_NUMBER/);
  assert.match(api, /structuredFieldErrors/);
});
