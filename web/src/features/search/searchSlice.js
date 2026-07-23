import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { searchGlobal } from '../../lib/api';

export const fetchSearchResults = createAsyncThunk(
  'search/fetchSearchResults',
  async ({ query, projectId }, thunkAPI) => {
    try {
      const response = await searchGlobal({ query, projectId });
      return response.data;
    } catch (error) {
      return thunkAPI.rejectWithValue(error.message || 'Search failed');
    }
  }
);

const initialState = {
  query: '',
  results: {
    projects: [],
    keywords: [],
    reports: [],
    totals: {
      projects: 0,
      keywords: 0,
      reports: 0,
    },
  },
  loading: false,
  error: null,
  open: false,
};

const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setSearchQuery(state, action) {
      state.query = action.payload;
    },
    clearSearch(state) {
      state.query = '';
      state.results = initialState.results;
      state.loading = false;
      state.error = null;
      state.open = false;
    },
    closeSearch(state) {
      state.open = false;
    },
    openSearch(state) {
      state.open = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSearchResults.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSearchResults.fulfilled, (state, action) => {
        state.loading = false;
        state.results = action.payload || initialState.results;
        state.open = true;
      })
      .addCase(fetchSearchResults.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Search failed';
      });
  },
});

export const { setSearchQuery, clearSearch, closeSearch, openSearch } = searchSlice.actions;
export default searchSlice.reducer;