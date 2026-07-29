import { configureStore } from '@reduxjs/toolkit';
import dashboardReducer from '../features/dashboard/dashboardSlice';
import projectsReducer from '../features/projects/projectsSlice';
import keywordsReducer from '../features/keywords/keywordsSlice';
import competitorsReducer from '../features/competitors/competitorsSlice';
import auditReducer from '../features/audit/auditSlice';
import reportReducer from '../features/reports/reportSlice';
import settingsReducer from "../features/settings/settingsSlice";
import notificationsReducer from '../features/notifications/notificationsSlice';
import searchReducer from '../features/search/searchSlice';
import pricingReducer from '../features/pricing/pricingSlice';

export const store = configureStore({
  reducer: {
    dashboard: dashboardReducer,
    projects: projectsReducer,
    keywords: keywordsReducer,
    competitors: competitorsReducer,
    audit: auditReducer,
    reports: reportReducer,
    settings: settingsReducer,
    notifications: notificationsReducer,
    search: searchReducer,
    pricing: pricingReducer,
  }
});
