# Module 02: Authentication & Identity

## Motivation

In any regulated laboratory system, the identity of the person creating or signing a record must be established with confidence. An ELN where the "author" field is a free-text input offers no identity assurance — anyone can type any name. This module covers the mechanisms this project uses to authenticate users and bind their identity to the records they create.

---

## 1. Password Storage: Hashing with bcrypt

### The Problem with Plaintext

Storing passwords in cleartext means a single database breach exposes every credential in the system. Because users frequently reuse passwords across services, a breach of one system can cascade into others.

### Cryptographic Hashing

A hash function maps an input of arbitrary length to a fixed-size output in a way that is computationally infeasible to reverse. We use **bcrypt**, an adaptive hashing algorithm designed specifically for password storage:

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# At registration time:
hashed = pwd_context.hash("mypassword123")
# Stores: "$2b$12$EixZaYVK1fsbw1ZfbX3OXe..."

# At login time:
is_valid = pwd_context.verify("mypassword123", hashed)
# Returns: True
```

The original password string is never stored. PostgreSQL holds only the bcrypt digest:

```sql
SELECT username, hashed_password FROM users WHERE username = 'jsmith';
-- hashed_password: $2b$12$EixZaYVK1fsbw1ZfbX3OXeJSIqByUs1J5g...
```

### Salting

Bcrypt automatically prepends a random **salt** to the password before hashing. This means two users who choose the same password will produce different hashes, which defeats precomputed lookup attacks (rainbow tables). Each call to `pwd_context.hash()` with the same input produces a different output — the `verify()` function knows how to extract the embedded salt and recompute correctly.

---

## 2. Session Management: JSON Web Tokens (JWT)

### Stateful Sessions (the traditional approach)

1. User submits credentials.
2. Server creates a session record in the database, returns a `session_id` cookie.
3. On every subsequent request, the server queries the database to look up the session.

This works, but it makes the database a bottleneck for every authenticated request.

### Stateless Tokens (JWT)

A JWT encodes the user's identity and claims into a self-contained token that the server can verify without a database lookup.

A token consists of three base64-encoded segments separated by dots:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
.eyJzdWIiOiJqc21pdGgiLCJyb2xlIjoic2NpZW50aXN0IiwiZXhwIjoxNzMxNzM5MjAwfQ
.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

| Segment | Contents |
|---|---|
| **Header** | Algorithm identifier (`HS256`) and token type |
| **Payload** | Claims: `sub` (username), `role`, `exp` (expiration timestamp) |
| **Signature** | HMAC of the header + payload, computed with a server-side secret key |

If anyone modifies the payload (for example, changing `role` from `scientist` to `admin`), the signature will not match when the server recomputes it, and the token is rejected.

### Authentication Flow

```
Client: POST /auth/login  { username, password }
        │
        ▼
Server: Verify password hash against PostgreSQL
        │
        ▼
Server: Generate JWT  { sub: "jsmith", role: "scientist", exp: ... }
        Sign with HMAC-SHA256 using SECRET_KEY
        │
        ▼
Client: Stores token, attaches it to future requests
        Authorization: Bearer <token>
        │
        ▼
Server: Verifies signature mathematically (no database query required)
```

**Trade-off:** Because the token is self-contained, the server cannot revoke an individual session before its expiration time without introducing a revocation list (which reintroduces server-side state). If a token is compromised, it remains valid until it expires. Production systems mitigate this with short token lifetimes and refresh-token rotation.

---

## 3. Polyglot Persistence: PostgreSQL + MongoDB

This project uses two databases, each chosen for the shape of data it stores:

| Database | Stores | Rationale |
|---|---|---|
| **PostgreSQL** | Users, roles, password hashes | Identity data requires strict uniqueness constraints, relational integrity, and transactional guarantees. SQLAlchemy provides the ORM layer. |
| **MongoDB** | ELN entries, experiments, audit logs | Lab records have variable-structure sections (free-text narratives, nested arrays of results, file attachments). A document store accommodates this without schema migrations. |

The User model in PostgreSQL:

```python
# backend/api/postgres.py
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    role = Column(String, default="scientist")
```

**Trade-off:** Operating two databases increases operational complexity — two backup strategies, two connection pools, two failure modes. For a small team or a learning environment this is manageable. At production scale, the trade-off would need to be weighed against the cost of maintaining a single database with a more complex schema.

---

## 4. Role-Based Access Control (RBAC)

Authentication establishes identity. Authorization determines what that identity is permitted to do.

This project implements a simple RBAC model with three roles:

| Role | Capabilities |
|---|---|
| `admin` | Manage users, assign roles, configure system settings |
| `scientist` | Create experiments, write and sign ELN entries |
| `reviewer` | View records, sign entries as a reviewer or approver |

### Enforcement via FastAPI Dependencies

```python
def require_role(*roles: str):
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return _check

