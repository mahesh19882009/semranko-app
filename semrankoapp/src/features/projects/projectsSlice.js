'use client'
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { apiRequest, toRejectedValue } from '../../lib/api';

const STORAGE_KEY = 'selectedProjectId';

const getStoredSelectedProjectId = () => {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value ? String(value) : null;
  } catch {
    return null;
  }
};

const setStoredSelectedProjectId = (projectId) => {
  try {
    if (projectId !== null && projectId !== undefined && String(projectId).trim() !== '') {
      localStorage.setItem(STORAGE_KEY, String(projectId));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    //
  }
};

const resolveSelectedProjectId = (projects, preferredId) => {
  if (!Array.isArray(projects) || projects.length === 0) {
    return null;
  }

  if (
    preferredId &&
    projects.some((project) => String(project.id) === String(preferredId))
  ) {
    return String(preferredId);
  }

  return String(projects[0].id);
};

const initialState = {
  list: [],
  selectedProjectId: getStoredSelectedProjectId(),
  loading: false,
  creating: false,
  updating: false,
  deleting: false,
  error: null,
  actionMessage: null,
};

export const fetchProjects = createAsyncThunk(
  'projects/fetchProjects',
  async (_, thunkAPI) => {
    try {
      const response = await apiRequest('/projects');
      return response.data || [];
    } catch (error) {
      return thunkAPI.rejectWithValue(toRejectedValue(error, 'Failed to fetch projects.'));
    }
  }
);

export const createProject = createAsyncThunk(
  'projects/createProject',
  async (payload, thunkAPI) => {
    try {
      const response = await apiRequest('/projects', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const createdProject = response.data;

      await thunkAPI.dispatch(fetchProjects());

      return createdProject;
    } catch (error) {
      return thunkAPI.rejectWithValue(toRejectedValue(error, 'Failed to create project.'));
    }
  }
);

export const deleteProjectById = createAsyncThunk(
  'projects/deleteProjectById',
  async (projectId, thunkAPI) => {
    try {
      const response = await apiRequest(`/projects/${projectId}`, {
        method: 'DELETE',
      });

      return {
        projectId,
        message: response.message || 'Project deleted successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue(toRejectedValue(error, 'Failed to delete project.'));
    }
  }
);

export const updateProject = createAsyncThunk(
  'projects/updateProject',
  async ({ projectId, payload }, thunkAPI) => {
    try {
      const response = await apiRequest(`/projects/${projectId}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });

      return {
        project: response.data,
        message: response.message || 'Project updated successfully',
      };
    } catch (error) {
      return thunkAPI.rejectWithValue(toRejectedValue(error, 'Failed to update project.'));
    }
  }
);

const projectsSlice = createSlice({
  name: 'projects',
  initialState,
  reducers: {
    setSelectedProjectId: (state, action) => {
      state.selectedProjectId = action.payload ? String(action.payload) : null;
      setStoredSelectedProjectId(state.selectedProjectId);
    },
    clearSelectedProjectId: (state) => {
      state.selectedProjectId = null;
      setStoredSelectedProjectId(null);
    },
    clearProjectMessage: (state) => {
      state.error = null;
      state.actionMessage = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchProjects.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchProjects.fulfilled, (state, action) => {
        state.loading = false;
        state.list = action.payload;

        const storedProjectId = getStoredSelectedProjectId();
        const preferredId = state.selectedProjectId || storedProjectId;

        state.selectedProjectId = resolveSelectedProjectId(
          action.payload,
          preferredId
        );

        setStoredSelectedProjectId(state.selectedProjectId);
      })
      .addCase(fetchProjects.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || { message: 'Failed to fetch projects.' };
      })

      .addCase(createProject.pending, (state) => {
        state.creating = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(createProject.fulfilled, (state, action) => {
        state.creating = false;
        state.actionMessage = 'Project created successfully';

        if (action.payload?.id) {
          state.selectedProjectId = String(action.payload.id);
          setStoredSelectedProjectId(state.selectedProjectId);
        }
      })
      .addCase(createProject.rejected, (state, action) => {
        state.creating = false;
        state.error = action.payload || 'Failed to create project';
      })

      .addCase(updateProject.pending, (state) => {
        state.updating = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(updateProject.fulfilled, (state, action) => {
        state.updating = false;
        const index = state.list.findIndex(
          (project) => String(project.id) === String(action.payload.project.id)
        );
        if (index !== -1) {
          state.list[index] = action.payload.project;
        }
        state.actionMessage = action.payload.message;
      })
      .addCase(updateProject.rejected, (state, action) => {
        state.updating = false;
        state.error = action.payload || 'Failed to update project';
      })

      .addCase(deleteProjectById.pending, (state) => {
        state.deleting = true;
        state.error = null;
        state.actionMessage = null;
      })
      .addCase(deleteProjectById.fulfilled, (state, action) => {
        state.deleting = false;
        state.list = state.list.filter(
          (project) => String(project.id) !== String(action.payload.projectId)
        );
        state.actionMessage = action.payload.message;

        if (String(state.selectedProjectId) === String(action.payload.projectId)) {
          state.selectedProjectId = resolveSelectedProjectId(state.list, null);
          setStoredSelectedProjectId(state.selectedProjectId);
        }
      })
      .addCase(deleteProjectById.rejected, (state, action) => {
        state.deleting = false;
        state.error = action.payload || 'Failed to delete project';
      });
  },
});

export const {
  setSelectedProjectId,
  clearSelectedProjectId,
  clearProjectMessage,
} = projectsSlice.actions;

export default projectsSlice.reducer;
