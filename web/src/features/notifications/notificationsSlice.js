import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { apiRequest } from "../../lib/api";

const initialState = {
  items: [],
  dropdownItems: [],
  unreadCount: 0,
  loading: false,
  dropdownLoading: false,
  currentRequestId: null,
  actionLoading: false,
  error: null,
  pagination: {
    page: 1,
    limit: 10,
    total: 0,
    totalPages: 0,
  },
};

const getErrorMessage = (error, fallback) =>
  error?.message || fallback;

const normalizeNotification = (item = {}) => ({
  id: item.id,
  userId: item.userId || item.user_id || null,
  title: item.title || "Notification",
  message: item.message || "",
  type: item.type || "system_message",
  status: String(item.status || "UNREAD").toUpperCase(),
  severity: item.severity || "info",
  projectId: item.projectId || item.project_id || null,
  entityType: item.entityType || item.entity_type || null,
  entityId: item.entityId || item.entity_id || null,
  createdAt: item.createdAt || item.created_at || null,
  readAt: item.readAt || item.read_at || null,
  updatedAt: item.updatedAt || item.updated_at || null,
  payload: item.payload || item.metadata || {},
});

const countUnread = (items = []) =>
  items.filter((item) => item.status === "UNREAD").length;

export const fetchNotifications = createAsyncThunk(
  "notifications/fetchNotifications",
  async (params = {}, { rejectWithValue }) => {
    try {
      const query = new URLSearchParams();

      if (params.page) query.append("page", params.page);
      if (params.limit) query.append("limit", params.limit);
      if (params.status && params.status !== "all") {
        query.append("status", String(params.status).toUpperCase());
      }
      if (params.projectId) query.append("projectId", params.projectId);

      const url = query.toString()
        ? `/notifications?${query.toString()}`
        : "/notifications";

      const response = await apiRequest(url);
      const payload = response?.data || {};


      const rawItems = Array.isArray(payload)
        ? payload
        : Array.isArray(payload.items)
          ? payload.items
          : [];

      const items = rawItems.map(normalizeNotification);
      return {
        items,
        pagination: payload.pagination || {
          page: Number(params.page) || 1,
          limit: Number(params.limit) || 10,
          total: items.length,
          totalPages: 1,
        },
        unreadCount:
          typeof payload.unreadCount === "number"
            ? payload.unreadCount
            : countUnread(items),
      };
    } catch (error) {
      return rejectWithValue(
        getErrorMessage(error, "Failed to fetch notifications")
      );
    }
  }
);

export const fetchUnreadCount = createAsyncThunk(
  "notifications/fetchUnreadCount",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiRequest("/notifications/unread-count");
      const payload = response?.data;

      const unreadCount =
        typeof payload === "number"
          ? payload
          : typeof payload?.count === "number"
            ? payload.count
            : typeof payload?.unreadCount === "number"
              ? payload.unreadCount
              : 0;

      return unreadCount;
    } catch (error) {
      return rejectWithValue(
        getErrorMessage(error, "Failed to fetch unread count")
      );
    }
  }
);

export const markNotificationRead = createAsyncThunk(
  "notifications/markNotificationRead",
  async (notificationId, { rejectWithValue }) => {
    try {
      const response = await apiRequest(`/notifications/${notificationId}/read`, {
        method: "PATCH",
      });

      const updated =
        response?.data && typeof response.data === "object"
          ? normalizeNotification(response.data)
          : null;

      return {
        notificationId,
        updated,
      };
    } catch (error) {
      return rejectWithValue(
        getErrorMessage(error, "Failed to mark notification as read")
      );
    }
  }
);

export const markAllNotificationsRead = createAsyncThunk(
  "notifications/markAllNotificationsRead",
  async (_, { rejectWithValue }) => {
    try {
      await apiRequest("/notifications/read-all", {
        method: "PATCH",
      });
      return true;
    } catch (error) {
      return rejectWithValue(
        getErrorMessage(error, "Failed to mark all notifications as read")
      );
    }
  }
);

