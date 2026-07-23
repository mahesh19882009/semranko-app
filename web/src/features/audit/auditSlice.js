import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { apiRequest } from '../../lib/api';
import { fetchDashboardByProject } from '../dashboard/dashboardSlice';

const initialState = {
  currentProjectId: null,
  auditRuns: [],
  loading: false,
  running: false,
  error: null,
  actionMessage: null,
};

const isSameProject = (a, b) => String(a ?? '') === String(b ?? '');

export const fetchAuditsByProject = createAsyncThunk(
  'audit/fetchAuditsByProject',
  async (projectId, thunkAPI) => {
    try {
      const response = await apiRequest(`/audits/${projectId}`);
      return {
        projectId,
        rows: response.data || [],
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to fetch audits',
      });
    }
  }
);

export const runAuditByProject = createAsyncThunk(
  'audit/runAuditByProject',
  async (projectId, thunkAPI) => {
    try {
      const response = await apiRequest(`/audits/${projectId}/run`, {
        method: 'POST',
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        await Promise.all([
          thunkAPI.dispatch(fetchAuditsByProject(projectId)),
          thunkAPI.dispatch(fetchDashboardByProject(projectId)),
        ]);
      }

      return {
        projectId,
        message: response.message || 'Audit completed successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to run audit',
      });
    }
  }
);

const auditSlice = createSlice({
  name: 'audit',
  initialState,
  reducers: {
    clearAuditMessage: (state) => {
      state.error = null;
      state.actionMessage = null;
    },
    clearAuditState: () => initialState,
    resetAuditForProjectChange: (state, action) => {
      state.currentProjectId = action.payload ?? null;
      state.auditRuns = [];
      state.loading = !!action.payload;
      state.running = false;
      state.error = null;
      state.actionMessage = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAuditsByProject.pending, (state, action) => {
        state.loading = true;
        state.error = null;
        state.currentProjectId = action.meta.arg;
        state.auditRuns = [];
      })
      .addCase(fetchAuditsByProject.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.loading = false;
        state.auditRuns = action.payload.rows;
      })
      .addCase(fetchAuditsByProject.rejected, (state, action) => {
        const projectId = action.payload?.projectId ?? action.meta.arg;

        if (!isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.loading = false;
        state.error = action.payload?.message || 'Failed to fetch audits';
      })

      .addCase(runAuditByProject.pending, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.meta.arg)) {
          return;
        }

        state.running = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(runAuditByProject.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.running = false;
        state.actionMessage = action.payload.message;
      })
      .addCase(runAuditByProject.rejected, (state, action) => {
        const projectId = action.payload?.projectId ?? action.meta.arg;

        if (!isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.running = false;
        state.error = action.payload?.message || 'Failed to run audit';
      });
  },
});

export const {
  clearAuditMessage,
  clearAuditState,
  resetAuditForProjectChange,
} = auditSlice.actions;

export default auditSlice.reducer;