# Usage: only admins can list all users
@router.get("/auth/users")
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return db.query(User).all()
```

FastAPI's dependency injection framework evaluates `require_role` before the route handler executes. If the user's role is not in the allowed set, the request is rejected with a `403 Forbidden` response and the handler body never runs.

**Trade-off:** This is a coarse-grained model — permissions are global to the user, not scoped to specific resources. Enterprise systems typically use Attribute-Based Access Control (ABAC) or integrate with dedicated IAM platforms (Keycloak, Auth0, Active Directory) that support fine-grained policies, user groups, and federated identity.

---

## 5. The First-User Bootstrap

A bootstrapping problem exists: the system requires an admin to create user accounts, but no admin exists in a fresh database. This project solves it by leaving the `/register` endpoint open only when the `users` table is empty:

```python
@router.post("/register")
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(403, "Registration closed. An admin must create your account.")

    # First user is automatically assigned the admin role
    role = "admin"
```

After the first account is created, the endpoint rejects all subsequent self-registration attempts. All further accounts must be provisioned through the admin interface.

---

## 6. Binding Signatures to Authenticated Identity (21 CFR Part 11)

The original implementation accepted a free-text signer name during the signature step. This provided no assurance that the person signing was who they claimed to be.

The current implementation requires a valid JWT at signature time and verifies that the username encoded in the token matches the asserted signer name:

```python
@router.post("/{entry_id}/sign")
async def sign_eln_entry(
    entry_id: str,
    sig: SignatureRequest,
    current_user: User = Depends(get_current_user),
):
    if current_user.username.lower() != sig.signer_name.lower():
        raise HTTPException(403, "Identity mismatch: token username does not match signer_name")
```

This enforces a two-component signature as required by §11.200(a): the user must have authenticated with their credentials (to obtain the JWT), and the JWT must resolve to the identity claimed on the signature.

---

## Exercises

### Exercise 2.1: Register and Authenticate

1. Start the services with `docker-compose up`.
2. Navigate to `http://localhost:3000/register` and create the first account.
3. Open the Swagger UI at `http://localhost:8000/docs`, find `/auth/login`, and authenticate. Note the JWT returned in the response.

### Exercise 2.2: Inspect a JWT

Open your browser's Developer Tools → Application → Local Storage and find the `lab_jwt` key. Copy the token value and paste it into [jwt.io](https://jwt.io).

- Identify the claims in the payload (`sub`, `role`, `exp`).
- In the jwt.io debugger, manually change the `role` claim to `"admin"`. Observe that the "Signature Verified" indicator turns invalid — the server would reject this modified token.

### Exercise 2.3: Test Role Enforcement

Using the Swagger UI:
1. As the admin user, call `POST /auth/admin/create-user` to create a user with the `scientist` role.
2. Log in as the new scientist.
3. Attempt to call `GET /auth/users` (which requires `admin`). Record the HTTP status code and error message.

### Exercise 2.4: Observe Salted Hashing

Run the following in a Python shell:

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

h1 = pwd_context.hash("hello123")
h2 = pwd_context.hash("hello123")

print(h1)
print(h2)
print(h1 == h2)  # False — different salts produce different hashes

print(pwd_context.verify("hello123", h1))   # True
print(pwd_context.verify("wrongpass", h1))   # False
```

Explain why `h1 != h2` even though the input password is identical.
