# Module 06: Role-Based Access Control & Administration

## Authentication vs. Authorization

Authentication establishes *who* a user is. Authorization determines *what* that user is permitted to do. Both are required by 21 CFR Part 11, which mandates that electronic record systems restrict access to authorized individuals (§11.10(d)).

This module covers the RBAC model used in this project and the administrative interface that manages it.

---

## 1. Regulatory Requirements

Three constraints drive the design:

- **Access restriction:** Only designated users should be able to create records or execute signatures. A QA reviewer and a bench scientist need different capabilities.
- **Separation of duties:** Administrative operations (creating users, assigning roles) must be isolated from routine laboratory workflows.
- **Account deactivation, not deletion:** When an employee leaves, their account must be disabled immediately. However, the user record itself must be retained — deleting it would orphan the signatures and audit trail entries associated with that identity, violating data integrity requirements.

## 2. Role Definitions

Each user is assigned one of four roles, stored in the `role` column of the PostgreSQL `users` table:

| Role | Capabilities |
|---|---|
| `admin` | Access the user management dashboard. Create accounts, change roles, activate/deactivate users. |
| `scientist` | Create and edit draft ELN entries. Sign records as "Author". Standard operational role. |
| `reviewer` | Create records and sign as "Reviewer" or "Approver". Typically assigned to QA or senior staff. |
| `read-only` | Authenticate and view data. Cannot create, edit, or sign records. |

**Trade-off:** This is a flat, global RBAC model — a user's permissions are the same regardless of which project or document they are accessing. Enterprise systems typically implement Attribute-Based Access Control (ABAC), where authorization decisions consider context such as project membership, document ownership, or organizational unit. Alternatively, they integrate with centralized IAM platforms (Keycloak, Active Directory, Okta) that support fine-grained policies and group hierarchies.

---

## 3. API Enforcement

Authorization is enforced at the API layer using a FastAPI dependency that checks the user's role before the route handler executes:

```python
def require_role(*roles: str):
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: role '{current_user.role}' is not authorized for this endpoint",
            )
        return current_user
    return _check
```

Applied to a route:

```python
@router.post("/eln/")
async def create_eln_entry(
    entry: ELNEntry,
    current_user: User = Depends(require_role("admin", "scientist", "reviewer"))
):
    ...
```

If a `read-only` user sends a POST request to this endpoint, FastAPI evaluates the dependency, raises a `403 Forbidden` response, and never executes the handler body. This means authorization is enforced server-side regardless of what the frontend UI shows or hides.

---

## 4. The Admin Dashboard

The administrative interface (`frontend/src/pages/admin/users.js`) is accessible only to users with the `admin` role. It supports three operations:

### A. Account Creation

When creating a new account, the administrator sets the user's full name and professional title. Centralizing this step — rather than allowing self-registration — ensures that names appearing on electronic signatures are administratively verified, satisfying §11.50(a)(1).

### B. Role Changes

An administrator can promote or demote a user's role by sending a `PATCH /auth/users/{user_id}/role` request. Because the backend evaluates the role from the database (or the current JWT claims) on every request, changes take effect on the user's next API call.

### C. Account Deactivation

Instead of deleting a user record, the admin dashboard sends `PATCH /auth/users/{user_id}/status` to set the `is_active` flag to `False`.

- **Authentication blocked:** The login endpoint checks `is_active` before issuing a JWT. Deactivated users cannot obtain tokens.
- **Data preserved:** The user row remains in PostgreSQL, so all historical signatures and audit log entries that reference this user ID continue to resolve correctly.

This approach satisfies the regulatory requirement that records remain intact and traceable throughout their retention period, even after the originating user has left the organization.

---

## 5. Exercise: Testing the Authorization Boundary

1. Log in with your `admin` account.
2. In the Admin dashboard, create a new user with the `read-only` role.
3. Open a private/incognito browser window and log in as the new `read-only` user.
4. Attempt to create a new ELN entry or sign an existing one.
5. The frontend may display the form, but the backend API will reject the request with a `403 Forbidden` response. This demonstrates that authorization is enforced at the API layer, independent of the UI.
