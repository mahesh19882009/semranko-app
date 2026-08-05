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

// Optional: Add a thunk for overview if you want it in Redux, 
// but your component currently fetches it locally. 
// Let's keep it local as per your current pattern to minimize changes.

const initialState = {
  stats: {
    totalKeywords: 0,
    avgRank: 0,
    estimatedTraffic: 0,
  },
  rankTrend: [],
  competitors: [],
  keywords: [],
  keywords_table_rows: [],
  overview: null, // Added for future use if moved from local state
  loading: false,
  error: null,
};

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    resetDashboard(state) {
      state.stats = initialState.stats;
      state.rankTrend = [];
      state.competitors = [];
      state.keywords = [];
      state.keywords_table_rows = [];
      state.overview = null;
      state.loading = false;
      state.error = null;
    },
    setOverview(state, action) {
      state.overview = action.payload;
    }
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
        state.keywords = data.keywords || [];
        state.keywords_table_rows = data.keywords_table_rows || [];
      })
      .addCase(fetchDashboardByProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Failed to load dashboard';
      });
  },
});

export const { resetDashboard, setOverview } = dashboardSlice.actions;
export default dashboardSlice.reducer;