# Contract: HTTP API changes

Base path `/api/v1`. All endpoints require a bearer token, as before. Only the changes are listed here.

## Unchanged shape, new guarantee

### `GET /users/me/api-keys` · `GET /users/me/api-keys/{service_name}`

The response shape `APIKeyResponse` stays the same: `id`, `service_name`, `base_url`, `is_active`, `created_at`.

**Guarantee**: The response never contains the plaintext or the ciphertext (FR-005). These endpoints never decrypt, so they also work for unreadable entries.

### `POST /users/me/api-keys`

The request stays the same: `{ "service_name": str, "api_key": str, "base_url": str | null }`.

- The secret is encrypted before it is stored. Replacing an existing entry, including an unreadable one, overwrites it.
- **New**: if `api_key` is empty or only whitespace, the response is `422` and nothing is stored.
- Response (201): `{ "message": "<service> API key created|updated successfully" }`. It contains no secret.

### `DELETE /users/me/api-keys/{service_name}`

Unchanged (204). This works without decrypting, so unreadable entries can be deleted.

## New error case

### `POST /integrations/upload-mealie` · `GET /integrations/verify-mealie-user`

| Status | When | Body |
|---|---|---|
| 404 | no Mealie credentials (unchanged) | `{"detail": "Mealie API key not configured. …"}` |
| **409** | the stored secret cannot be decrypted with the current key | `{"detail": "Your stored Mealie credentials can no longer be read (the server's encryption key has changed). Please enter your Mealie API key again in the settings."}` |

The 409 body must not contain the ciphertext, any part of the key or an exception text. The frontend shows `detail` as is (`frontend/src/lib/api.ts`). 409 does not trigger the 401 auto-logout.
