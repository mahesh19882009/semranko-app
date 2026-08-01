(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/app/context/Providers.jsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Providers",
    ()=>Providers
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$redux$2f$dist$2f$react$2d$redux$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/react-redux/dist/react-redux.mjs [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$helmet$2d$async$2f$lib$2f$index$2e$esm$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/react-helmet-async/lib/index.esm.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$app$2f$store$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/app/store.js [app-client] (ecmascript)");
'use client';
;
;
;
;
function Providers({ children }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$redux$2f$dist$2f$react$2d$redux$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Provider"], {
        store: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$app$2f$store$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["store"],
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$helmet$2d$async$2f$lib$2f$index$2e$esm$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["HelmetProvider"], {
            children: children
        }, void 0, false, {
            fileName: "[project]/app/context/Providers.jsx",
            lineNumber: 9,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/app/context/Providers.jsx",
        lineNumber: 8,
        columnNumber: 5
    }, this);
}
_c = Providers;
var _c;
__turbopack_context__.k.register(_c, "Providers");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/app/store.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "store",
    ()=>store
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/@reduxjs/toolkit/dist/redux-toolkit.modern.mjs [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/dashboard/dashboardSlice.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$projects$2f$projectsSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/projects/projectsSlice.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$keywords$2f$keywordsSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/keywords/keywordsSlice.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$competitors$2f$competitorsSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/competitors/competitorsSlice.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/pricing/pricingSlice.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$subscription$2f$subscriptionSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/subscription/subscriptionSlice.js [app-client] (ecmascript)");
'use client';
;
;
;
;
;
;
;
const store = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["configureStore"])({
    reducer: {
        dashboard: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"],
        projects: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$projects$2f$projectsSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"],
        keywords: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$keywords$2f$keywordsSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"],
        competitors: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$competitors$2f$competitorsSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"],
        pricing: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"],
        subscription: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$subscription$2f$subscriptionSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"]
    }
});
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/features/competitors/competitorsSlice.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "addCompetitorToProject",
    ()=>addCompetitorToProject,
    "clearCompetitorMessage",
    ()=>clearCompetitorMessage,
    "clearCompetitorsState",
    ()=>clearCompetitorsState,
    "default",
    ()=>__TURBOPACK__default__export__,
    "deleteCompetitorById",
    ()=>deleteCompetitorById,
    "fetchCompetitorsByProject",
    ()=>fetchCompetitorsByProject,
    "resetCompetitorsForProjectChange",
    ()=>resetCompetitorsForProjectChange,
    "updateCompetitorById",
    ()=>updateCompetitorById
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/@reduxjs/toolkit/dist/redux-toolkit.modern.mjs [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/dashboard/dashboardSlice.js [app-client] (ecmascript)");
'use client';
;
;
;
const initialState = {
    currentProjectId: null,
    list: [],
    loading: false,
    adding: false,
    updating: false,
    deleting: false,
    error: null,
    actionMessage: null
};
const isSameProject = (a, b)=>String(a ?? '') === String(b ?? '');
const normalizeDomain = (value = '')=>value.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/+$/, '');
const fetchCompetitorsByProject = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('competitors/fetchCompetitorsByProject', async (projectId, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/competitors/project/${projectId}`);
        return {
            projectId,
            rows: response.data || []
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to fetch competitors'
        });
    }
});
const addCompetitorToProject = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('competitors/addCompetitorToProject', async ({ projectId, payload }, thunkAPI)=>{
    try {
        const cleanPayload = {
            projectId,
            name: payload.name?.trim(),
            domain: normalizeDomain(payload.domain)
        };
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/competitors`, {
            method: 'POST',
            body: JSON.stringify(cleanPayload)
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            await Promise.all([
                thunkAPI.dispatch(fetchCompetitorsByProject(projectId)),
                thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
            ]);
        }
        return {
            projectId,
            message: response.message || 'Competitor added successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to add competitor'
        });
    }
});
const updateCompetitorById = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('competitors/updateCompetitorById', async ({ competitorId, projectId, payload }, thunkAPI)=>{
    try {
        const cleanPayload = {
            name: payload.name?.trim(),
            domain: normalizeDomain(payload.domain)
        };
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/competitors/${competitorId}`, {
            method: 'PUT',
            body: JSON.stringify(cleanPayload)
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            await Promise.all([
                thunkAPI.dispatch(fetchCompetitorsByProject(projectId)),
                thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
            ]);
        }
        return {
            projectId,
            message: response.message || 'Competitor updated successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to update competitor'
        });
    }
});
const deleteCompetitorById = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('competitors/deleteCompetitorById', async ({ competitorId, projectId }, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/competitors/${competitorId}`, {
            method: 'DELETE'
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            await Promise.all([
                thunkAPI.dispatch(fetchCompetitorsByProject(projectId)),
                thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
            ]);
        }
        return {
            projectId,
            message: response.message || 'Competitor deleted successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to delete competitor'
        });
    }
});
const competitorsSlice = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createSlice"])({
    name: 'competitors',
    initialState,
    reducers: {
        clearCompetitorMessage: (state)=>{
            state.error = null;
            state.actionMessage = null;
        },
        clearCompetitorsState: ()=>initialState,
        resetCompetitorsForProjectChange: (state, action)=>{
            state.currentProjectId = action.payload ?? null;
            state.list = [];
            state.loading = !!action.payload;
            state.adding = false;
            state.updating = false;
            state.deleting = false;
            state.error = null;
            state.actionMessage = null;
        }
    },
    extraReducers: (builder)=>{
        builder.addCase(fetchCompetitorsByProject.pending, (state, action)=>{
            state.loading = true;
            state.error = null;
            state.currentProjectId = action.meta.arg;
            state.list = [];
        }).addCase(fetchCompetitorsByProject.fulfilled, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.loading = false;
            state.list = action.payload.rows;
        }).addCase(fetchCompetitorsByProject.rejected, (state, action)=>{
            const projectId = action.payload?.projectId ?? action.meta.arg;
            if (!isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.loading = false;
            state.error = action.payload?.message || 'Failed to fetch competitors';
        }).addCase(addCompetitorToProject.pending, (state)=>{
            state.adding = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(addCompetitorToProject.fulfilled, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.adding = false;
            state.actionMessage = action.payload.message;
        }).addCase(addCompetitorToProject.rejected, (state, action)=>{
            const projectId = action.payload?.projectId;
            if (projectId && !isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.adding = false;
            state.error = action.payload?.message || 'Failed to add competitor';
        }).addCase(updateCompetitorById.pending, (state)=>{
            state.updating = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(updateCompetitorById.fulfilled, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.updating = false;
            state.actionMessage = action.payload.message;
        }).addCase(updateCompetitorById.rejected, (state, action)=>{
            const projectId = action.payload?.projectId;
            if (projectId && !isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.updating = false;
            state.error = action.payload?.message || 'Failed to update competitor';
        }).addCase(deleteCompetitorById.pending, (state)=>{
            state.deleting = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(deleteCompetitorById.fulfilled, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.deleting = false;
            state.actionMessage = action.payload.message;
        }).addCase(deleteCompetitorById.rejected, (state, action)=>{
            const projectId = action.payload?.projectId;
            if (projectId && !isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.deleting = false;
            state.error = action.payload?.message || 'Failed to delete competitor';
        });
    }
});
const { clearCompetitorMessage, clearCompetitorsState, resetCompetitorsForProjectChange } = competitorsSlice.actions;
const __TURBOPACK__default__export__ = competitorsSlice.reducer;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/features/dashboard/dashboardSlice.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>__TURBOPACK__default__export__,
    "fetchDashboardByProject",
    ()=>fetchDashboardByProject,
    "resetDashboard",
    ()=>resetDashboard,
    "setDateRange",
    ()=>setDateRange
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/@reduxjs/toolkit/dist/redux-toolkit.modern.mjs [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.js [app-client] (ecmascript)");
'use client';
;
;
const fetchDashboardByProject = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('dashboard/fetchByProject', async (projectId, { rejectWithValue })=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/dashboard/${projectId}`);
        return response.data;
    } catch (error) {
        return rejectWithValue(error.message || 'Failed to fetch dashboard');
    }
});
const initialState = {
    stats: {
        totalKeywords: 0,
        avgRank: 0,
        estimatedTraffic: 0
    },
    rankTrend: [],
    competitors: [],
    dateRange: 'Last 7 days',
    loading: false,
    error: null
};
const dashboardSlice = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createSlice"])({
    name: 'dashboard',
    initialState,
    reducers: {
        setDateRange (state, action) {
            state.dateRange = action.payload;
        },
        resetDashboard (state) {
            state.stats = initialState.stats;
            state.rankTrend = [];
            state.competitors = [];
            state.loading = false;
            state.error = null;
        }
    },
    extraReducers: (builder)=>{
        builder.addCase(fetchDashboardByProject.pending, (state)=>{
            state.loading = true;
            state.error = null;
        }).addCase(fetchDashboardByProject.fulfilled, (state, action)=>{
            state.loading = false;
            state.error = null;
            const data = action.payload || {};
            state.stats = data.stats || initialState.stats;
            state.rankTrend = data.rankTrend || [];
            state.competitors = data.competitors?.items || [];
        }).addCase(fetchDashboardByProject.rejected, (state, action)=>{
            state.loading = false;
            state.error = action.payload || 'Failed to load dashboard';
        });
    }
});
const { setDateRange, resetDashboard } = dashboardSlice.actions;
const __TURBOPACK__default__export__ = dashboardSlice.reducer;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/features/keywords/keywordsSlice.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "addKeywordToProject",
    ()=>addKeywordToProject,
    "bulkAddKeywords",
    ()=>bulkAddKeywords,
    "bulkDeleteKeywords",
    ()=>bulkDeleteKeywords,
    "bulkDeleteRankings",
    ()=>bulkDeleteRankings,
    "clearKeywordMessage",
    ()=>clearKeywordMessage,
    "clearKeywordsState",
    ()=>clearKeywordsState,
    "clearProjectRankings",
    ()=>clearProjectRankings,
    "default",
    ()=>__TURBOPACK__default__export__,
    "deleteKeywordById",
    ()=>deleteKeywordById,
    "deleteRankingById",
    ()=>deleteRankingById,
    "fetchKeywordsByProject",
    ()=>fetchKeywordsByProject,
    "fetchRankingsByProject",
    ()=>fetchRankingsByProject,
    "pollRankingsByProject",
    ()=>pollRankingsByProject,
    "resetKeywordsForProjectChange",
    ()=>resetKeywordsForProjectChange,
    "runRankCheck",
    ()=>runRankCheck,
    "setKeywordSearch",
    ()=>setKeywordSearch,
    "setSortBy",
    ()=>setSortBy
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/@reduxjs/toolkit/dist/redux-toolkit.modern.mjs [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/dashboard/dashboardSlice.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/pricing/pricingSlice.js [app-client] (ecmascript)");
'use client';
;
;
;
;
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
    actionMessage: null
};
const isSameProject = (a, b)=>String(a ?? '') === String(b ?? '');
const fetchKeywordsByProject = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/fetchKeywordsByProject', async (projectId, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/keywords/${projectId}`);
        return {
            projectId,
            rows: response.data || []
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to fetch keywords'
        });
    }
});
const fetchRankingsByProject = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/fetchRankingsByProject', async (projectId, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/rankings/${projectId}`);
        return {
            projectId,
            rows: response.data || []
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to fetch rankings'
        });
    }
});
const addKeywordToProject = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/addKeywordToProject', async ({ projectId, payload }, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/keywords/${projectId}`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            await Promise.all([
                thunkAPI.dispatch(fetchKeywordsByProject(projectId)),
                thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
            ]);
        }
        await thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchCurrentPricing"])());
        return {
            projectId,
            message: response.message || 'Keyword added successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to add keyword'
        });
    }
});
const deleteKeywordById = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/deleteKeywordById', async ({ keywordId, projectId }, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/keywords/${keywordId}`, {
            method: 'DELETE'
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            try {
                await Promise.all([
                    thunkAPI.dispatch(fetchKeywordsByProject(projectId)),
                    thunkAPI.dispatch(fetchRankingsByProject(projectId)),
                    thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
                ]);
            } catch (refreshError) {
                console.warn('Failed to refresh data after keyword delete:', refreshError);
            }
        }
        try {
            await thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchCurrentPricing"])());
        } catch (refreshError) {
            console.warn('Failed to refresh pricing after keyword delete:', refreshError);
        }
        return {
            projectId,
            message: response.message || 'Keyword deleted successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to delete keyword'
        });
    }
});
const deleteRankingById = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/deleteRankingById', async ({ rankingId, projectId }, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/rankings/${rankingId}`, {
            method: 'DELETE'
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            try {
                await Promise.all([
                    thunkAPI.dispatch(fetchRankingsByProject(projectId)),
                    thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
                ]);
            } catch (refreshError) {
                console.warn('Failed to refresh data after ranking delete:', refreshError);
            }
        }
        return {
            projectId,
            message: response.message || 'Ranking deleted successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to delete ranking'
        });
    }
});
const clearProjectRankings = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/clearProjectRankings', async (projectId, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/rankings/project/${projectId}`, {
            method: 'DELETE'
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            try {
                await Promise.all([
                    thunkAPI.dispatch(fetchRankingsByProject(projectId)),
                    thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
                ]);
            } catch (refreshError) {
                console.warn('Failed to refresh data after clearing rankings:', refreshError);
            }
        }
        return {
            projectId,
            message: response.message || 'Rankings cleared successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to clear rankings'
        });
    }
});
const bulkAddKeywords = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/bulkAddKeywords', async ({ projectId, keywords }, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/keywords/${projectId}/bulk`, {
            method: 'POST',
            body: JSON.stringify({
                keywords
            })
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            await Promise.all([
                thunkAPI.dispatch(fetchKeywordsByProject(projectId)),
                thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
            ]);
        }
        await thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchCurrentPricing"])());
        return {
            projectId,
            message: response.message || 'Keywords added successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to add keywords'
        });
    }
});
const bulkDeleteKeywords = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/bulkDeleteKeywords', async ({ projectId, keywordIds }, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/keywords/bulk`, {
            method: 'DELETE',
            body: JSON.stringify({
                keyword_ids: keywordIds
            })
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            try {
                await Promise.all([
                    thunkAPI.dispatch(fetchKeywordsByProject(projectId)),
                    thunkAPI.dispatch(fetchRankingsByProject(projectId)),
                    thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
                ]);
            } catch (refreshError) {
                console.warn('Failed to refresh data after bulk keyword delete:', refreshError);
            }
        }
        try {
            await thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchCurrentPricing"])());
        } catch (refreshError) {
            console.warn('Failed to refresh pricing after bulk keyword delete:', refreshError);
        }
        return {
            projectId,
            message: response.message || 'Keywords deleted successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to delete keywords'
        });
    }
});
const bulkDeleteRankings = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/bulkDeleteRankings', async ({ projectId, rankingIds }, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/rankings/bulk`, {
            method: 'DELETE',
            body: JSON.stringify({
                ranking_ids: rankingIds
            })
        });
        const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
        if (isSameProject(selectedProjectId, projectId)) {
            try {
                await Promise.all([
                    thunkAPI.dispatch(fetchRankingsByProject(projectId)),
                    thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId))
                ]);
            } catch (refreshError) {
                console.warn('Failed to refresh data after bulk ranking delete:', refreshError);
            }
        }
        return {
            projectId,
            message: response.message || 'Rankings deleted successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to delete rankings'
        });
    }
});
const pollRankingsByProject = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/pollRankingsByProject', async ({ projectId, previousLatestCheckedAt = null, attempts = 10, delayMs = 2500 }, thunkAPI)=>{
    const sleep = (ms)=>new Promise((resolve)=>setTimeout(resolve, ms));
    try {
        const previousTime = previousLatestCheckedAt ? new Date(previousLatestCheckedAt).getTime() : 0;
        for(let i = 0; i < attempts; i += 1){
            const selectedProjectId = thunkAPI.getState().projects.selectedProjectId;
            if (!isSameProject(selectedProjectId, projectId)) {
                return thunkAPI.rejectWithValue({
                    projectId,
                    message: 'Project changed while polling rankings'
                });
            }
            const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/rankings/${projectId}`);
            const rows = response.data || [];
            const latestCheckedAt = rows.length ? Math.max(...rows.map((row)=>new Date(row.checkedAt || row.updatedAt || row.createdAt || 0).getTime())) : 0;
            if (rows.length > 0 && latestCheckedAt > previousTime) {
                return {
                    projectId,
                    rows
                };
            }
            await sleep(delayMs);
        }
        return {
            projectId,
            rows: []
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed while polling rankings'
        });
    }
});
const runRankCheck = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('keywords/runRankCheck', async (projectId, thunkAPI)=>{
    try {
        const state = thunkAPI.getState();
        const selectedProjectId = state.projects.selectedProjectId;
        if (!isSameProject(selectedProjectId, projectId)) {
            return thunkAPI.rejectWithValue({
                projectId,
                message: 'Selected project changed. Please run again.'
            });
        }
        const rankings = state.keywords.rankings || [];
        const previousLatestCheckedAt = rankings.length ? rankings.reduce((latest, row)=>{
            const current = row.checkedAt || row.updatedAt || row.createdAt || null;
            if (!current) return latest;
            if (!latest) return current;
            return new Date(current) > new Date(latest) ? current : latest;
        }, null) : null;
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/rankings/${projectId}/run`, {
            method: 'POST'
        });
        await thunkAPI.dispatch(pollRankingsByProject({
            projectId,
            previousLatestCheckedAt
        }));
        if (isSameProject(selectedProjectId, projectId)) {
            await thunkAPI.dispatch((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$dashboard$2f$dashboardSlice$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchDashboardByProject"])(projectId));
        }
        return {
            projectId,
            message: response.message || 'Rank check queued successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            projectId,
            message: error.message || 'Failed to run rank check'
        });
    }
});
const keywordsSlice = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createSlice"])({
    name: 'keywords',
    initialState,
    reducers: {
        setKeywordSearch: (state, action)=>{
            state.search = action.payload;
        },
        setSortBy: (state, action)=>{
            state.sortBy = action.payload;
        },
        clearKeywordMessage: (state)=>{
            state.error = null;
            state.actionMessage = null;
        },
        clearKeywordsState: ()=>initialState,
        resetKeywordsForProjectChange: (state, action)=>{
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
        }
    },
    extraReducers: (builder)=>{
        builder.addCase(fetchKeywordsByProject.pending, (state, action)=>{
            state.loadingKeywords = true;
            state.error = null;
            state.currentProjectId = action.meta.arg;
            state.keywords = [];
        }).addCase(fetchKeywordsByProject.fulfilled, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.loadingKeywords = false;
            state.keywords = action.payload.rows;
        }).addCase(fetchKeywordsByProject.rejected, (state, action)=>{
            const projectId = action.payload?.projectId ?? action.meta.arg;
            if (!isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.loadingKeywords = false;
            state.error = action.payload?.message || 'Failed to fetch keywords';
        }).addCase(fetchRankingsByProject.pending, (state, action)=>{
            state.loadingRankings = true;
            state.error = null;
            state.currentProjectId = action.meta.arg;
            state.rankings = [];
        }).addCase(fetchRankingsByProject.fulfilled, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.loadingRankings = false;
            state.rankings = action.payload.rows;
        }).addCase(fetchRankingsByProject.rejected, (state, action)=>{
            const projectId = action.payload?.projectId ?? action.meta.arg;
            if (!isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.loadingRankings = false;
            state.error = action.payload?.message || 'Failed to fetch rankings';
        }).addCase(bulkAddKeywords.pending, (state)=>{
            state.adding = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(bulkAddKeywords.fulfilled, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.adding = false;
            state.actionMessage = action.payload.message;
        }).addCase(bulkAddKeywords.rejected, (state, action)=>{
            const projectId = action.payload?.projectId;
            if (projectId && !isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.adding = false;
            state.error = action.payload?.message || 'Failed to add keywords';
        }).addCase(bulkDeleteKeywords.pending, (state)=>{
            state.deletingBulkKeywords = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(bulkDeleteKeywords.fulfilled, (state, action)=>{
            state.deletingBulkKeywords = false;
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.actionMessage = action.payload.message;
        }).addCase(bulkDeleteKeywords.rejected, (state, action)=>{
            state.deletingBulkKeywords = false;
            const projectId = action.payload?.projectId;
            if (projectId && !isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.error = action.payload?.message || 'Failed to delete keywords';
        }).addCase(deleteKeywordById.pending, (state)=>{
            state.deletingKeyword = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(deleteKeywordById.fulfilled, (state, action)=>{
            state.deletingKeyword = false;
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.actionMessage = action.payload.message;
        }).addCase(deleteKeywordById.rejected, (state, action)=>{
            state.deletingKeyword = false;
            const projectId = action.payload?.projectId;
            if (projectId && !isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.error = action.payload?.message || 'Failed to delete keyword';
        }).addCase(bulkDeleteRankings.pending, (state)=>{
            state.deletingBulkRankings = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(bulkDeleteRankings.fulfilled, (state, action)=>{
            state.deletingBulkRankings = false;
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.actionMessage = action.payload.message;
        }).addCase(bulkDeleteRankings.rejected, (state, action)=>{
            state.deletingBulkRankings = false;
            const projectId = action.payload?.projectId;
            if (projectId && !isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.error = action.payload?.message || 'Failed to delete rankings';
        }).addCase(deleteRankingById.pending, (state)=>{
            state.deletingRanking = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(deleteRankingById.fulfilled, (state, action)=>{
            state.deletingRanking = false;
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.actionMessage = action.payload.message;
        }).addCase(deleteRankingById.rejected, (state, action)=>{
            state.deletingRanking = false;
            const projectId = action.payload?.projectId;
            if (projectId && !isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.error = action.payload?.message || 'Failed to delete ranking';
        }).addCase(clearProjectRankings.pending, (state)=>{
            state.clearingRankings = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(clearProjectRankings.fulfilled, (state, action)=>{
            state.clearingRankings = false;
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.actionMessage = action.payload.message;
        }).addCase(clearProjectRankings.rejected, (state, action)=>{
            state.clearingRankings = false;
            const projectId = action.payload?.projectId;
            if (projectId && !isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.error = action.payload?.message || 'Failed to clear rankings';
        }).addCase(runRankCheck.pending, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.meta.arg)) {
                return;
            }
            state.running = true;
            state.loadingRankings = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(runRankCheck.fulfilled, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.running = false;
            state.loadingRankings = false;
            state.actionMessage = action.payload.message;
        }).addCase(runRankCheck.rejected, (state, action)=>{
            const projectId = action.payload?.projectId ?? action.meta.arg;
            if (!isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.running = false;
            state.loadingRankings = false;
            state.error = action.payload?.message || 'Failed to run rank check';
        }).addCase(pollRankingsByProject.pending, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.meta.arg.projectId)) {
                return;
            }
            state.loadingRankings = true;
            state.error = null;
        }).addCase(pollRankingsByProject.fulfilled, (state, action)=>{
            if (!isSameProject(state.currentProjectId, action.payload.projectId)) {
                return;
            }
            state.rankings = action.payload.rows;
            state.loadingRankings = false;
        }).addCase(pollRankingsByProject.rejected, (state, action)=>{
            const projectId = action.payload?.projectId ?? action.meta.arg?.projectId;
            if (!isSameProject(state.currentProjectId, projectId)) {
                return;
            }
            state.loadingRankings = false;
            if (action.payload?.message !== 'Project changed while polling rankings') {
                state.error = action.payload?.message || 'Failed while polling rankings';
            }
        });
    }
});
const { setKeywordSearch, setSortBy, clearKeywordMessage, clearKeywordsState, resetKeywordsForProjectChange } = keywordsSlice.actions;
const __TURBOPACK__default__export__ = keywordsSlice.reducer;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/features/pricing/pricingApi.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "changePlanApi",
    ()=>changePlanApi,
    "checkPlanChangeApi",
    ()=>checkPlanChangeApi,
    "createPaymentOrderApi",
    ()=>createPaymentOrderApi,
    "fetchCurrentPricingApi",
    ()=>fetchCurrentPricingApi,
    "fetchInvoicesApi",
    ()=>fetchInvoicesApi,
    "fetchPlansApi",
    ()=>fetchPlansApi,
    "getSubscriptionStatusApi",
    ()=>getSubscriptionStatusApi,
    "markPaymentFailedApi",
    ()=>markPaymentFailedApi,
    "verifyPaymentApi",
    ()=>verifyPaymentApi
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.js [app-client] (ecmascript)");
'use client';
;
const fetchPlansApi = async ()=>{
    const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])("/pricing/plans");
    return response || {
        success: true,
        data: [],
        message: "Plans fetched"
    };
};
const fetchCurrentPricingApi = async ()=>{
    const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])("/pricing/current");
    return response.data || null;
};
const checkPlanChangeApi = async (plan)=>{
    const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/pricing/downgrade-check?plan=${encodeURIComponent(plan)}`);
    return response.data || null;
};
const changePlanApi = async (plan)=>{
    const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])("/pricing/change-plan", {
        method: "POST",
        body: JSON.stringify({
            plan
        })
    });
    return response.data || null;
};
const createPaymentOrderApi = async (planId, amount)=>{
    const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/payments/create-order?plan_id=${planId}&amount=${amount}`, {
        method: "POST"
    });
    // Backend returns the order data directly (not wrapped in { success, message, data })
    return response || null;
};
const verifyPaymentApi = async (orderId, paymentId, signature, planId, creditApplied = 0)=>{
    const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])("/payments/verify-payment", {
        method: "POST",
        body: JSON.stringify({
            razorpay_order_id: orderId,
            razorpay_payment_id: paymentId,
            razorpay_signature: signature,
            plan_id: planId,
            credit_applied: creditApplied
        })
    });
    return response || null;
};
const getSubscriptionStatusApi = async ()=>{
    const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])("/payments/subscription-status");
    return response.data || null;
};
const fetchInvoicesApi = async ()=>{
    const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])("/payments/invoices");
    return response.data || {
        invoices: [],
        credit_balance: 0
    };
};
const markPaymentFailedApi = async (orderId)=>{
    const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])("/payments/mark-failed", {
        method: "POST",
        body: JSON.stringify({
            razorpay_order_id: orderId
        })
    });
    return response || null;
};
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/features/pricing/pricingSlice.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "changePlan",
    ()=>changePlan,
    "checkPlanChange",
    ()=>checkPlanChange,
    "clearPricingError",
    ()=>clearPricingError,
    "default",
    ()=>__TURBOPACK__default__export__,
    "fetchCurrentPricing",
    ()=>fetchCurrentPricing,
    "fetchPricingPlans",
    ()=>fetchPricingPlans
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/@reduxjs/toolkit/dist/redux-toolkit.modern.mjs [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingApi$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/features/pricing/pricingApi.js [app-client] (ecmascript)");
'use client';
;
;
const fetchPricingPlans = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])("pricing/fetchPlans", async (_, thunkAPI)=>{
    try {
        return await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingApi$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchPlansApi"])();
    } catch (error) {
        return thunkAPI.rejectWithValue(error.message || "Failed to fetch plans");
    }
});
const fetchCurrentPricing = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])("pricing/fetchCurrent", async (_, thunkAPI)=>{
    try {
        return await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingApi$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["fetchCurrentPricingApi"])();
    } catch (error) {
        return thunkAPI.rejectWithValue(error.message || "Failed to fetch current pricing");
    }
});
const checkPlanChange = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])("pricing/checkPlanChange", async (plan, thunkAPI)=>{
    try {
        const result = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingApi$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["checkPlanChangeApi"])(plan);
        return {
            plan,
            result
        };
    } catch (error) {
        return thunkAPI.rejectWithValue({
            plan,
            message: error.message || "Failed to validate plan change"
        });
    }
});
const changePlan = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])("pricing/changePlan", async (plan, thunkAPI)=>{
    try {
        const result = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$features$2f$pricing$2f$pricingApi$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["changePlanApi"])(plan);
        return result;
    } catch (error) {
        return thunkAPI.rejectWithValue({
            message: error.message || "Failed to change plan",
            data: error.data || null
        });
    }
});
const initialState = {
    plans: [],
    current: null,
    trialDays: 10,
    loadingPlans: false,
    loadingCurrent: false,
    changingPlan: false,
    error: null,
    changePlanValidation: {}
};
const pricingSlice = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createSlice"])({
    name: "pricing",
    initialState,
    reducers: {
        clearPricingError (state) {
            state.error = null;
        }
    },
    extraReducers: (builder)=>{
        builder.addCase(fetchPricingPlans.pending, (state)=>{
            state.loadingPlans = true;
            state.error = null;
        }).addCase(fetchPricingPlans.fulfilled, (state, action)=>{
            state.loadingPlans = false;
            state.plans = action.payload?.data || [];
            state.trialDays = action.payload?.trialDays || 10;
        }).addCase(fetchPricingPlans.rejected, (state, action)=>{
            state.loadingPlans = false;
            state.error = action.payload || "Failed to fetch plans";
        }).addCase(fetchCurrentPricing.pending, (state)=>{
            state.loadingCurrent = true;
            state.error = null;
        }).addCase(fetchCurrentPricing.fulfilled, (state, action)=>{
            state.loadingCurrent = false;
            state.current = action.payload || null;
        }).addCase(fetchCurrentPricing.rejected, (state, action)=>{
            state.loadingCurrent = false;
            state.error = action.payload || "Failed to fetch current pricing";
        }).addCase(checkPlanChange.fulfilled, (state, action)=>{
            state.changePlanValidation[action.payload.plan] = action.payload.result;
        }).addCase(checkPlanChange.rejected, (state, action)=>{
            const plan = action.payload?.plan;
            if (plan) {
                state.changePlanValidation[plan] = {
                    allowed: false,
                    violations: [],
                    message: action.payload?.message || "Failed to validate plan change"
                };
            }
        }).addCase(changePlan.pending, (state)=>{
            state.changingPlan = true;
            state.error = null;
        }).addCase(changePlan.fulfilled, (state, action)=>{
            state.changingPlan = false;
            state.current = action.payload || null;
        }).addCase(changePlan.rejected, (state, action)=>{
            state.changingPlan = false;
            state.error = action.payload?.message || "Failed to change plan";
        });
    }
});
const { clearPricingError } = pricingSlice.actions;
const __TURBOPACK__default__export__ = pricingSlice.reducer;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/features/projects/projectsSlice.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "clearProjectMessage",
    ()=>clearProjectMessage,
    "clearSelectedProjectId",
    ()=>clearSelectedProjectId,
    "createProject",
    ()=>createProject,
    "default",
    ()=>__TURBOPACK__default__export__,
    "deleteProjectById",
    ()=>deleteProjectById,
    "fetchProjects",
    ()=>fetchProjects,
    "setSelectedProjectId",
    ()=>setSelectedProjectId,
    "updateProject",
    ()=>updateProject
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/@reduxjs/toolkit/dist/redux-toolkit.modern.mjs [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.js [app-client] (ecmascript)");
'use client';
;
;
const STORAGE_KEY = 'selectedProjectId';
const getStoredSelectedProjectId = ()=>{
    try {
        const value = localStorage.getItem(STORAGE_KEY);
        return value ? String(value) : null;
    } catch  {
        return null;
    }
};
const setStoredSelectedProjectId = (projectId)=>{
    try {
        if (projectId !== null && projectId !== undefined && String(projectId).trim() !== '') {
            localStorage.setItem(STORAGE_KEY, String(projectId));
        } else {
            localStorage.removeItem(STORAGE_KEY);
        }
    } catch  {
    //
    }
};
const resolveSelectedProjectId = (projects, preferredId)=>{
    if (!Array.isArray(projects) || projects.length === 0) {
        return null;
    }
    if (preferredId && projects.some((project)=>String(project.id) === String(preferredId))) {
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
    actionMessage: null
};
const fetchProjects = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('projects/fetchProjects', async (_, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])('/projects');
        return response.data || [];
    } catch (error) {
        return thunkAPI.rejectWithValue(error.message || 'Failed to fetch projects');
    }
});
const createProject = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('projects/createProject', async (payload, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])('/projects', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        const createdProject = response.data;
        await thunkAPI.dispatch(fetchProjects());
        return createdProject;
    } catch (error) {
        return thunkAPI.rejectWithValue(error.message || 'Failed to create project');
    }
});
const deleteProjectById = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('projects/deleteProjectById', async (projectId, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/projects/${projectId}`, {
            method: 'DELETE'
        });
        return {
            projectId,
            message: response.message || 'Project deleted successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue(error.message || 'Failed to delete project');
    }
});
const updateProject = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])('projects/updateProject', async ({ projectId, payload }, thunkAPI)=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])(`/projects/${projectId}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        return {
            project: response.data,
            message: response.message || 'Project updated successfully'
        };
    } catch (error) {
        return thunkAPI.rejectWithValue(error.message || 'Failed to update project');
    }
});
const projectsSlice = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createSlice"])({
    name: 'projects',
    initialState,
    reducers: {
        setSelectedProjectId: (state, action)=>{
            state.selectedProjectId = action.payload ? String(action.payload) : null;
            setStoredSelectedProjectId(state.selectedProjectId);
        },
        clearSelectedProjectId: (state)=>{
            state.selectedProjectId = null;
            setStoredSelectedProjectId(null);
        },
        clearProjectMessage: (state)=>{
            state.error = null;
            state.actionMessage = null;
        }
    },
    extraReducers: (builder)=>{
        builder.addCase(fetchProjects.pending, (state)=>{
            state.loading = true;
            state.error = null;
        }).addCase(fetchProjects.fulfilled, (state, action)=>{
            state.loading = false;
            state.list = action.payload;
            const storedProjectId = getStoredSelectedProjectId();
            const preferredId = state.selectedProjectId || storedProjectId;
            state.selectedProjectId = resolveSelectedProjectId(action.payload, preferredId);
            setStoredSelectedProjectId(state.selectedProjectId);
        }).addCase(fetchProjects.rejected, (state, action)=>{
            state.loading = false;
            state.error = action.payload || 'Failed to fetch projects';
        }).addCase(createProject.pending, (state)=>{
            state.creating = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(createProject.fulfilled, (state, action)=>{
            state.creating = false;
            state.actionMessage = 'Project created successfully';
            if (action.payload?.id) {
                state.selectedProjectId = String(action.payload.id);
                setStoredSelectedProjectId(state.selectedProjectId);
            }
        }).addCase(createProject.rejected, (state, action)=>{
            state.creating = false;
            state.error = action.payload || 'Failed to create project';
        }).addCase(updateProject.pending, (state)=>{
            state.updating = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(updateProject.fulfilled, (state, action)=>{
            state.updating = false;
            const index = state.list.findIndex((project)=>String(project.id) === String(action.payload.project.id));
            if (index !== -1) {
                state.list[index] = action.payload.project;
            }
            state.actionMessage = action.payload.message;
        }).addCase(updateProject.rejected, (state, action)=>{
            state.updating = false;
            state.error = action.payload || 'Failed to update project';
        }).addCase(deleteProjectById.pending, (state)=>{
            state.deleting = true;
            state.error = null;
            state.actionMessage = null;
        }).addCase(deleteProjectById.fulfilled, (state, action)=>{
            state.deleting = false;
            state.list = state.list.filter((project)=>String(project.id) !== String(action.payload.projectId));
            state.actionMessage = action.payload.message;
            if (String(state.selectedProjectId) === String(action.payload.projectId)) {
                state.selectedProjectId = resolveSelectedProjectId(state.list, null);
                setStoredSelectedProjectId(state.selectedProjectId);
            }
        }).addCase(deleteProjectById.rejected, (state, action)=>{
            state.deleting = false;
            state.error = action.payload || 'Failed to delete project';
        });
    }
});
const { setSelectedProjectId, clearSelectedProjectId, clearProjectMessage } = projectsSlice.actions;
const __TURBOPACK__default__export__ = projectsSlice.reducer;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/features/subscription/subscriptionSlice.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>__TURBOPACK__default__export__,
    "fetchSubscriptionStatus",
    ()=>fetchSubscriptionStatus
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/@reduxjs/toolkit/dist/redux-toolkit.modern.mjs [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.js [app-client] (ecmascript)");
'use client';
;
;
const fetchSubscriptionStatus = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAsyncThunk"])("subscription/fetchStatus", async (_, { rejectWithValue })=>{
    try {
        const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["apiRequest"])("/pricing/subscription-status");
        return response.data;
    } catch (error) {
        return rejectWithValue(error.message);
    }
});
const subscriptionSlice = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$reduxjs$2f$toolkit$2f$dist$2f$redux$2d$toolkit$2e$modern$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createSlice"])({
    name: "subscription",
    initialState: {
        status: null,
        loading: false,
        error: null,
        data: {
            plan: null,
            effectivePlan: null,
            subscriptionStatus: null,
            trialStartsAt: null,
            trialEndsAt: null,
            gracePeriodEndsAt: null,
            isInGracePeriod: false,
            trialDays: 10,
            usage: {
                projects: 0,
                keywords: 0,
                reportsThisMonth: 0,
                maxCompetitorsPerProject: 0
            },
            limits: {
                projects: 0,
                keywords: 0,
                competitorsPerProject: 0,
                reportsPerMonth: 0,
                teamMembers: 0
            },
            creditBalance: 0
        }
    },
    reducers: {},
    extraReducers: (builder)=>{
        builder.addCase(fetchSubscriptionStatus.pending, (state)=>{
            state.loading = true;
            state.error = null;
        }).addCase(fetchSubscriptionStatus.fulfilled, (state, action)=>{
            state.loading = false;
            state.data = action.payload;
        }).addCase(fetchSubscriptionStatus.rejected, (state, action)=>{
            state.loading = false;
            state.error = action.payload;
        });
    }
});
const __TURBOPACK__default__export__ = subscriptionSlice.reducer;
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/lib/api.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "acceptTeamInviteApi",
    ()=>acceptTeamInviteApi,
    "addKeywordsToListApi",
    ()=>addKeywordsToListApi,
    "apiRequest",
    ()=>apiRequest,
    "cancelTeamInviteApi",
    ()=>cancelTeamInviteApi,
    "competitorSpyApi",
    ()=>competitorSpyApi,
    "createApiKeyApi",
    ()=>createApiKeyApi,
    "createKeywordListApi",
    ()=>createKeywordListApi,
    "createScheduledReportApi",
    ()=>createScheduledReportApi,
    "createTeamApi",
    ()=>createTeamApi,
    "deactivateApiKeyApi",
    ()=>deactivateApiKeyApi,
    "deleteApiKeyApi",
    ()=>deleteApiKeyApi,
    "deleteKeywordListApi",
    ()=>deleteKeywordListApi,
    "deleteScheduledReportApi",
    ()=>deleteScheduledReportApi,
    "deleteTeamApi",
    ()=>deleteTeamApi,
    "exportKeywordListApi",
    ()=>exportKeywordListApi,
    "forgotPasswordApi",
    ()=>forgotPasswordApi,
    "getAgencyOverviewApi",
    ()=>getAgencyOverviewApi,
    "getAioCitationsApi",
    ()=>getAioCitationsApi,
    "getAioDashboardApi",
    ()=>getAioDashboardApi,
    "getCompetitorComparisonApi",
    ()=>getCompetitorComparisonApi,
    "getKeywordsWithSerpFeaturesApi",
    ()=>getKeywordsWithSerpFeaturesApi,
    "getLHFOpportunitiesApi",
    ()=>getLHFOpportunitiesApi,
    "getLHFSummaryApi",
    ()=>getLHFSummaryApi,
    "getProjectComparisonApi",
    ()=>getProjectComparisonApi,
    "getRazorpayKey",
    ()=>getRazorpayKey,
    "getRoiMetricsApi",
    ()=>getRoiMetricsApi,
    "getSerpFeaturesForKeywordApi",
    ()=>getSerpFeaturesForKeywordApi,
    "getSerpFeaturesSummaryApi",
    ()=>getSerpFeaturesSummaryApi,
    "getTeamApi",
    ()=>getTeamApi,
    "getTeamInvitesApi",
    ()=>getTeamInvitesApi,
    "getTeamMembersApi",
    ()=>getTeamMembersApi,
    "initRazorpayCheckout",
    ()=>initRazorpayCheckout,
    "inviteTeamMemberApi",
    ()=>inviteTeamMemberApi,
    "listApiKeysApi",
    ()=>listApiKeysApi,
    "listKeywordListsApi",
    ()=>listKeywordListsApi,
    "listScheduledReportsApi",
    ()=>listScheduledReportsApi,
    "listTeamsApi",
    ()=>listTeamsApi,
    "onboardProjectApi",
    ()=>onboardProjectApi,
    "registerApi",
    ()=>registerApi,
    "removeKeywordFromListApi",
    ()=>removeKeywordFromListApi,
    "removeTeamMemberApi",
    ()=>removeTeamMemberApi,
    "researchKeywordApi",
    ()=>researchKeywordApi,
    "resendVerificationApi",
    ()=>resendVerificationApi,
    "resetPasswordApi",
    ()=>resetPasswordApi,
    "searchGlobal",
    ()=>searchGlobal,
    "setRazorpayKey",
    ()=>setRazorpayKey,
    "syncSerpFeaturesApi",
    ()=>syncSerpFeaturesApi,
    "trackAioApi",
    ()=>trackAioApi,
    "trackCompetitorRankingsApi",
    ()=>trackCompetitorRankingsApi,
    "updateScheduledReportApi",
    ()=>updateScheduledReportApi,
    "updateTeamMemberRoleApi",
    ()=>updateTeamMemberRoleApi,
    "verifyEmailApi",
    ()=>verifyEmailApi
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
'use client';
const API_BASE_URL = ("TURBOPACK compile-time value", "http://localhost:4000/api") || '/api';
// Razorpay configuration - will be loaded from backend
let razorpayKey = null;
function setRazorpayKey(key) {
    razorpayKey = key;
}
function getRazorpayKey() {
    return razorpayKey;
}
async function parseJsonSafe(response) {
    try {
        return await response.json();
    } catch  {
        return null;
    }
}
async function verifyEmailApi(token) {
    const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            token
        })
    });
    const result = await parseJsonSafe(response);
    if (!response.ok || !result?.success) {
        throw new Error(result?.message || "Email verification failed");
    }
    return result;
}
async function resendVerificationApi(email) {
    const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email
        })
    });
    const result = await parseJsonSafe(response);
    if (!response.ok || !result?.success) {
        throw new Error(result?.message || "Failed to resend verification email");
    }
    return result;
}
async function forgotPasswordApi(email) {
    const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email
        })
    });
    const result = await parseJsonSafe(response);
    if (!response.ok || !result?.success) {
        throw new Error(result?.message || "Failed to send password reset email");
    }
    return result;
}
async function resetPasswordApi(token, newPassword) {
    const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            token,
            newPassword
        })
    });
    const result = await parseJsonSafe(response);
    if (!response.ok || !result?.success) {
        throw new Error(result?.message || "Failed to reset password");
    }
    return result;
}
async function researchKeywordApi(keyword, location = "India") {
    return apiRequest(`/keyword-research/research?keyword=${encodeURIComponent(keyword)}&location=${encodeURIComponent(location)}`);
}
async function competitorSpyApi(domain, location = "India", limit = 100) {
    return apiRequest(`/keyword-research/competitor-spy?domain=${encodeURIComponent(domain)}&location=${encodeURIComponent(location)}&limit=${limit}`);
}
async function onboardProjectApi({ name, domain, location, keywords }) {
    const params = new URLSearchParams();
    params.set('name', name);
    params.set('domain', domain);
    params.set('location', location);
    keywords.forEach((kw)=>params.append('keywords', kw));
    return apiRequest(`/keyword-research/project/onboard?${params.toString()}`, {
        method: "POST"
    });
}
async function createKeywordListApi(name) {
    return apiRequest('/keyword-lists/', {
        method: "POST",
        body: JSON.stringify({
            name
        })
    });
}
async function listKeywordListsApi() {
    return apiRequest('/keyword-lists/');
}
async function addKeywordsToListApi(listId, keywords) {
    return apiRequest(`/keyword-lists/${listId}/items`, {
        method: "POST",
        body: JSON.stringify({
            keywords
        })
    });
}
async function removeKeywordFromListApi(listId, itemId) {
    return apiRequest(`/keyword-lists/${listId}/items/${itemId}`, {
        method: "DELETE"
    });
}
async function deleteKeywordListApi(listId) {
    return apiRequest(`/keyword-lists/${listId}`, {
        method: "DELETE"
    });
}
async function exportKeywordListApi(listId) {
    return apiRequest(`/keyword-lists/${listId}/export`);
}
async function trackCompetitorRankingsApi(projectId) {
    return apiRequest(`/competitor-rankings/${projectId}/track`, {
        method: "POST"
    });
}
async function getCompetitorComparisonApi(projectId) {
    return apiRequest(`/competitor-rankings/${projectId}/comparison`);
}
async function trackAioApi(projectId) {
    return apiRequest(`/aio/${projectId}/track`, {
        method: "POST"
    });
}
async function getAioDashboardApi(projectId) {
    return apiRequest(`/aio/${projectId}/dashboard`);
}
async function getAioCitationsApi(projectId) {
    return apiRequest(`/aio/${projectId}/citations`);
}
async function getLHFOpportunitiesApi(projectId, limit = 20) {
    return apiRequest(`/lhf/opportunities?project_id=${projectId}&limit=${limit}`);
}
async function getLHFSummaryApi(projectId) {
    return apiRequest(`/lhf/summary?project_id=${projectId}`);
}
async function getSerpFeaturesForKeywordApi(projectId, keyword) {
    return apiRequest(`/serp-features/keyword?project_id=${projectId}&keyword=${encodeURIComponent(keyword)}`);
}
async function getSerpFeaturesSummaryApi(projectId) {
    return apiRequest(`/serp-features/summary?project_id=${projectId}`);
}
async function getKeywordsWithSerpFeaturesApi(projectId, limit = 50) {
    return apiRequest(`/serp-features/keywords?project_id=${projectId}&limit=${limit}`);
}
async function syncSerpFeaturesApi(projectId) {
    return apiRequest(`/serp-features/sync?project_id=${projectId}`, {
        method: "POST"
    });
}
async function createApiKeyApi(name, expiresInDays) {
    return apiRequest('/api-keys/create', {
        method: "POST",
        body: JSON.stringify({
            name,
            expires_in_days: expiresInDays
        })
    });
}
async function listApiKeysApi() {
    return apiRequest('/api-keys/list');
}
async function deactivateApiKeyApi(apiKeyId) {
    return apiRequest(`/api-keys/${apiKeyId}/deactivate`, {
        method: "POST"
    });
}
async function deleteApiKeyApi(apiKeyId) {
    return apiRequest(`/api-keys/${apiKeyId}`, {
        method: "DELETE"
    });
}
async function createScheduledReportApi(projectId, name, frequency, format, recipients, startDate) {
    const body = {
        project_id: projectId,
        name,
        frequency,
        format,
        recipients
    };
    if (startDate) {
        body.start_date = startDate;
    }
    return apiRequest('/scheduled-reports/create', {
        method: "POST",
        body: JSON.stringify(body)
    });
}
async function listScheduledReportsApi() {
    return apiRequest('/scheduled-reports/list');
}
async function updateScheduledReportApi(reportId, updates) {
    return apiRequest(`/scheduled-reports/${reportId}`, {
        method: "PUT",
        body: JSON.stringify(updates)
    });
}
async function deleteScheduledReportApi(reportId) {
    return apiRequest(`/scheduled-reports/${reportId}`, {
        method: "DELETE"
    });
}
async function createTeamApi(name) {
    return apiRequest('/teams/create', {
        method: "POST",
        body: JSON.stringify({
            name
        })
    });
}
async function listTeamsApi() {
    return apiRequest('/teams/list');
}
async function getTeamApi(teamId) {
    return apiRequest(`/teams/${teamId}`);
}
async function getTeamMembersApi(teamId) {
    return apiRequest(`/teams/${teamId}/members`);
}
async function inviteTeamMemberApi(teamId, email, role) {
    return apiRequest(`/teams/${teamId}/invite`, {
        method: "POST",
        body: JSON.stringify({
            email,
            role
        })
    });
}
async function updateTeamMemberRoleApi(teamId, userId, role) {
    return apiRequest(`/teams/${teamId}/members/${userId}/role`, {
        method: "PUT",
        body: JSON.stringify({
            role
        })
    });
}
async function removeTeamMemberApi(teamId, userId) {
    return apiRequest(`/teams/${teamId}/members/${userId}`, {
        method: "DELETE"
    });
}
async function deleteTeamApi(teamId) {
    return apiRequest(`/teams/${teamId}`, {
        method: "DELETE"
    });
}
async function getTeamInvitesApi(teamId) {
    return apiRequest(`/teams/${teamId}/invites`);
}
async function acceptTeamInviteApi(teamId, inviteId) {
    return apiRequest(`/teams/${teamId}/invites/${inviteId}/accept`, {
        method: "POST"
    });
}
async function cancelTeamInviteApi(teamId, inviteId) {
    return apiRequest(`/teams/${teamId}/invites/${inviteId}`, {
        method: "DELETE"
    });
}
async function getAgencyOverviewApi() {
    return apiRequest('/agency-dashboard/overview');
}
async function getProjectComparisonApi() {
    return apiRequest('/agency-dashboard/comparison');
}
async function getRoiMetricsApi() {
    return apiRequest('/agency-dashboard/roi');
}
const apiRequest = async (endpoint, options = {})=>{
    let token = null;
    try {
        token = localStorage.getItem('accessToken');
    } catch  {
        token = null;
    }
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...token ? {
                Authorization: `Bearer ${token}`
            } : {},
            ...options.headers || {}
        }
    });
    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    let data;
    if (isJson) {
        data = await response.json();
    } else {
        const text = await response.text();
        throw new Error(`API did not return JSON. Status: ${response.status}. Response: ${text.slice(0, 120)}`);
    }
    if (!response.ok) {
        const errorMessage = data.message || (typeof data.detail === 'string' ? data.detail : null) || 'Request failed';
        throw new Error(errorMessage);
    }
    return data;
};
const searchGlobal = async ({ query, projectId })=>{
    const params = new URLSearchParams();
    params.set('q', query);
    if (projectId) {
        params.set('projectId', projectId);
    }
    return apiRequest(`/search?${params.toString()}`);
};
async function registerApi(payload) {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });
    const result = await parseJsonSafe(response);
    if (!response.ok || !result?.success) {
        throw new Error(result?.message || "Registration failed");
    }
    return result;
}
async function initRazorpayCheckout(options) {
    const { order_id, amount, currency, key_id, onPaymentSuccess, onPaymentError } = options;
    // Store the key for later use
    setRazorpayKey(key_id);
    // Check if Razorpay script is loaded
    if (typeof window.Razorpay === 'undefined') {
        // Load Razorpay script dynamically
        await new Promise((resolve, reject)=>{
            const script = document.createElement('script');
            script.src = 'https://checkout.razorpay.com/v1/checkout.js';
            script.onload = resolve;
            script.onerror = ()=>reject(new Error('Failed to load Razorpay SDK'));
            document.body.appendChild(script);
        });
    }
    // Track whether payment was already handled to prevent ondismiss from firing error
    let paymentHandled = false;
    const razorpayOptions = {
        key: key_id,
        amount: amount,
        currency: currency,
        name: 'RankCare',
        description: 'SEO Rank Tracking Subscription',
        order_id: order_id,
        handler: function(response) {
            // Mark payment as handled so ondismiss doesn't trigger error
            paymentHandled = true;
            // Payment successful - call the success callback
            onPaymentSuccess(response);
        },
        prefill: {
            name: options.prefill?.name || '',
            email: options.prefill?.email || '',
            contact: options.prefill?.contact || ''
        },
        theme: {
            color: '#4F46E5'
        },
        modal: {
            ondismiss: function() {
                // Only call error callback if payment wasn't already handled
                if (!paymentHandled && onPaymentError) {
                    onPaymentError({
                        error: {
                            description: 'Payment cancelled by user'
                        }
                    });
                }
            }
        }
    };
    const rzp = new window.Razorpay(razorpayOptions);
    rzp.on('payment.failed', function(response) {
        paymentHandled = true;
        if (onPaymentError) {
            onPaymentError(response.error);
        }
    });
    rzp.open();
    return rzp;
}
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=_1zqrh9z._.js.map