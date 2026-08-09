# Plan: Remove Team Feature + Add Single-Session Enforcement

## Goal
Remove the team/members feature entirely so every account has exactly one owner. Add lightweight single-session enforcement: only one active login per account at a time; a new login automatically invalidates the previous session.

## Context
- Auth is JWT-based with no session tracking today.
- Redis is already configured and used by `cache_service.py` and `queues/redis_client.py`.
- Database: PostgreSQL (`DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/rankcare`)
- **Current DB state**: `Team` and `TeamMember` tables still exist with 3 teams and 6 members. The `a54a6d764a82_drop_unused_tables.py` migration was created but never applied to this database.
- Team feature currently lives in: `models.py`, `team_service.py`, `routes/teams.py`, `schemas/team.py`, `router.py`, `deps.py`, plus frontend pages and API wrappers.

## 1. Remove Team Feature (backend)
- **Delete** `api/fastapi_app/app/services/team_service.py`
- **Delete** `api/fastapi_app/app/api/routes/teams.py`
- **Delete** `api/fastapi_app/app/schemas/team.py`
- **Edit `api/fastapi_app/app/db/models.py`**: remove `Team`, `TeamMember` classes and User relationships (`ownedTeams`, `teamMemberships`)
- **Edit `api/fastapi_app/app/api/router.py`**: remove `teams_router` import and `include_router(teams_router)`
- **Edit `api/fastapi_app/app/api/deps.py`**: remove `require_team_action`
- **Edit `api/fastapi_app/app/services/plan_service.py`**: remove `teamMembers` references
- **Edit `api/fastapi_app/app/core/config.py`**: remove `"team_member"` from `USER_CREDIT_COSTS`
- **Edit `api/fastapi_app/app/api/routes/keywords.py`, `credits.py`, `tracked_keywords.py`**: remove `from app.services.team_service import get_team_owner_id` and replace `get_team_owner_id(db, user_id)` calls with `user_id` directly (no team = user is always owner)
- **Edit `api/fastapi_app/app/services/keyword_service.py`, `keyword_research_service.py`, `keyword_update_service.py`, `monday_tracker.py`**: same import/call replacement as above

## 2. Remove Team Feature (frontend)
- **Delete** `rankcareapp/src/views/TeamPage.jsx` and `MembersPage.jsx`
- **Delete** `rankcareapp/app/(auth)/dashboard/team/` and `members/` route folders
- **Edit `rankcareapp/src/components/SideBar.jsx`**: remove the Team/Members nav item
- **Edit `rankcareapp/src/features/pricing/pricingApi.js`**: remove team API wrappers (`createTeamApi`, `listTeamsApi`, `getTeamApi`, `addTeamMemberApi`, `updateTeamMemberRoleApi`, `removeTeamMemberApi`, `deleteTeamApi`)
- **Edit `rankcareapp/src/lib/api.js`**: remove team API wrappers
- **Edit `rankcareapp/src/features/subscription/subscriptionSlice.js`**: remove `teamMembers` from limits state
- **Edit `rankcareapp/src/config/pricing.js`**: remove team-member credit items
- **Edit `rankcareapp/src/views/PricingPage.jsx`**: remove "growing SEO teams" copy if present
- **Edit `rankcareapp/src/views/HomePage.jsx`**: remove "SEO teams and agencies" copy if present

## 3. Add Single-Session Enforcement
### 3.1 Session token model
- **Create `api/fastapi_app/app/core/session.py`**:
  - Import `redis_client` from `app.services.cache_service` (already configured with `decode_responses=True`)
  - `generate_session_token() -> str` — `secrets.token_hex(32)`
  - `store_session(user_id: str, token: str) -> None` — key=`rankcare:session:{user_id}`, value=token, TTL=`settings.JWT_ACCESS_EXPIRES_IN_DAYS * 86400`
  - `validate_session(user_id: str, token: str) -> bool` — GET key, compare value, return match
  - `invalidate_session(user_id: str) -> None` — DELETE key

### 3.2 Login flow changes
- **Edit `api/fastapi_app/app/api/routes/auth.py` login endpoint**:
  - After successful `login_user`, call `invalidate_session(user.id)` to clear any existing session
  - Generate `session_token`
  - Call `store_session(user.id, session_token)`
  - Return `accessToken`, `user`, and `sessionToken` in response

### 3.3 Protected endpoint guard
- **Edit `api/fastapi_app/app/api/deps.py`** `get_current_user`:
  - Accept `session_token: Optional[str] = Header(default=None, alias="X-Session-Token")`
  - After loading user from JWT, call `validate_session(user.id, session_token)`
  - If invalid/missing → raise `401 Unauthorized("Session expired or invalid")`
  - Wrap Redis calls in try/except: on Redis failure, **fail closed** (401)

### 3.4 Frontend changes
- **Edit `rankcareapp/src/views/LoginPage.jsx`**:
  - After login, save `sessionToken` to localStorage (`sessionToken` key)
- **Edit `rankcareapp/src/lib/api.js`**:
  - In `apiRequest`, read `sessionToken` from localStorage
  - Attach `X-Session-Token` header to every request
  - Add `logoutApi()` that calls `POST /auth/logout` and clears both `accessToken` and `sessionToken`
- **Edit `rankcareapp/src/utils/auth.js`**:
  - Add `getSessionToken()`, `setSessionToken()`, `clearSessionToken()`

### 3.5 Logout endpoint
- **Edit `api/fastapi_app/app/api/routes/auth.py`**:
  - Add `POST /logout`:
    - Accept `session_token` header
    - Call `invalidate_session(current_user.id)`
    - Return `ok("Logged out")`

## 4. Database Migration
- **Create Alembic migration** `drop_team_tables.py`:
  - `upgrade()`:
    ```sql
    DROP TABLE IF EXISTS "TeamMember" CASCADE;
    DROP TABLE IF EXISTS "Team" CASCADE;
    ```
  - `downgrade()`:
    ```sql
    CREATE TABLE "Team" (...);
    CREATE TABLE "TeamMember" (...);
    ```
- Down-revision: latest current migration (`aio_rankresult_extras`)
- **Warning**: This drops existing data (3 teams, 6 members). No backup/archive step included per user's "remove completely" instruction.

## 5. Validation
1. **Python syntax**: `python3 -m py_compile` on all modified backend files
2. **Frontend build**: `npm run build` succeeds in `rankcareapp/`
3. **Functional checks**:
   - Login on Device A → succeeds, session stored in Redis
   - Login on Device B with same credentials → Device A session invalidated
   - Device A subsequent API call → 401
   - All `/api/teams/*` routes → 404
   - Team UI removed from sidebar/nav

## 6. Risks & Mitigations
| Risk | Mitigation |
|------|-----------|
| Redis unavailable | Fail closed (401) on session validation; login also fails if cannot store session |
| Stale Redis keys after server restart | TTL matches JWT expiry; `invalidate_session` on login cleans up previous |
| Concurrent API calls during re-login | New login invalidates old session immediately; old session's next request gets 401 |
| Existing team data loss | Migration drops tables; user confirmed "remove completely" |

## Out of Scope
- Password reset flow changes
- Email verification changes
- Redis connection pooling/config changes
- Frontend logout button UI (only API + storage logic)
- Data backup/archive before dropping team tables
