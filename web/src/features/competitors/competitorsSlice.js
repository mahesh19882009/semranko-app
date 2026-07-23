import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { apiRequest } from '../../lib/api';
import { fetchDashboardByProject } from '../dashboard/dashboardSlice';

const initialState = {
  currentProjectId: null,
  list: [],
  loading: false,
  adding: false,
  updating: false,
  deleting: false,
  error: null,
  actionMessage: null,
};

const isSameProject = (a, b) => String(a ?? '') === String(b ?? '');

const normalizeDomain = (value = '') =>
  value
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/+$/, '');

export const fetchCompetitorsByProject = createAsyncThunk(
  'competitors/fetchCompetitorsByProject',
  async (projectId, thunkAPI) => {
    try {
      const response = await apiRequest(`/competitors/project/${projectId}`);
      return {
        projectId,
        rows: response.data || [],
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to fetch competitors',
      });
    }
  }
);

export const addCompetitorToProject = createAsyncThunk(
  'competitors/addCompetitorToProject',
  async ({ projectId, payload }, thunkAPI) => {
    try {
      const cleanPayload = {
        projectId,
        name: payload.name?.trim(),
        domain: normalizeDomain(payload.domain),
      };

      const response = await apiRequest(`/competitors`, {
        method: 'POST',
        body: JSON.stringify(cleanPayload),
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        await Promise.all([
          thunkAPI.dispatch(fetchCompetitorsByProject(projectId)),
          thunkAPI.dispatch(fetchDashboardByProject(projectId)),
        ]);
      }

      return {
        projectId,
        message: response.message || 'Competitor added successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to add competitor',
      });
    }
  }
);

export const updateCompetitorById = createAsyncThunk(
  'competitors/updateCompetitorById',
  async ({ competitorId, projectId, payload }, thunkAPI) => {
    try {
      const cleanPayload = {
        name: payload.name?.trim(),
        domain: normalizeDomain(payload.domain),
      };

      const response = await apiRequest(`/competitors/${competitorId}`, {
        method: 'PUT',
        body: JSON.stringify(cleanPayload),
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        await Promise.all([
          thunkAPI.dispatch(fetchCompetitorsByProject(projectId)),
          thunkAPI.dispatch(fetchDashboardByProject(projectId)),
        ]);
      }

      return {
        projectId,
        message: response.message || 'Competitor updated successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to update competitor',
      });
    }
  }
);

export const deleteCompetitorById = createAsyncThunk(
  'competitors/deleteCompetitorById',
  async ({ competitorId, projectId }, thunkAPI) => {
    try {
      const response = await apiRequest(`/competitors/${competitorId}`, {
        method: 'DELETE',
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        await Promise.all([
          thunkAPI.dispatch(fetchCompetitorsByProject(projectId)),
          thunkAPI.dispatch(fetchDashboardByProject(projectId)),
        ]);
      }

      return {
        projectId,
        message: response.message || 'Competitor deleted successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to delete competitor',
      });
    }
  }
);

const competitorsSlice = createSlice({
  name: 'competitors',
  initialState,
  reducers: {
    clearCompetitorMessage: (state) => {
      state.error = null;
      state.actionMessage = null;
    },
    clearCompetitorsState: () => initialState,
    resetCompetitorsForProjectChange: (state, action) => {
      state.currentProjectId = action.payload ?? null;
      state.list = [];
      state.loading = !!action.payload;
      state.adding = false;
      state.updating = false;
      state.deleting = false;
      state.error = null;
      state.actionMessage = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCompetitorsByProject.pending, (state, action) => {
        state.loading = true;
        state.error = null;
        state.currentProjectId = action.meta.arg;
        state.list = [];
      })
      .addCase(fetchCompetitorsByProject.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.loading = false;
        state.list = action.payload.rows;
      })
      .addCase(fetchCompetitorsByProject.rejected, (state, action) => {
        const projectId = action.payload?.projectId ?? action.meta.arg;

        if (!isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.loading = false;
        state.error = action.payload?.message || 'Failed to fetch competitors';
      })

      .addCase(addCompetitorToProject.pending, (state) => {
        state.adding = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(addCompetitorToProject.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.adding = false;
        state.actionMessage = action.payload.message;
      })
      .addCase(addCompetitorToProject.rejected, (state, action) => {
        const projectId = action.payload?.projectId;

        if (projectId && !isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.adding = false;
        state.error = action.payload?.message || 'Failed to add competitor';
      })

      .addCase(updateCompetitorById.pending, (state) => {
        state.updating = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(updateCompetitorById.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.updating = false;
        state.actionMessage = action.payload.message;
      })
      .addCase(updateCompetitorById.rejected, (state, action) => {
        const projectId = action.payload?.projectId;

        if (projectId && !isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.updating = false;
        state.error = action.payload?.message || 'Failed to update competitor';
      })

      .addCase(deleteCompetitorById.pending, (state) => {
        state.deleting = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(deleteCompetitorById.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.deleting = false;
        state.actionMessage = action.payload.message;
      })
      .addCase(deleteCompetitorById.rejected, (state, action) => {
        const projectId = action.payload?.projectId;

        if (projectId && !isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.deleting = false;
        state.error = action.payload?.message || 'Failed to delete competitor';
      });
  },
});

export const {
  clearCompetitorMessage,
  clearCompetitorsState,
  resetCompetitorsForProjectChange,
} = competitorsSlice.actions;

export default competitorsSlice.reducer;