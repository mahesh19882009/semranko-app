import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { apiRequest } from "../../lib/api";

export const fetchSubscriptionStatus = createAsyncThunk(
  "subscription/fetchStatus",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiRequest("/pricing/subscription-status");
      return response.data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

const subscriptionSlice = createSlice({
  name: "subscription",
  initialState: {
    status: null,
    loading: false,
    error: null,
    data: {
      plan: null,
      effectivePlan: null,
      subscriptionStatus: null,
      trialStartsAt: null,
      trialEndsAt: null,
      gracePeriodEndsAt: null,
      isInGracePeriod: false,
      trialDays: 10,
      usage: {
        projects: 0,
        keywords: 0,
        reportsThisMonth: 0,
        maxCompetitorsPerProject: 0,
      },
      limits: {
        projects: 0,
        keywords: 0,
        competitorsPerProject: 0,
        reportsPerMonth: 0,
        teamMembers: 0,
      },
      creditBalance: 0,
    },
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchSubscriptionStatus.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSubscriptionStatus.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload;
      })
      .addCase(fetchSubscriptionStatus.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export default subscriptionSlice.reducer;
