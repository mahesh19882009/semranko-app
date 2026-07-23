import { createSelector } from '@reduxjs/toolkit';

const selectDashboard = (state) => state.dashboard;
const selectProjects = (state) => state.projects;

export const selectDateRange = (state) => selectDashboard(state).dateRange;
export const selectDashboardError = (state) => selectDashboard(state).error || null;
export const selectDashboardLoading = (state) => selectDashboard(state).loading || false;
export const selectAuditsRaw = (state) => {
  const value = selectDashboard(state).audits;
  return Array.isArray(value) ? value : value?.items || [];
};

export const selectCompetitorsRaw = (state) => {
  const value = selectDashboard(state).competitors;
  return Array.isArray(value) ? value : value?.items || [];
};

export const selectReportsRaw = (state) => {
  const value = selectDashboard(state).reports;
  return Array.isArray(value) ? value : value?.items || [];
};
export const selectRankTrendRaw = (state) => selectDashboard(state).rankTrend || [];
export const selectGlobalStats = (state) => selectDashboard(state).stats || {};

export const selectProjectsList = (state) => selectProjects(state).list || [];
export const selectSelectedProjectId = (state) => selectProjects(state).selectedProjectId || null;

export const selectSelectedProject = createSelector(
  [selectProjectsList, selectSelectedProjectId],
  (projects, selectedProjectId) =>
    projects.find((item) => item.id === selectedProjectId) || null
);

export const selectRangeDays = createSelector([selectDateRange], (dateRange) => {
  if (dateRange === 'Last 30 days') return 30;
  if (dateRange === 'Last 90 days') return 90;
  return 7;
});

export const selectStats = createSelector(
  [selectSelectedProject, selectGlobalStats, selectRangeDays, selectDateRange],
  (project, globalStats, rangeDays, dateRange) => {
    const projectName = project?.name || '';

    const baseStats = {
      totalKeywords: project?.keywordCount ?? 0,
      avgRank: project?.avgRank ?? 0,
      estimatedTraffic: project?.estimatedTraffic ?? 0,
      technicalHealth: project?.technicalHealth ?? 0,
      backlinks: project?.backlinks ?? 0,
      reportsSent: project?.reportsSent ?? 0,
    };

    const hasProjectScopedData =
      baseStats.totalKeywords > 0 ||
      baseStats.avgRank > 0 ||
      baseStats.estimatedTraffic > 0 ||
      baseStats.technicalHealth > 0 ||
      baseStats.backlinks > 0 ||
      baseStats.reportsSent > 0;

    const fallbackStats = project
      ? {
          totalKeywords: Math.max(0, project?.keywords?.length || 0),
          avgRank: projectName ? 18.4 : 0,
          estimatedTraffic: projectName ? 1240 : 0,
          technicalHealth: projectName ? 76 : 0,
          backlinks: projectName ? 148 : 0,
          reportsSent: 0,
        }
      : {
          totalKeywords: globalStats.totalKeywords ?? 0,
          avgRank: globalStats.avgRank ?? 0,
          estimatedTraffic: globalStats.estimatedTraffic ?? 0,
          technicalHealth: globalStats.technicalHealth ?? 0,
          backlinks: globalStats.backlinks ?? 0,
          reportsSent: globalStats.reportsSent ?? 0,
        };

    const stats = hasProjectScopedData ? baseStats : fallbackStats;

    let scaledStats = stats;

    if (rangeDays === 7) {
      scaledStats = {
        ...stats,
        estimatedTraffic: Math.round(stats.estimatedTraffic * 0.25),
        backlinks: Math.round(stats.backlinks * 0.2),
        reportsSent: Math.max(0, Math.round(stats.reportsSent * 0.25)),
      };
    } else if (rangeDays === 30) {
      scaledStats = {
        ...stats,
        estimatedTraffic: Math.round(stats.estimatedTraffic * 0.7),
        backlinks: Math.round(stats.backlinks * 0.55),
        reportsSent: Math.max(0, Math.round(stats.reportsSent * 0.7)),
      };
    }

    return {
      ...scaledStats,
      totalKeywordsHint: project
        ? `Tracked terms for ${project.name}`
        : `Across the selected range: ${dateRange}`,
      avgRankHint: project
        ? `Current average position for ${project.name}`
        : `Updated for ${dateRange.toLowerCase()}`,
      estimatedTrafficHint: project
        ? `Estimated organic visits for ${project.name}`
        : 'Projected organic sessions',
      technicalHealthHint: project
        ? `Technical site health score`
        : 'Audit and crawl quality signals',
      backlinksHint: project
        ? `Tracked referring links for ${project.name}`
        : `Visible for ${dateRange.toLowerCase()}`,
      reportsSentHint: project
        ? `Reports generated for ${project.name}`
        : `Based on ${dateRange.toLowerCase()}`,
    };
  }
);

