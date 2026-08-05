'use client'
import { configureStore } from '@reduxjs/toolkit';
import dashboardReducer from '../features/dashboard/dashboardSlice';
import projectsReducer from '../features/projects/projectsSlice';
import keywordsReducer from '../features/keywords/keywordsSlice';
import competitorsReducer from '../features/competitors/competitorsSlice';
import pricingReducer from '../features/pricing/pricingSlice';
import subscriptionReducer from '../features/subscription/subscriptionSlice';

export const store = configureStore({
  reducer: {
    dashboard: dashboardReducer,
    projects: projectsReducer,
    keywords: keywordsReducer,
    competitors: competitorsReducer,
    pricing: pricingReducer,
    subscription: subscriptionReducer,
  }
});
