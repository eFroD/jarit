# HTTP API Contract: Nutzersprache

Base path: `/api/v1`. All endpoints except `/auth/*` require `Authorization: Bearer <token>`.

`Language` = one of `"en" | "de" | "es" | "fr" | "it"`.

## Changed: `GET /users/me`

Response `200` gains `language`:

```json
{
  "id": 1,
  "email": "a@example.com",
  "username": "alice",
  "role": "USER",
  "is_active": true,
  "created_at": "2026-10-02T12:00:00Z",
  "language": "de"
}
```

The admin user list (`GET /admin/users`) returns the same shape, including `language` (read-only there).

## New: `PATCH /users/me`

Changes the caller's own profile. Only `language` is accepted in this feature.

Request:

```json
{ "language": "fr" }
```

| Status | When | Body |
|--------|------|------|
| `200`  | saved | the full user object as in `GET /users/me`, with the new `language` |
| `422`  | `language` missing or not a `Language` | FastAPI validation error; stored language unchanged |
| `401`  | no or invalid token | `{ "detail": "...", "code": "INVALID_TOKEN" }` |

There is no endpoint to change another user's language.

## Changed: `POST /auth/register`

Request gains an optional `language` (default `"en"`):

```json
{ "email": "a@example.com", "username": "alice", "password": "secret123", "language": "de" }
```

Unsupported value → `422`, no user is created. The response includes `language`.

## Changed: `POST /extraction-jobs`

`target_language` becomes an optional `Language`:

| Request `target_language` | Stored on the job |
|---------------------------|-------------------|
| omitted or `null`         | the caller's `language` |
| a `Language` code         | that code |
| anything else (e.g. `"english"`, `"japanese"`, `""`) | — `422`, no job created |

Job responses (`GET /extraction-jobs`, `GET /extraction-jobs/{id}`) return `target_language` as stored. Jobs created before this feature show the migrated code (`"english"` → `"en"`, …) or, for other legacy values, the original text.

## Error codes

Every error raised by the application (not FastAPI's own `422` validation errors) has this shape:

```json
{ "detail": "<English text, unchanged>", "code": "<CODE>" }
```

`detail` is kept for logs and API clients. The frontend translates by `code`.

| Code | Status | Raised by | Current `detail` |
|------|--------|-----------|------------------|
| `INVALID_TOKEN` | 401 | any authenticated endpoint | Invalid token |
| `USER_NOT_FOUND` | 401 / 404 | auth dependency / admin delete | User not found |
| `INVALID_CREDENTIALS` | 401 | `POST /auth/login` | Incorrect username or password |
| `REGISTRATION_DISABLED` | 403 | `POST /auth/register` | Registration is disabled. … |
| `EMAIL_TAKEN` | 400 | `POST /auth/register` | Email already registered |
| `USERNAME_TAKEN` | 400 | `POST /auth/register` | Username already taken |
| `ADMIN_REQUIRED` | 403 | admin endpoints | Admin privileges required |
| `CANNOT_DELETE_SELF` | 400 | admin delete | Cannot delete your own account |
| `API_KEY_NOT_FOUND` | 404 | `/users/me/api-keys/{service}` | API key for … not found / No active API key found for … |
| `JOB_NOT_FOUND` | 404 | `/extraction-jobs/{id}*` | Extraction job not found |
| `JOB_NOT_EDITABLE` | 409 | `PUT …/recipe` | Only completed extractions can be edited |
| `JOB_NOT_UPLOADABLE` | 409 | `POST …/upload` | Only completed extractions can be uploaded |
| `JOB_NOT_RETRYABLE` | 409 | `POST …/retry` | Only failed extractions can be retried |
| `JOB_NOT_DELETABLE` | 409 | `DELETE /extraction-jobs/{id}` | Wait until the extraction has finished before deleting it |
| `MEALIE_NOT_CONFIGURED` | 404 | Mealie credential dependency | Mealie API key not configured. … |
| `MEALIE_URL_NOT_CONFIGURED` | 400 | Mealie credential dependency | Mealie base URL not configured. … |
| `MEALIE_CREDENTIALS_UNREADABLE` | 409 | Mealie credential dependency | Your stored Mealie credentials can no longer be read … |
| `MEALIE_ERROR` | Mealie's status | `POST …/upload` | Mealie error: … |
| `MEALIE_INVALID_CREDENTIALS` | 401 | `GET /integrations/verify-mealie-user` | Invalid Mealie credentials |

A backend test pins this list (codes and statuses), so a change here is a deliberate contract change.

**Note on `401`**: Today the frontend logs the user out on every `401`, including `MEALIE_INVALID_CREDENTIALS`, which is about Mealie and not about the JarIt session. With codes, the frontend logs out only on `401` with `INVALID_TOKEN`, `USER_NOT_FOUND` or no code.
