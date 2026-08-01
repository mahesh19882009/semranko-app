'use client'
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { apiRequest } from '../../lib/api';

export const fetchDashboardByProject = createAsyncThunk(
  'dashboard/fetchByProject',
  async (projectId, { rejectWithValue }) => {
    try {
      const response = await apiRequest(`/dashboard/${projectId}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to fetch dashboard');
    }
  }
);

const initialState = {
  stats: {
    totalKeywords: 0,
    avgRank: 0,
    estimatedTraffic: 0,
  },
  rankTrend: [],
  competitors: [],
  dateRange: 'Last 7 days',
  loading: false,
  error: null,
};

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    setDateRange(state, action) {
      state.dateRange = action.payload;
    },
    resetDashboard(state) {
      state.stats = initialState.stats;
      state.rankTrend = [];
      state.competitors = [];
      state.loading = false;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboardByProject.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboardByProject.fulfilled, (state, action) => {
        state.loading = false;
        state.error = null;
        const data = action.payload || {};
        state.stats = data.stats || initialState.stats;
        state.rankTrend = data.rankTrend || [];
        state.competitors = data.competitors?.items || [];
      })
      .addCase(fetchDashboardByProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Failed to load dashboard';
      });
  },
});

export const { setDateRange, resetDashboard } = dashboardSlice.actions;
export default dashboardSlice.reducer;
