import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { apiRequest } from "../../lib/api";

const initialState = {
  settings: null,
  loading: false,
  profileLoading: false,
  notificationsLoading: false,
  passwordLoading: false,
  error: null,
  successMessage: null,
};

export const fetchMySettings = createAsyncThunk(
  "settings/fetchMySettings",
  async (_, thunkAPI) => {
    try {
      const response = await apiRequest("/settings/me");
      return response.data;
    } catch (error) {
      return thunkAPI.rejectWithValue(
        error?.message || "Failed to fetch settings"
      );
    }
  }
);

export const updateProfile = createAsyncThunk(
  "settings/updateProfile",
  async (payload, thunkAPI) => {
    try {
      const response = await apiRequest("/settings/profile", {
        method: "PUT",
        body: JSON.stringify(payload),
      });

      return {
        data: response.data,
        message: response.message || "Profile updated successfully",
      };
    } catch (error) {
      return thunkAPI.rejectWithValue(
        error?.message || "Failed to update profile"
      );
    }
  }
);

export const updateNotifications = createAsyncThunk(
  "settings/updateNotifications",
  async (payload, thunkAPI) => {
    try {
      const response = await apiRequest("/settings/notifications", {
        method: "PUT",
        body: JSON.stringify(payload),
      });

      return {
        data: response.data,
        message: response.message || "Notification settings updated successfully",
      };
    } catch (error) {
      return thunkAPI.rejectWithValue(
        error?.message || "Failed to update notifications"
      );
    }
  }
);

export const updatePassword = createAsyncThunk(
  "settings/updatePassword",
  async (payload, thunkAPI) => {
    try {
      const response = await apiRequest("/settings/password", {
        method: "PUT",
        body: JSON.stringify(payload),
      });

      return {
        message: response.message || "Password updated successfully",
      };
    } catch (error) {
      return thunkAPI.rejectWithValue(
        error?.message || "Failed to update password"
      );
    }
  }
);

const settingsSlice = createSlice({
  name: "settings",
  initialState,
  reducers: {
    clearSettingsMessages: (state) => {
      state.error = null;
      state.successMessage = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMySettings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchMySettings.fulfilled, (state, action) => {
        state.loading = false;
        state.settings = action.payload;
      })
      .addCase(fetchMySettings.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      .addCase(updateProfile.pending, (state) => {
        state.profileLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(updateProfile.fulfilled, (state, action) => {
        state.profileLoading = false;
        state.settings = action.payload.data;
        state.successMessage = action.payload.message;
      })
      .addCase(updateProfile.rejected, (state, action) => {
        state.profileLoading = false;
        state.error = action.payload;
      })

      .addCase(updateNotifications.pending, (state) => {
        state.notificationsLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(updateNotifications.fulfilled, (state, action) => {
        state.notificationsLoading = false;
        state.settings = action.payload.data;
        state.successMessage = action.payload.message;
      })
      .addCase(updateNotifications.rejected, (state, action) => {
        state.notificationsLoading = false;
        state.error = action.payload;
      })

      .addCase(updatePassword.pending, (state) => {
        state.passwordLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(updatePassword.fulfilled, (state, action) => {
        state.passwordLoading = false;
        state.successMessage = action.payload.message;
      })
      .addCase(updatePassword.rejected, (state, action) => {
        state.passwordLoading = false;
        state.error = action.payload;
      });
  },
});

export const { clearSettingsMessages } = settingsSlice.actions;
export default settingsSlice.reducer;