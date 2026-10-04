# Data Model: Verschlüsselte Integrations-Keys

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

No schema change. The table `api_keys` keeps all its columns. Only the meaning and format of the column `api_key` change.

## IntegrationCredential (table `api_keys`, ORM `APIKey`)

| Column (DB) | ORM attribute | Type | Change | Notes |
|---|---|---|---|---|
| `id` | `id` | int PK | — | |
| `user_id` | `user_id` | FK → `users.id`, cascade delete | — | |
| `service_name` | `service_name` | str | — | e.g. `mealie`; not secret |
| `api_key` | **`api_key_ciphertext`** | str, not null | **format** | `enc:v1:<fernet-token>`, or legacy plaintext before migration |
| `base_url` | `base_url` | str, nullable | — | not secret, stays in plaintext |
| `is_active` | `is_active` | bool | — | |
| `created_at` / `updated_at` | same | timestamptz | `updated_at` is set when the secret is replaced or migrated | |

**Validation rules**
- The plaintext secret must be non-empty after trimming. Empty values are rejected with 422 before encryption.
- A stored value starting with `enc:v1:` is always treated as ciphertext and is never encrypted again (FR-012).
- At most one row per (`user_id`, `service_name`). This is already enforced by the upsert logic in `POST /users/me/api-keys`.

**Access rules**
- Writes go only through `credentials.set_secret(entry, plaintext)`.
- Reads go only through `credentials.reveal_secret(db, entry)`, and only where the secret is sent to the integration (FR-002, FR-003).
- Listing, reading metadata and deleting never decrypt.

## Secret state transitions

```text
              set_secret()                 reveal_secret() / startup migration
 (none) ───────────────────▶ ENCRYPTED ◀───────────────────────────── LEGACY_PLAINTEXT
                                 │   ▲
     key changed or lost         │   │ set_secret() (user re-enters credentials)
                                 ▼   │
                             UNREADABLE  ──── delete ────▶ (none)
```

| State | Detected by | Behaviour on use |
|---|---|---|
| `LEGACY_PLAINTEXT` | no `enc:v1:` prefix | used as is, then encrypted with a compare-and-set update |
| `ENCRYPTED` | prefix present, decryption succeeds | decrypted in memory for the call only |
| `UNREADABLE` | prefix present, `InvalidToken` | HTTP 409 "please re-enter credentials"; WARNING log without secrets |

`UNREADABLE` is not stored anywhere. It is found out on each access, so it ends as soon as the original key is back in place.

## EncryptionKey (not persisted)

- Source: env var `JARIT_ENCRYPTION_KEY`, read once at startup.
- Valid: Fernet constructor accepts it (32 bytes, URL-safe base64).
- One active key per instance. No key history.
