import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = async (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('public layout contains full navigation, responsive menu, and legal footer links', async () => {
  const layout = await source('src/components/PublicLayout.jsx');
  for (const route of ['/features', '/pricing', '/about', '/faq', '/contact', '/privacy', '/terms', '/refund-policy']) assert.match(layout, new RegExp(route.replace('/', '\\/')));
  assert.match(layout, /menuOpen/);
  assert.match(layout, /aria-expanded=\{menuOpen\}/);
  assert.match(layout, /lg:hidden/);
});

test('public content avoids fake social proof and identifies illustrative product visuals', async () => {
  const home = await source('src/views/HomePage.jsx');
  assert.match(home, /Illustrative interface/);
  assert.match(home, /does not present this as dedicated historical AIO reporting/);
  assert.doesNotMatch(home, /trusted by|customers|testimonials|rating/i);
});

test('pricing exposes currency and billing toggles with annual eleven-month messaging and custom contact sales', async () => {
  const pricing = await source('src/views/PricingPage.jsx');
  assert.match(pricing, /options=\{\['INR', 'USD'\]\}/);
  assert.match(pricing, /options=\{\['monthly', 'yearly'\]\}/);
  assert.match(pricing, /12 months for the price of 11/);
  assert.match(pricing, /USD checkout is not available yet/);
  assert.match(pricing, /Custom pricing/);
  assert.match(pricing, /Contact sales/);
  assert.match(pricing, /Manual Refresh unavailable/);
  assert.match(pricing, /Check, Minus/);
});

test('SEO and public legal route foundations are present', async () => {
  const rootLayout = await source('app/layout.jsx');
  const robots = await source('app/robots.js');
  const sitemap = await source('app/sitemap.js');
  const legal = await source('src/content/public.js');
  assert.match(rootLayout, /metadataBase/);
  assert.match(robots, /sitemap/);
  assert.match(sitemap, /refund-policy/);
  assert.match(legal, /requires legal review/);
});
