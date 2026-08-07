'use client'
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import {
  getProfileApi,
  updateProfileApi,
  getGstInfoApi,
  updateGstInfoApi,
  changePasswordApi,
} from "./settingsApi";

export const fetchSettingsProfile = createAsyncThunk(
  "settings/fetchProfile",
  async (_, thunkAPI) => {
    try {
      return await getProfileApi();
    } catch (error) {
      return thunkAPI.rejectWithValue(error.message || "Failed to fetch profile");
    }
  }
);

export const updateSettingsProfile = createAsyncThunk(
  "settings/updateProfile",
  async ({ name }, thunkAPI) => {
    try {
      return await updateProfileApi(name);
    } catch (error) {
      return thunkAPI.rejectWithValue(error.message || "Failed to update profile");
    }
  }
);

export const fetchGstInfo = createAsyncThunk(
  "settings/fetchGstInfo",
  async (_, thunkAPI) => {
    try {
      return await getGstInfoApi();
    } catch (error) {
      return thunkAPI.rejectWithValue(error.message || "Failed to fetch GST info");
    }
  }
);

export const updateGstInfo = createAsyncThunk(
  "settings/updateGstInfo",
  async (payload, thunkAPI) => {
    try {
      return await updateGstInfoApi(payload);
    } catch (error) {
      return thunkAPI.rejectWithValue(error.message || "Failed to update GST info");
    }
  }
);

export const changeSettingsPassword = createAsyncThunk(
  "settings/changePassword",
  async ({ currentPassword, newPassword }, thunkAPI) => {
    try {
      return await changePasswordApi(currentPassword, newPassword);
    } catch (error) {
      return thunkAPI.rejectWithValue(error.message || "Failed to change password");
    }
  }
);

const initialState = {
  profile: null,
  gstInfo: null,
  loadingProfile: false,
  loadingGst: false,
  changingPassword: false,
  updatingProfile: false,
  updatingGst: false,
  error: null,
};

const settingsSlice = createSlice({
  name: "settings",
  initialState,
  reducers: {
    clearSettingsError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSettingsProfile.pending, (state) => {
        state.loadingProfile = true;
        state.error = null;
      })
      .addCase(fetchSettingsProfile.fulfilled, (state, action) => {
        state.loadingProfile = false;
        state.profile = action.payload || null;
      })
      .addCase(fetchSettingsProfile.rejected, (state, action) => {
        state.loadingProfile = false;
        state.error = action.payload || "Failed to fetch profile";
      })
      .addCase(updateSettingsProfile.pending, (state) => {
        state.updatingProfile = true;
        state.error = null;
      })
      .addCase(updateSettingsProfile.fulfilled, (state, action) => {
        state.updatingProfile = false;
        if (state.profile && action.payload) {
          state.profile.name = action.payload.name;
        }
      })
      .addCase(updateSettingsProfile.rejected, (state, action) => {
        state.updatingProfile = false;
        state.error = action.payload || "Failed to update profile";
      })
      .addCase(fetchGstInfo.pending, (state) => {
        state.loadingGst = true;
        state.error = null;
      })
      .addCase(fetchGstInfo.fulfilled, (state, action) => {
        state.loadingGst = false;
        state.gstInfo = action.payload || null;
      })
      .addCase(fetchGstInfo.rejected, (state, action) => {
        state.loadingGst = false;
        state.error = action.payload || "Failed to fetch GST info";
      })
      .addCase(updateGstInfo.pending, (state) => {
        state.updatingGst = true;
        state.error = null;
      })
      .addCase(updateGstInfo.fulfilled, (state, action) => {
        state.updatingGst = false;
        state.gstInfo = action.payload || state.gstInfo;
      })
      .addCase(updateGstInfo.rejected, (state, action) => {
        state.updatingGst = false;
        state.error = action.payload || "Failed to update GST info";
      })
      .addCase(changeSettingsPassword.pending, (state) => {
        state.changingPassword = true;
        state.error = null;
      })
      .addCase(changeSettingsPassword.fulfilled, (state) => {
        state.changingPassword = false;
      })
      .addCase(changeSettingsPassword.rejected, (state, action) => {
        state.changingPassword = false;
        state.error = action.payload || "Failed to change password";
      });
  },
});

export const { clearSettingsError } = settingsSlice.actions;
export default settingsSlice.reducer;