export const deleteNotification = createAsyncThunk(
  "notifications/deleteNotification",
  async (notificationId, { rejectWithValue }) => {
    try {
      await apiRequest(`/notifications/${notificationId}`, {
        method: "DELETE",
      });
      return notificationId;
    } catch (error) {
      return rejectWithValue(
        getErrorMessage(error, "Failed to delete notification")
      );
    }
  }
);

const notificationsSlice = createSlice({
  name: "notifications",
  initialState,
  reducers: {
    clearNotificationsError: (state) => {
      state.error = null;
    },
    resetNotificationsState: () => initialState,
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchNotifications.pending, (state, action) => {
        state.error = null;
        state.loading = true;
        state.currentRequestId = action.meta.requestId;
      })
      .addCase(fetchNotifications.fulfilled, (state, action) => {
        if (state.currentRequestId !== action.meta.requestId) return;
        state.loading = false;
        state.currentRequestId = null;
        state.items = action.payload.items;
        state.pagination = action.payload.pagination;
        state.unreadCount = action.payload.unreadCount;
      })
      .addCase(fetchNotifications.rejected, (state, action) => {
        if (state.currentRequestId !== action.meta.requestId) return;
        state.loading = false;
        state.currentRequestId = null;
        state.error = action.payload;
      })

      .addCase(fetchUnreadCount.pending, (state) => {
        state.error = null;
      })
      .addCase(fetchUnreadCount.fulfilled, (state, action) => {
        state.unreadCount = action.payload;
      })
      .addCase(fetchUnreadCount.rejected, (state, action) => {
        state.error = action.payload;
      })

      .addCase(markNotificationRead.pending, (state) => {
        state.actionLoading = true;
        state.error = null;
      })
      .addCase(markNotificationRead.fulfilled, (state, action) => {
        state.actionLoading = false;

        const { notificationId, updated } = action.payload;
        const existing = state.items.find((item) => item.id === notificationId);

        if (existing) {
          existing.status = "READ";
          existing.readAt = updated?.readAt || new Date().toISOString();
          existing.updatedAt = updated?.updatedAt || existing.readAt;

          if (updated) {
            existing.title = updated.title ?? existing.title;
            existing.message = updated.message ?? existing.message;
            existing.type = updated.type ?? existing.type;
            existing.severity = updated.severity ?? existing.severity;
            existing.projectId = updated.projectId ?? existing.projectId;
            existing.entityType = updated.entityType ?? existing.entityType;
            existing.entityId = updated.entityId ?? existing.entityId;
            existing.payload = updated.payload ?? existing.payload;
            existing.createdAt = updated.createdAt ?? existing.createdAt;
          }
        }

        state.unreadCount = countUnread(state.items);
      })
      .addCase(markNotificationRead.rejected, (state, action) => {
        state.actionLoading = false;
        state.error = action.payload;
      })

      .addCase(markAllNotificationsRead.pending, (state) => {
        state.actionLoading = true;
        state.error = null;
      })
      .addCase(markAllNotificationsRead.fulfilled, (state) => {
        state.actionLoading = false;
        const now = new Date().toISOString();

        state.items.forEach((item) => {
          item.status = "READ";
          item.readAt = item.readAt || now;
          item.updatedAt = now;
        });

        state.unreadCount = 0;
      })
      .addCase(markAllNotificationsRead.rejected, (state, action) => {
        state.actionLoading = false;
        state.error = action.payload;
      })

      .addCase(deleteNotification.pending, (state) => {
        state.actionLoading = true;
        state.error = null;
      })
      .addCase(deleteNotification.fulfilled, (state, action) => {
        state.actionLoading = false;
        state.items = state.items.filter((item) => item.id !== action.payload);
        state.unreadCount = countUnread(state.items);
      })
      .addCase(deleteNotification.rejected, (state, action) => {
        state.actionLoading = false;
        state.error = action.payload;
      });
  },
});

export const { clearNotificationsError, resetNotificationsState } =
  notificationsSlice.actions;

export default notificationsSlice.reducer;