# Contract: Operator configuration and startup

## Environment variable

| Name | Required | Format | Default |
|---|---|---|---|
| `JARIT_ENCRYPTION_KEY` | yes | Fernet key: 44 characters of URL-safe base64 (32 bytes) | none (startup aborts) |

It must be passed to the backend container. Both compose files list it under `backend.environment` as `JARIT_ENCRYPTION_KEY=${JARIT_ENCRYPTION_KEY}`. In `.env_example`, it is a placeholder that fails validation, for example `JARIT_ENCRYPTION_KEY=CHANGEME`.

How to generate a key (documented in the README):

```sh
docker run --rm python:3.13-slim sh -c "pip -q install cryptography && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
# or, inside an existing checkout:
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Startup failure output

This applies when the variable is missing or invalid: the backend writes the block below to **stderr**, exits with **code 1**, and does not serve any request. The wording may vary, but every element listed below is required.

```text
================================================================
JarIt cannot start: JARIT_ENCRYPTION_KEY is missing.          ← or: "… is invalid (expected a 44-character Fernet key)."
                                                              ← the invalid value itself is NEVER printed
Add this line to your .env file and restart:

JARIT_ENCRYPTION_KEY=3q2-7wJx...generated-fresh-each-start...=

Keep this key safe and back it up. If it is lost or changed, all
stored integration credentials (e.g. Mealie API keys) become
unreadable and every user has to enter them again.
================================================================
```

Requirements:
- A new key is generated on every failed start, so there is no fixed suggestion (Story 2, scenario 4).
- The block is printed before Logfire is configured, so it is never sent to external monitoring.
- On success, nothing about the key is printed. A single line `Integration secret encryption enabled` is fine.

## Startup migration log

After a successful key check, at most one INFO line is logged, and only if any legacy rows were found:

```text
Encrypted N legacy plaintext integration credential(s); M failed and will be retried.
```

The line contains no ids of secrets and no values.
