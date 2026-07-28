import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { getWhiteLabelSettingsApi } from "../../lib/api";

const initialState = {
  settings: null,
  loading: false,
  error: null,
};

export const fetchWhiteLabelSettings = createAsyncThunk(
  "whiteLabel/fetchSettings",
  async (_, { rejectWithValue }) => {
    try {
      const result = await getWhiteLabelSettingsApi();
      return result.data.settings;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

const whiteLabelSlice = createSlice({
  name: "whiteLabel",
  initialState,
  reducers: {
    clearSettings: (state) => {
      state.settings = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchWhiteLabelSettings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchWhiteLabelSettings.fulfilled, (state, action) => {
        state.loading = false;
        state.settings = action.payload;
      })
      .addCase(fetchWhiteLabelSettings.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { clearSettings } = whiteLabelSlice.actions;
export const selectWhiteLabelSettings = (state) => state.whiteLabel.settings;
export const selectWhiteLabelLoading = (state) => state.whiteLabel.loading;

export default whiteLabelSlice.reducer;
