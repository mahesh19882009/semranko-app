'use client'
import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { apiRequest, toRejectedValue } from "../../lib/api";

export const fetchSubscriptionStatus = createAsyncThunk(
  "subscription/fetchStatus",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiRequest("/pricing/subscription-status");
      return response.data;
    } catch (error) {
      return rejectWithValue(toRejectedValue(error, "Failed to fetch subscription status."));
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
      pendingPlanChange: null,
      trialStartsAt: null,
      trialEndsAt: null,
      gracePeriodEndsAt: null,
      isInGracePeriod: false,
      trialDays: 0,
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
      },
      creditBalance: 0,
      totalMonthlyAllocation: 0,
      spendableCreditsRemaining: 0,
      planSpendableCreditsRemaining: 0,
      purchasedCreditsRemaining: 0,
      automaticReservedAllocation: 0,
      automaticReservedRemaining: 0,
      nextCreditResetAt: null,
      featureUsage: {},
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
