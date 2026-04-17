# Skill: SaaS / B2B Application Testing

## Domain
Software-as-a-Service, project management, CRM, HR tools, analytics platforms, team collaboration

## Trigger Keywords
workspace, team, organization, project, task, dashboard, subscription, plan, billing, invite, member, role, permission, admin, settings, integration, webhook, api-key

## Critical Test Areas

### Multi-tenancy (Highest Priority)
- User A cannot access User B's organisation data
- Organisation-scoped data is correctly isolated
- Switching between organisations (if supported) shows correct data
- Deleted organisation data is not accessible
- Tenant-specific settings do not bleed across tenants

### Role-Based Access Control (RBAC)
- Admin can perform all actions
- Regular member cannot access admin-only sections
- Read-only user cannot create/edit/delete
- Role change takes effect immediately (no re-login required)
- Removed member loses access immediately
- Permission enforcement is server-side (not just UI-hidden)

### Team / Member Management
- Invite by email sends invitation
- Invitation link is single-use and expires
- Invitee can accept and joins the correct org
- Duplicate invite to existing member handled
- Member removal revokes access immediately
- Owner cannot remove themselves (or proper transfer flow exists)

### Subscription & Billing
- Free tier limitations enforced (e.g., max 3 projects)
- Upgrade flow works correctly
- Downgrade to lower plan enforces new limits
- Trial expiry: access restricted after trial ends
- Billing history shows correct invoices
- Payment method update works
- Cancellation flow and data retention policy

### Core Workflow (Varies by App)
- Create → Edit → Delete lifecycle for primary entity (project, deal, ticket)
- Status transitions follow allowed workflow
- Notifications triggered on status change
- Activity log records user actions
- Search and filter work across all records

### Dashboard & Analytics
- Widgets load with correct data
- Date range filters apply correctly
- Export (CSV/PDF) contains correct data
- Real-time updates (if applicable)
- Empty state shown correctly when no data

### Integrations & API
- OAuth integration connect/disconnect flow
- Webhook delivery on trigger events
- API key generation and revocation
- API rate limits enforced

### Data Management
- Import (CSV) validates format, reports errors on bad rows
- Export downloads correct data in correct format
- Bulk operations (select all, bulk delete) work
- Pagination works correctly with filters applied
- Sort persists with pagination

## Business Rules Unique to SaaS
- Seats/licences: cannot add more members than plan allows
- Feature flags: premium features hidden/locked on free plan
- Data retention: deleted items go to trash, permanently deleted after N days
- Audit logs: sensitive actions are logged
- SSO enforcement: org admin can mandate SSO login

## Common Selector Patterns
- Create button: `button:has-text('New')`, `button:has-text('Create')`, `.create-btn`
- Save: `button:has-text('Save')`, `button[type='submit']`
- Delete confirm: `.confirm-delete`, `button:has-text('Delete')`, `.modal button.danger`
- Role selector: `select[name='role']`, `.role-dropdown`
- Invite email: `input[placeholder*='email']`, `#invite-email`
