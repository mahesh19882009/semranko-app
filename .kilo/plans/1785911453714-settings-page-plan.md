# Settings Page Plan

## Goal
Build a comprehensive Settings page at `/dashboard/settings` with profile management, password change, GST info, and notification preferences.

## Current State
- Backend: `/settings/gst` GET/POST exists. No profile, password, or notification endpoints.
- Frontend: No Settings page exists. Sidebar has 9 nav items, no Settings link.
- User model has editable fields: `name`, `dailyKeywordMovement`, `weeklyAuditSummary`, `competitorAlerts`, `refreshFrequency`, plus 5 GST fields.

## Proposed Sections

### 1. Profile Information
- **Display name** (editable input)
- **Email** (read-only, used for login)
- **Current plan** badge (read-only display from existing billing data)
- **Account created** date (read-only)

### 2. Change Password
- Current password, new password, confirm new password
- Requires backend endpoint `POST /settings/change-password` with current password verification

### 3. GST / Billing Information
- Form with: GSTIN, Business Name, Address, State, State Code
- Backend endpoints already exist: `GET /settings/gst`, `POST /settings/gst`
- Shows seller (company) GST details read-only for reference

### 4. Notification Preferences
- Toggle switches for:
  - Daily keyword movement alerts (`dailyKeywordMovement`)
  - Weekly audit summary (`weeklyAuditSummary`)
  - Competitor alerts (`competitorAlerts`)
- Requires backend endpoints `GET /settings/notifications`, `PUT /settings/notifications`

### 5. Refresh Frequency
- Select/dropdown for refresh frequency (currently only "weekly" is implemented)
- Maps to `refreshFrequency` field on User model
- Requires backend endpoint `PUT /settings/refresh-frequency`

## Backend Changes Needed

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/settings/profile` | GET | Return current user name, email, plan info |
| `/settings/profile` | PUT | Update user name |
| `/settings/change-password` | POST | Verify current password, set new password |
| `/settings/notifications` | GET | Return notification prefs |
| `/settings/notifications` | PUT | Update notification prefs |
| `/settings/refresh-frequency` | PUT | Update refreshFrequency |
| `/settings/gst` | GET | Already exists |
| `/settings/gst` | POST | Already exists |

**New service function:** `change_user_password(db, user_id, current_password, new_password)` in `auth_service.py`

## Frontend Changes Needed

| File | Change |
|------|--------|
| `rankcareapp/src/views/SettingsPage.jsx` | **Create** — main page with tabbed/sectioned layout |
| `rankcareapp/app/(auth)/dashboard/settings/page.jsx` | **Create** — Next.js route wrapper |
| `rankcareapp/src/components/SideBar.jsx` | Add Settings nav item with gear icon |
| `rankcareapp/src/features/settings/` | **Create** — Redux slice + API functions for settings |

## Section Layout (Suggested)
```
Settings
├── Profile
│   ├── Display name [input]
│   ├── Email [read-only]
│   └── Plan & Credits [read-only cards]
├── Security
│   └── Change Password [form]
├── Billing & GST
│   ├── Your GST info [form]
│   └── Seller GST info [read-only]
├── Notifications
│   ├── Daily keyword movement [toggle]
│   ├── Weekly audit summary [toggle]
│   └── Competitor alerts [toggle]
└── Data & Account
    └── Refresh frequency [select]
```

## Validation Rules
- Name: required, 2-100 chars
- Password change: current password must match, new password min 8 chars
- GSTIN: optional, validate format if provided (15 chars, alphanumeric)
- Notifications: boolean toggles
- Refresh frequency: enum ["weekly"]

## Out of Scope (Future)
- Account deletion / data export
- Theme preference
- Language / timezone
- API key management
- Two-factor authentication

## Migration
- No DB migration needed — all fields already exist on User model
- No seed data needed

## Validation
- Backend: verify endpoints return correct data, password change works, GST endpoints already tested
- Frontend: verify forms submit, toggles persist, sidebar navigation works
