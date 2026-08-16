'use client'
import { configureStore } from '@reduxjs/toolkit';
import dashboardReducer from '../features/dashboard/dashboardSlice';
import projectsReducer from '../features/projects/projectsSlice';
import keywordsReducer from '../features/keywords/keywordsSlice';
import pricingReducer from '../features/pricing/pricingSlice';
import subscriptionReducer from '../features/subscription/subscriptionSlice';
import settingsReducer from '../features/settings/settingsSlice';
import authReducer from '../features/auth/authSlice';

export const store = configureStore({
  reducer: {
    dashboard: dashboardReducer,
    projects: projectsReducer,
    keywords: keywordsReducer,
    pricing: pricingReducer,
    subscription: subscriptionReducer,
    settings: settingsReducer,
    auth: authReducer,
  }
});
