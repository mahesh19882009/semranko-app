'use client'
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { apiRequest } from '../../lib/api';
import { fetchDashboardByProject } from '../dashboard/dashboardSlice';
import { fetchCurrentPricing } from '../pricing/pricingSlice';

const initialState = {
  currentProjectId: null,

  keywords: [],
  rankings: [],

  search: '',
  sortBy: 'position',

  loadingKeywords: false,
  loadingRankings: false,
  adding: false,
  running: false,
  deletingKeyword: false,
  deletingRanking: false,
  clearingRankings: false,
  deletingBulkKeywords: false,
  deletingBulkRankings: false,

  error: null,
  actionMessage: null,
};

const isSameProject = (a, b) => String(a ?? '') === String(b ?? '');

export const fetchKeywordsByProject = createAsyncThunk(
  'keywords/fetchKeywordsByProject',
  async (projectId, thunkAPI) => {
    try {
      const response = await apiRequest(`/keywords/${projectId}`);
      return {
        projectId,
        rows: response.data || [],
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to fetch keywords',
      });
    }
  }
);

export const fetchRankingsByProject = createAsyncThunk(
  'keywords/fetchRankingsByProject',
  async (projectId, thunkAPI) => {
    try {
      const response = await apiRequest(`/rankings/${projectId}`);
      return {
        projectId,
        rows: response.data || [],
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to fetch rankings',
      });
    }
  }
);

