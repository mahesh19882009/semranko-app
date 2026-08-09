# Plan: Remove Team → Rename to Account

## Goal
Replace the "Team" abstraction with an "Account" abstraction. Each account has one owner and multiple members. Simplify member management, remove team-specific credit charges, and introduce new member pricing.

---

## 1. Database Migration

**Create new Alembic migration:** `rename_team_to_account.py`

- Rename `Team` table → `Account`
- Rename `TeamMember` table → `AccountMember`
- Rename `TeamMember.teamId` column → `AccountMember.accountId`
- Update foreign key constraints, indexes, and unique constraints to use new table/column names
- Update `User.ownedTeams`/`teamMemberships` relationship back-populates if they are in migration scope (they are ORM-only, not DB-level)

**Note:** Existing migration `a54a6d764a82_drop_unused_tables.py` drops `Team`/`TeamMember` in `upgrade()`. The new migration must handle both cases: tables exist (rename) or were dropped (recreate with new names).

---

## 2. Models (`app/db/models.py`)

- Rename `Team` → `Account`
- Rename `TeamMember` → `AccountMember`
- Update `User` relationships:
  - `ownedTeams` → `ownedAccounts`
  - `teamMemberships` → `accountMemberships`
- Update `Account` relationships:
  - `owner` stays same
  - `members` → `accountMembers` with `cascade="all, delete-orphan"`
- Update `AccountMember` relationships:
  - `team` → `account`
  - `user` stays same
- Update `__tablename__` values:
  - `"Team"` → `"Account"`
  - `"TeamMember"` → `"AccountMember"`

---

## 3. Backend Services

### 3.1 Rename `team_service.py` → `account_service.py`

Update all function names:
- `get_team_owner_id` → `get_account_owner_id`
- `create_team` → `create_account`
- `get_team` → `get_account`
- `list_teams_for_user` → `list_accounts_for_user`
- `add_team_member` → `add_account_member`
- `update_team_member_role` → `update_account_member_role`
- `remove_team_member` → `remove_account_member`
- `delete_team` → `delete_account`
- `deduct_credits_for_team_action` → `deduct_credits_for_account_action`

Update internal variable names and docstrings.

### 3.2 Remove team-specific credit charges

- Remove `USER_CREDIT_COSTS["team_member"] = 10` from `app/core/config.py`
- In `add_account_member`: remove the 10-credit charge for adding members
- In `create_account`: remove the 10-credit charge for creating a 2nd+ account

### 3.3 Add new member pricing: 500 credits per member after first free

New logic in `add_account_member`:
- Account owner + 1 member = free (no charge)
- Each additional member beyond the first free one = 500 credits
- Deduct from account owner

### 3.4 Update all `get_team_owner_id` → `get_account_owner_id` calls

Files to update:
- `keyword_service.py`
- `keyword_update_service.py`  
- `keyword_research_service.py`
- `monday_tracker.py`
- `credits.py`
- `deps.py` (if used)
- `tracked_keywords.py` (remove dead import)

---

## 4. Backend Routes

### 4.1 Rename `app/api/routes/teams.py` → `accounts.py`

- Update `APIRouter` prefix: `/teams` → `/accounts`
- Update all endpoint paths
- Update function names and docstrings
- Update schema imports from `app.schemas.team` → `app.schemas.account`

### 4.2 Update router registration in `app/api/router.py`

- Rename import: `teams_router` → `accounts_router`
- Keep same include path

---

## 5. Schemas

### 5.1 Rename `app/schemas/team.py` → `account.py`

- `TeamCreate` → `AccountCreate`
- `TeamUpdate` → `AccountUpdate`
- `TeamMemberAdd` → `AccountMemberAdd`
- `TeamMemberUpdate` → `AccountMemberUpdate`
- `TeamResponse` → `AccountResponse`
- `TeamMemberResponse` → `AccountMemberResponse`
- Update all field references (teamId → accountId, etc.)

---

## 6. Config (`app/core/config.py`)

- Remove `"team_member": 10` from `USER_CREDIT_COSTS`
- Add `"account_member": 500` to `USER_CREDIT_COSTS`

---

## 7. Plan Definitions (`app/services/plan_service.py`)

- Rename `teamMembers` → `accountMembers` in all plan definitions
- Update the field name in the limits payload returned to frontend

---

## 8. Frontend Changes

### 8.1 Rename `TeamPage.jsx` → `AccountPage.jsx` or `MembersPage.jsx`

- Update all internal references from team → account
- Update API endpoint paths from `/teams/` → `/accounts/`
- Update form labels, button text, headings

### 8.2 Update Sidebar navigation (`SideBar.jsx`)

- Update path: `/dashboard/team` → `/dashboard/account` (or `/dashboard/members`)
- Update label: `Team` → `Members` or `Account`

### 8.3 Update API wrappers

- `src/lib/api.js`: Rename team API functions, update endpoints
- `src/features/pricing/pricingApi.js`: Update team API calls

### 8.4 Update Redux state (`subscriptionSlice.js`)

- Rename `limits.teamMembers` → `limits.accountMembers`

### 8.5 Update pricing config (`pricing.js`)

- Rename credit items: `"Team (After 1st Free)"` → `"Member (After 1st Free)"`
- Update cost from 10 → 500
- Update enterprise plan marketing copy

### 8.6 Update marketing pages

- `PricingPage.jsx`: Update copy from "SEO teams" → "SEO accounts" or similar
- `HomePage.jsx`: Update copy if needed

---

## 9. Routing

- Update `app/navigation.jsx` or equivalent if it has team routes
- Update any React Router routes for team page

---

## 10. Validation Steps

1. **Database**: Run migration, verify `Account` and `AccountMember` tables exist with correct columns
2. **Models**: Verify SQLAlchemy can import all models without errors
3. **Backend**: 
   - Start server, verify no import errors
   - Create account, add members, verify 500-credit charge applies after first free member
   - Verify keyword operations still work with `get_account_owner_id`
4. **Frontend**:
   - Navigate to members page
   - Add member, verify API calls work
   - Verify pricing page shows updated costs
5. **Data integrity**: Verify existing team data is preserved after rename

---

## Open Questions

1. **Migration strategy for existing data**: Should we create a migration that renames tables, or drop and recreate? (Recommend rename to preserve data)
2. **Plan member limits**: Should `teamMembers` limits in plans be renamed to `accountMembers` with same values, or adjusted? (Recommend rename with same values first)
3. **Frontend route path**: `/dashboard/account` or `/dashboard/members`? (Recommend `/dashboard/members` for clarity)
4. **Credit charge timing**: Is the 500-credit charge one-time when adding a member, or recurring monthly? (Recommend one-time, matching current team member charge behavior)
