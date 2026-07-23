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
    technicalHealth: 0,
    backlinks: 0,
    reportsSent: 0,
  },
  rankTrend: [],
  audits: [],
  competitors: [],
  reports: [],
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
      state.audits = [];
      state.competitors = [];
      state.reports = [];
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
        state.stats = action.payload?.stats || initialState.stats;
        state.rankTrend = action.payload?.rankTrend || [];
        state.audits = action.payload?.audits || [];
        state.competitors = action.payload?.competitors || [];
        state.reports = action.payload?.reports || [];
      })
      .addCase(fetchDashboardByProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Failed to load dashboard';
      });
  },
});

export const { setDateRange, resetDashboard } = dashboardSlice.actions;
export default dashboardSlice.reducer;