export const addKeywordToProject = createAsyncThunk(
  'keywords/addKeywordToProject',
  async ({ projectId, payload }, thunkAPI) => {
    try {
      const response = await apiRequest(`/keywords/${projectId}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        await Promise.all([
          thunkAPI.dispatch(fetchKeywordsByProject(projectId)),
          thunkAPI.dispatch(fetchDashboardByProject(projectId)),
        ]);
      }

      await thunkAPI.dispatch(fetchCurrentPricing());

      return {
        projectId,
        message: response.message || 'Keyword added successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to add keyword',
      });
    }
  }
);

export const deleteKeywordById = createAsyncThunk(
  'keywords/deleteKeywordById',
  async ({ keywordId, projectId }, thunkAPI) => {
    try {
      const response = await apiRequest(`/keywords/${keywordId}`, {
        method: 'DELETE',
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        try {
          await Promise.all([
            thunkAPI.dispatch(fetchKeywordsByProject(projectId)),
            thunkAPI.dispatch(fetchRankingsByProject(projectId)),
            thunkAPI.dispatch(fetchDashboardByProject(projectId)),
          ]);
        } catch (refreshError) {
          console.warn('Failed to refresh data after keyword delete:', refreshError);
        }
      }

      try {
        await thunkAPI.dispatch(fetchCurrentPricing());
      } catch (refreshError) {
        console.warn('Failed to refresh pricing after keyword delete:', refreshError);
      }

      return {
        projectId,
        message: response.message || 'Keyword deleted successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to delete keyword',
      });
    }
  }
);

export const deleteRankingById = createAsyncThunk(
  'keywords/deleteRankingById',
  async ({ rankingId, projectId }, thunkAPI) => {
    try {
      const response = await apiRequest(`/rankings/${rankingId}`, {
        method: 'DELETE',
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        try {
          await Promise.all([
            thunkAPI.dispatch(fetchRankingsByProject(projectId)),
            thunkAPI.dispatch(fetchDashboardByProject(projectId)),
          ]);
        } catch (refreshError) {
          console.warn('Failed to refresh data after ranking delete:', refreshError);
        }
      }

      return {
        projectId,
        message: response.message || 'Ranking deleted successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to delete ranking',
      });
    }
  }
);

export const clearProjectRankings = createAsyncThunk(
  'keywords/clearProjectRankings',
  async (projectId, thunkAPI) => {
    try {
      const response = await apiRequest(`/rankings/project/${projectId}`, {
        method: 'DELETE',
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        try {
          await Promise.all([
            thunkAPI.dispatch(fetchRankingsByProject(projectId)),
            thunkAPI.dispatch(fetchDashboardByProject(projectId)),
          ]);
        } catch (refreshError) {
          console.warn('Failed to refresh data after clearing rankings:', refreshError);
        }
      }

      return {
        projectId,
        message: response.message || 'Rankings cleared successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to clear rankings',
      });
    }
  }
);

export const bulkAddKeywords = createAsyncThunk(
  'keywords/bulkAddKeywords',
  async ({ projectId, keywords, location_code, location, device }, thunkAPI) => {
    try {
      const response = await apiRequest(`/keywords/${projectId}/bulk`, {
        method: 'POST',
        body: JSON.stringify({ keywords, location_code, location, device }),
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        await Promise.all([
          thunkAPI.dispatch(fetchKeywordsByProject(projectId)),
          thunkAPI.dispatch(fetchDashboardByProject(projectId)),
        ]);
      }

      await thunkAPI.dispatch(fetchCurrentPricing());

      return {
        projectId,
        message: response.message || 'Keywords added successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to add keywords',
      });
    }
  }
);

export const bulkDeleteKeywords = createAsyncThunk(
  'keywords/bulkDeleteKeywords',
  async ({ projectId, keywordIds }, thunkAPI) => {
    try {
      const response = await apiRequest(`/keywords/bulk`, {
        method: 'DELETE',
        body: JSON.stringify({ keyword_ids: keywordIds }),
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        try {
          await Promise.all([
            thunkAPI.dispatch(fetchKeywordsByProject(projectId)),
            thunkAPI.dispatch(fetchRankingsByProject(projectId)),
            thunkAPI.dispatch(fetchDashboardByProject(projectId)),
          ]);
        } catch (refreshError) {
          console.warn('Failed to refresh data after bulk keyword delete:', refreshError);
        }
      }

      try {
        await thunkAPI.dispatch(fetchCurrentPricing());
      } catch (refreshError) {
        console.warn('Failed to refresh pricing after bulk keyword delete:', refreshError);
      }

      return {
        projectId,
        message: response.message || 'Keywords deleted successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to delete keywords',
      });
    }
  }
);

export const bulkDeleteRankings = createAsyncThunk(
  'keywords/bulkDeleteRankings',
  async ({ projectId, rankingIds }, thunkAPI) => {
    try {
      const response = await apiRequest(`/rankings/bulk`, {
        method: 'DELETE',
        body: JSON.stringify({ ranking_ids: rankingIds }),
      });

      const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

      if (isSameProject(selectedProjectId, projectId)) {
        try {
          await Promise.all([
            thunkAPI.dispatch(fetchRankingsByProject(projectId)),
            thunkAPI.dispatch(fetchDashboardByProject(projectId)),
          ]);
        } catch (refreshError) {
          console.warn('Failed to refresh data after bulk ranking delete:', refreshError);
        }
      }

      return {
        projectId,
        message: response.message || 'Rankings deleted successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to delete rankings',
      });
    }
  }
);

export const pollRankingsByProject = createAsyncThunk(
  'keywords/pollRankingsByProject',
  async ({ projectId, previousLatestCheckedAt = null, attempts = 10, delayMs = 2500 }, thunkAPI) => {
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    try {
      const previousTime = previousLatestCheckedAt
        ? new Date(previousLatestCheckedAt).getTime()
        : 0;

      for (let i = 0; i < attempts; i += 1) {
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;

        if (!isSameProject(selectedProjectId, projectId)) {
          return thunkAPI.rejectWithValue({
            projectId,
            message: 'Project changed while polling rankings',
          });
        }

        const response = await apiRequest(`/rankings/${projectId}`);
        const rows = response.data || [];

        const latestCheckedAt = rows.length
          ? Math.max(
              ...rows.map((row) => new Date(row.checkedAt || row.updatedAt || row.createdAt || 0).getTime())
            )
          : 0;

        if (rows.length > 0 && latestCheckedAt > previousTime) {
          return {
            projectId,
            rows,
          };
        }

        await sleep(delayMs);
      }

      return {
        projectId,
        rows: [],
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed while polling rankings',
      });
    }
  }
);

export const runRankCheck = createAsyncThunk(
  'keywords/runRankCheck',
  async (projectId, thunkAPI) => {
    try {
      const state = thunkAPI.getState();
      const selectedProjectId = state.projects.selectedProjectId;

      if (!isSameProject(selectedProjectId, projectId)) {
        return thunkAPI.rejectWithValue({
          projectId,
          message: 'Selected project changed. Please run again.',
        });
      }

      const rankings = state.keywords.rankings || [];
      const previousLatestCheckedAt = rankings.length
        ? rankings.reduce((latest, row) => {
            const current = row.checkedAt || row.updatedAt || row.createdAt || null;
            if (!current) return latest;
            if (!latest) return current;
            return new Date(current) > new Date(latest) ? current : latest;
          }, null)
        : null;

      const response = await apiRequest(`/rankings/${projectId}/run`, {
        method: 'POST',
      });

      await thunkAPI.dispatch(
        pollRankingsByProject({
          projectId,
          previousLatestCheckedAt,
        })
      );

      if (isSameProject(selectedProjectId, projectId)) {
        await thunkAPI.dispatch(fetchDashboardByProject(projectId));
      }

      return {
        projectId,
        message: response.message || 'Rank check queued successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue({
        projectId,
        message: error.message || 'Failed to run rank check',
      });
    }
  }
);

const keywordsSlice = createSlice({
  name: 'keywords',
  initialState,
  reducers: {
    setKeywordSearch: (state, action) => {
      state.search = action.payload;
    },
    setSortBy: (state, action) => {
      state.sortBy = action.payload;
    },
    clearKeywordMessage: (state) => {
      state.error = null;
      state.actionMessage = null;
    },
    clearKeywordsState: () => initialState,
    resetKeywordsForProjectChange: (state, action) => {
      state.currentProjectId = action.payload ?? null;
      state.keywords = [];
      state.rankings = [];
      state.loadingKeywords = !!action.payload;
      state.loadingRankings = !!action.payload;
      state.adding = false;
      state.running = false;
      state.deletingKeyword = false;
      state.deletingRanking = false;
      state.clearingRankings = false;
      state.error = null;
      state.actionMessage = null;
      state.search = '';
      state.sortBy = 'position';
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchKeywordsByProject.pending, (state, action) => {
        state.loadingKeywords = true;
        state.error = null;
        state.currentProjectId = action.meta.arg;
        state.keywords = [];
      })
      .addCase(fetchKeywordsByProject.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.loadingKeywords = false;
        state.keywords = action.payload.rows;
      })
      .addCase(fetchKeywordsByProject.rejected, (state, action) => {
        const projectId = action.payload?.projectId ?? action.meta.arg;

        if (!isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.loadingKeywords = false;
        state.error = action.payload?.message || 'Failed to fetch keywords';
      })

      .addCase(fetchRankingsByProject.pending, (state, action) => {
        state.loadingRankings = true;
        state.error = null;
        state.currentProjectId = action.meta.arg;
        state.rankings = [];
      })
      .addCase(fetchRankingsByProject.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.loadingRankings = false;
        state.rankings = action.payload.rows;
      })
      .addCase(fetchRankingsByProject.rejected, (state, action) => {
        const projectId = action.payload?.projectId ?? action.meta.arg;

        if (!isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.loadingRankings = false;
        state.error = action.payload?.message || 'Failed to fetch rankings';
      })

      .addCase(bulkAddKeywords.pending, (state) => {
        state.adding = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(bulkAddKeywords.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.adding = false;
        state.actionMessage = action.payload.message;
      })
      .addCase(bulkAddKeywords.rejected, (state, action) => {
        const projectId = action.payload?.projectId;

        if (projectId && !isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.adding = false;
        state.error = action.payload?.message || 'Failed to add keywords';
      })

      .addCase(bulkDeleteKeywords.pending, (state) => {
        state.deletingBulkKeywords = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(bulkDeleteKeywords.fulfilled, (state, action) => {
        state.deletingBulkKeywords = false;

        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.actionMessage = action.payload.message;
      })
      .addCase(bulkDeleteKeywords.rejected, (state, action) => {
        state.deletingBulkKeywords = false;

        const projectId = action.payload?.projectId;

        if (projectId && !isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.error = action.payload?.message || 'Failed to delete keywords';
      })

      .addCase(deleteKeywordById.pending, (state) => {
        state.deletingKeyword = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(deleteKeywordById.fulfilled, (state, action) => {
        state.deletingKeyword = false;
        
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.actionMessage = action.payload.message;
      })
      .addCase(deleteKeywordById.rejected, (state, action) => {
        state.deletingKeyword = false;
        
        const projectId = action.payload?.projectId;

        if (projectId && !isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.error = action.payload?.message || 'Failed to delete keyword';
      })

      .addCase(bulkDeleteRankings.pending, (state) => {
        state.deletingBulkRankings = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(bulkDeleteRankings.fulfilled, (state, action) => {
        state.deletingBulkRankings = false;

        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.actionMessage = action.payload.message;
      })
      .addCase(bulkDeleteRankings.rejected, (state, action) => {
        state.deletingBulkRankings = false;

        const projectId = action.payload?.projectId;

        if (projectId && !isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.error = action.payload?.message || 'Failed to delete rankings';
      })

      .addCase(deleteRankingById.pending, (state) => {
        state.deletingRanking = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(deleteRankingById.fulfilled, (state, action) => {
        state.deletingRanking = false;
        
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.actionMessage = action.payload.message;
      })
      .addCase(deleteRankingById.rejected, (state, action) => {
        state.deletingRanking = false;
        
        const projectId = action.payload?.projectId;

        if (projectId && !isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.error = action.payload?.message || 'Failed to delete ranking';
      })

      .addCase(clearProjectRankings.pending, (state) => {
        state.clearingRankings = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(clearProjectRankings.fulfilled, (state, action) => {
        state.clearingRankings = false;
        
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.actionMessage = action.payload.message;
      })
      .addCase(clearProjectRankings.rejected, (state, action) => {
        state.clearingRankings = false;
        
        const projectId = action.payload?.projectId;

        if (projectId && !isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.error = action.payload?.message || 'Failed to clear rankings';
      })

      .addCase(runRankCheck.pending, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.meta.arg)) {
          return;
        }

        state.running = true;
        state.loadingRankings = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(runRankCheck.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.running = false;
        state.loadingRankings = false;
        state.actionMessage = action.payload.message;
      })
      .addCase(runRankCheck.rejected, (state, action) => {
        const projectId = action.payload?.projectId ?? action.meta.arg;

        if (!isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.running = false;
        state.loadingRankings = false;
        state.error = action.payload?.message || 'Failed to run rank check';
      })

      .addCase(pollRankingsByProject.pending, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.meta.arg.projectId)) {
          return;
        }

        state.loadingRankings = true;
        state.error = null;
      })
      .addCase(pollRankingsByProject.fulfilled, (state, action) => {
        if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
          return;
        }

        state.rankings = action.payload.rows;
        state.loadingRankings = false;
      })
      .addCase(pollRankingsByProject.rejected, (state, action) => {
        const projectId = action.payload?.projectId ?? action.meta.arg?.projectId;

        if (!isSameProject(state.currentProjectId, projectId)) {
          return;
        }

        state.loadingRankings = false;

        if (action.payload?.message !== 'Project changed while polling rankings') {
          state.error = action.payload?.message || 'Failed while polling rankings';
        }
      });
  },
});

export const {
  setKeywordSearch,
  setSortBy,
  clearKeywordMessage,
  clearKeywordsState,
  resetKeywordsForProjectChange,
} = keywordsSlice.actions;

export default keywordsSlice.reducer;