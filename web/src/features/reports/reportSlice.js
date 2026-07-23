import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { apiRequest } from '../../lib/api';
import { fetchDashboardByProject } from '../dashboard/dashboardSlice';

export const fetchReports = createAsyncThunk(
  'reports/fetchReports',
  async (projectId, { rejectWithValue }) => {
    try {
      const data = await apiRequest(`/reports/${projectId}`);
      return {
        projectId,
        rows: Array.isArray(data?.data) ? data.data : [],
      };
    } catch (error) {
      return rejectWithValue({
        projectId,
        message: error.message || 'Failed to fetch reports',
      });
    }
  }
);

export const fetchReportById = createAsyncThunk(
  'reports/fetchReportById',
  async (reportId, { rejectWithValue }) => {
    try {
      const data = await apiRequest(`/reports/detail/${reportId}`);
      return data?.data || null;
    } catch (error) {
      return rejectWithValue(error.message || 'Failed to fetch report details');
    }
  }
);

export const runReport = createAsyncThunk(
  'reports/runReport',
  async (projectId, { dispatch, rejectWithValue }) => {
    try {
      const data = await apiRequest(`/reports/${projectId}/run`, {
        method: 'POST',
      });

      const reportsResult = await dispatch(fetchReports(projectId));
      if (fetchReports.rejected.match(reportsResult)) {
        return rejectWithValue({
          projectId,
          message:
            reportsResult.payload?.message ||
            reportsResult.error?.message ||
            'Report created but failed to refresh reports',
        });
      }

      await dispatch(fetchDashboardByProject(projectId));

      return {
        projectId,
        report: data?.data || null,
        message: data?.message || 'Report created successfully',
      };
    } catch (error) {
      return rejectWithValue({
        projectId,
        message: error.message || 'Failed to run report',
      });
    }
  }
);

export const deleteReportById = createAsyncThunk(
  'reports/deleteReportById',
  async ({ reportId, projectId }, { dispatch, rejectWithValue }) => {
    try {
      const data = await apiRequest(`/reports/detail/${reportId}`, {
        method: 'DELETE',
      });

      const reportsResult = await dispatch(fetchReports(projectId));
      if (fetchReports.rejected.match(reportsResult)) {
        return rejectWithValue({
          reportId,
          projectId,
          message:
            reportsResult.payload?.message ||
            reportsResult.error?.message ||
            'Report deleted but failed to refresh reports',
        });
      }

      await dispatch(fetchDashboardByProject(projectId));

      return {
        reportId,
        projectId,
        message: data?.message || 'Report deleted successfully',
      };
    } catch (error) {
      return rejectWithValue({
        reportId,
        projectId,
        message: error.message || 'Failed to delete report',
      });
    }
  }
);

export const deleteAllReports = createAsyncThunk(
  'reports/deleteAllReports',
  async (projectId, { dispatch, rejectWithValue }) => {
    try {
      const data = await apiRequest(`/reports/${projectId}/all`, {
        method: 'DELETE',
      });

      const reportsResult = await dispatch(fetchReports(projectId));
      if (fetchReports.rejected.match(reportsResult)) {
        return rejectWithValue({
          projectId,
          message:
            reportsResult.payload?.message ||
            reportsResult.error?.message ||
            'Reports deleted but failed to refresh reports',
        });
      }

      await dispatch(fetchDashboardByProject(projectId));

      return {
        projectId,
        message: data?.message || 'All reports deleted successfully',
      };
    } catch (error) {
      return rejectWithValue({
        projectId,
        message: error.message || 'Failed to delete all reports',
      });
    }
  }
);

const initialState = {
  reports: [],
  loading: false,
  running: false,
  error: null,
  selectedReport: null,
  selectedReportLoading: false,
  selectedReportError: null,
  deleteLoadingById: {},
  deleteAllLoading: false,
  message: null,
  currentProjectId: null,
};

const reportSlice = createSlice({
  name: 'reports',
  initialState,
  reducers: {
    clearReportError: (state) => {
      state.error = null;
      state.selectedReportError = null;
    },
    clearReportMessage: (state) => {
      state.message = null;
    },
    clearSelectedReport: (state) => {
      state.selectedReport = null;
      state.selectedReportError = null;
      state.selectedReportLoading = false;
    },
    resetReportsState: (state) => {
      state.reports = [];
      state.loading = false;
      state.running = false;
      state.error = null;
      state.selectedReport = null;
      state.selectedReportLoading = false;
      state.selectedReportError = null;
      state.deleteLoadingById = {};
      state.deleteAllLoading = false;
      state.message = null;
      state.currentProjectId = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchReports.pending, (state, action) => {
        state.loading = true;
        state.error = null;
        state.currentProjectId = action.meta.arg;
      })
      .addCase(fetchReports.fulfilled, (state, action) => {
        state.loading = false;
        state.reports = action.payload.rows;
        state.currentProjectId = action.payload.projectId;
      })
      .addCase(fetchReports.rejected, (state, action) => {
        state.loading = false;
        state.reports = [];
        state.error =
          action.payload?.message || action.error?.message || 'Failed to fetch reports';
      })

      .addCase(fetchReportById.pending, (state) => {
        state.selectedReportLoading = true;
        state.selectedReportError = null;
      })
      .addCase(fetchReportById.fulfilled, (state, action) => {
        state.selectedReportLoading = false;
        state.selectedReport = action.payload;
      })
      .addCase(fetchReportById.rejected, (state, action) => {
        state.selectedReportLoading = false;
        state.selectedReportError =
          action.payload || action.error?.message || 'Failed to fetch report details';
      })

      .addCase(runReport.pending, (state) => {
        state.running = true;
        state.error = null;
        state.message = null;
      })
      .addCase(runReport.fulfilled, (state, action) => {
        state.running = false;
        state.message = action.payload.message;
        state.currentProjectId = action.payload.projectId;
      })
      .addCase(runReport.rejected, (state, action) => {
        state.running = false;
        state.error =
          action.payload?.message || action.error?.message || 'Failed to run report';
      })

      .addCase(deleteReportById.pending, (state, action) => {
        const reportId = action.meta.arg?.reportId;
        if (reportId) {
          state.deleteLoadingById[reportId] = true;
        }
        state.error = null;
        state.message = null;
      })
      .addCase(deleteReportById.fulfilled, (state, action) => {
        const reportId = action.payload?.reportId;
        if (reportId) {
          delete state.deleteLoadingById[reportId];
        }
        if (state.selectedReport?.id === reportId) {
          state.selectedReport = null;
        }
        state.message = action.payload.message;
      })
      .addCase(deleteReportById.rejected, (state, action) => {
        const reportId = action.payload?.reportId || action.meta.arg?.reportId;
        if (reportId) {
          delete state.deleteLoadingById[reportId];
        }
        state.error =
          action.payload?.message || action.error?.message || 'Failed to delete report';
      })

      .addCase(deleteAllReports.pending, (state) => {
        state.deleteAllLoading = true;
        state.error = null;
        state.message = null;
      })
      .addCase(deleteAllReports.fulfilled, (state, action) => {
        state.deleteAllLoading = false;
        state.selectedReport = null;
        state.message = action.payload.message;
      })
      .addCase(deleteAllReports.rejected, (state, action) => {
        state.deleteAllLoading = false;
        state.error =
          action.payload?.message || action.error?.message || 'Failed to delete all reports';
      });
  },
});

export const {
  clearReportError,
  clearReportMessage,
  clearSelectedReport,
  resetReportsState,
} = reportSlice.actions;

export default reportSlice.reducer;