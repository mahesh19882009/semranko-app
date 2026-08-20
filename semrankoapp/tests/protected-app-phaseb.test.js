import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = async (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('protected shell supplies responsive navigation and canonical billing access', async () => {
  const appLayout = await source('src/components/AppLayout.jsx');
  const sidebar = await source('src/components/SideBar.jsx');
  const topbar = await source('src/components/TopBar.jsx');
  const billingCompatibility = await source('app/(auth)/dashboard/billing/page.jsx');

  assert.match(appLayout, /mobileNavigationOpen/);
  assert.match(appLayout, /event\.key === 'Escape'/);
  assert.match(sidebar, /aria-label="Close navigation"/);
  assert.match(sidebar, /lg:hidden/);
  assert.match(sidebar, /to: '\/billing'/);
  assert.match(topbar, /navigate\('\/billing'\)/);
  assert.match(billingCompatibility, /redirect\('\/billing'\)/);
});

test('dashboard uses account-wide data with independent loading states', async () => {
  const dashboard = await source('src/views/DashboardPage.jsx');
  assert.match(dashboard, /apiRequest\('\/dashboard\/overview'\)/);
  assert.match(dashboard, /overviewLoading/);
  assert.match(dashboard, /pricingLoading/);
  assert.match(dashboard, /Historical movement is not displayed/);
  assert.match(dashboard, /projects_count/);
  assert.doesNotMatch(dashboard, /fetchDashboardData/);
});

test('project and keyword pages keep real counts and selected-project table controls', async () => {
  const projects = await source('src/views/ProjectsPage.jsx');
  const projectCard = await source('src/components/ProjectCard.jsx');
  const keywords = await source('src/views/KeywordsPage.jsx');

  assert.match(projects, /COUNTRY_LOCATION_CODES, getCountryCode/);
  assert.match(projectCard, /project\.keywordCount/);
  assert.match(projectCard, /keywordCount === 1 \? 'keyword' : 'keywords'/);
  assert.match(keywords, /keywords\/\$\{selectedProjectId\}\/table/);
  assert.match(keywords, /aria-label="Keyword table\. Scroll horizontally/);
  assert.match(keywords, /bg-surface-subtle/);
  assert.match(keywords, /variant="danger"/);
  assert.match(keywords, /Activate this keyword before refreshing it\./);
});

test('keyword table shows available values during processing and only shimmers missing values', async () => {
  const keywords = await source('src/views/KeywordsPage.jsx');

  assert.match(
    keywords,
    /if \(hasValue\) \{\s*return formatter\(value\);/
  );

  assert.match(
    keywords,
    /if \(isRowProcessing\(rowData\)\) \{\s*return <Shimmer width=\{width\} \/>;/
  );

  assert.match(
    keywords,
    /if \(rowData\.position && rowData\.position > 0\)/
  );

  assert.match(
    keywords,
    /if \(rowData\.localPackPosition && rowData\.localPackPosition > 0\)/
  );
});

test('keyword SSE completion clears only the completed processing keyword', async () => {
  const keywords = await source('src/views/KeywordsPage.jsx');

  assert.match(
    keywords,
    /JSON\.parse\(event\.data \|\| '\{\}'\)/
  );

  assert.match(
    keywords,
    /payload\.keyword/
  );

  assert.match(
    keywords,
    /setProcessingJobs\(\(current\) =>/
  );

  assert.doesNotMatch(
    keywords,
    /PostgreSQL now contains the completed SERP result\.\s*setProcessingJobs\(\[\]\)/
  );
});