export const selectRankTrend = createSelector(
  [selectSelectedProject, selectRankTrendRaw, selectRangeDays],
  (project, globalTrend, rangeDays) => {
    const projectTrend = project?.rankTrend;

    if (Array.isArray(projectTrend) && projectTrend.length > 0) {
      return projectTrend.slice(-Math.min(rangeDays, projectTrend.length));
    }

    if (project) {
      const points = Math.min(rangeDays, 12);
      return Array.from({ length: points }, (_, index) => ({
        label: `P${index + 1}`,
        value: Math.max(1, 24 - index),
      }));
    }

    return globalTrend.slice(-Math.min(rangeDays, globalTrend.length));
  }
);

export const selectAudits = createSelector(
  [selectSelectedProject, selectAuditsRaw],
  (project, globalAudits) => {
    if (Array.isArray(project?.audits) && project.audits.length > 0) {
      return project.audits;
    }

    if (project) {
      return [
        { label: 'Issues found', value: 0 },
        { label: 'Warnings', value: 0 },
        { label: 'Passed checks', value: 0 },
      ];
    }

    return globalAudits;
  }
);

export const selectCompetitors = createSelector(
  [selectSelectedProject, selectCompetitorsRaw],
  (project, globalCompetitors) => {
    const projectCompetitors = Array.isArray(project?.competitors)
      ? project.competitors
      : project?.competitors?.items || [];

    if (projectCompetitors.length > 0) {
      return projectCompetitors;
    }

    return globalCompetitors;
  }
);

// export const selectReports = createSelector(
//   [selectSelectedProject, selectReportsRaw, selectRangeDays],
//   (project, globalReports, rangeDays) => {
//     const projectReports = Array.isArray(project?.reports)
//       ? project.reports
//       : project?.reports?.items || [];

//     const reportsSource =
//       projectReports.length > 0 ? projectReports : globalReports;

//     if (rangeDays === 7) {
//       if (rangeDays === 7) {
//         return reportsSource.filter(
//           (report) => String(report.status || '').toLowerCase() === 'active'
//         );
//       }
//     }

//     if (rangeDays === 30) {
//       return reportsSource.slice(0, Math.min(3, reportsSource.length));
//     }

//     return reportsSource;
//   }
// );

export const selectReports = createSelector(
  [selectReportsRaw, selectRangeDays],
  (globalReports, rangeDays) => {
    const reportsSource = Array.isArray(globalReports) ? globalReports : [];

    if (rangeDays === 7) {
      return reportsSource.filter(
        (report) => String(report.status || '').toLowerCase() === 'active'
      );
    }

    if (rangeDays === 30) {
      return reportsSource.slice(0, Math.min(3, reportsSource.length));
    }

    return reportsSource;
  }
);

export const selectHasSelectedProjectData = createSelector(
  [selectSelectedProject, selectCompetitors, selectReports, selectRankTrend, selectStats],
  (project, competitors, reports, rankTrend, stats) => {
    if (!project) return false;

    return (
      stats.totalKeywords > 0 ||
      stats.estimatedTraffic > 0 ||
      competitors.length > 0 ||
      reports.length > 0 ||
      rankTrend.length > 0
    );
  }
);
