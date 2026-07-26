import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import {
  changePlanApi,
  checkPlanChangeApi,
  fetchCurrentPricingApi,
  fetchPlansApi,
} from "./pricingApi";

export const fetchPricingPlans = createAsyncThunk(
  "pricing/fetchPlans",
  async (_, thunkAPI) => {
    try {
      return await fetchPlansApi();
    } catch (error) {
      return thunkAPI.rejectWithValue(error.message || "Failed to fetch plans");
    }
  }
);

export const fetchCurrentPricing = createAsyncThunk(
  "pricing/fetchCurrent",
  async (_, thunkAPI) => {
    try {
      return await fetchCurrentPricingApi();
    } catch (error) {
      return thunkAPI.rejectWithValue(error.message || "Failed to fetch current pricing");
    }
  }
);

export const checkPlanChange = createAsyncThunk(
  "pricing/checkPlanChange",
  async (plan, thunkAPI) => {
    try {
      const result = await checkPlanChangeApi(plan);
      return { plan, result };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        plan,
        message: error.message || "Failed to validate plan change",
      });
    }
  }
);

export const changePlan = createAsyncThunk(
  "pricing/changePlan",
  async (plan, thunkAPI) => {
    try {
      const result = await changePlanApi(plan);
      return result;
    } catch (error) {
      return thunkAPI.rejectWithValue({
        message: error.message || "Failed to change plan",
        data: error.data || null,
      });
    }
  }
);

const initialState = {
  plans: [],
  current: null,
  trialDays: 10,
  loadingPlans: false,
  loadingCurrent: false,
  changingPlan: false,
  error: null,
  changePlanValidation: {},
};

const pricingSlice = createSlice({
  name: "pricing",
  initialState,
  reducers: {
    clearPricingError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPricingPlans.pending, (state) => {
        state.loadingPlans = true;
        state.error = null;
      })
       .addCase(fetchPricingPlans.fulfilled, (state, action) => {
         state.loadingPlans = false;
         state.plans = action.payload?.data || [];
         state.trialDays = action.payload?.trialDays || 10;
      })
      .addCase(fetchPricingPlans.rejected, (state, action) => {
        state.loadingPlans = false;
        state.error = action.payload || "Failed to fetch plans";
      })
      .addCase(fetchCurrentPricing.pending, (state) => {
        state.loadingCurrent = true;
        state.error = null;
      })
      .addCase(fetchCurrentPricing.fulfilled, (state, action) => {
        state.loadingCurrent = false;
        state.current = action.payload || null;
      })
      .addCase(fetchCurrentPricing.rejected, (state, action) => {
        state.loadingCurrent = false;
        state.error = action.payload || "Failed to fetch current pricing";
      })
      .addCase(checkPlanChange.fulfilled, (state, action) => {
        state.changePlanValidation[action.payload.plan] = action.payload.result;
      })
      .addCase(checkPlanChange.rejected, (state, action) => {
        const plan = action.payload?.plan;
        if (plan) {
          state.changePlanValidation[plan] = {
            allowed: false,
            violations: [],
            message: action.payload?.message || "Failed to validate plan change",
          };
        }
      })
      .addCase(changePlan.pending, (state) => {
        state.changingPlan = true;
        state.error = null;
      })
      .addCase(changePlan.fulfilled, (state, action) => {
        state.changingPlan = false;
        state.current = action.payload || null;
      })
      .addCase(changePlan.rejected, (state, action) => {
        state.changingPlan = false;
        state.error = action.payload?.message || "Failed to change plan";
      });
  },
});

export const { clearPricingError } = pricingSlice.actions;
export default pricingSlice.reducer;