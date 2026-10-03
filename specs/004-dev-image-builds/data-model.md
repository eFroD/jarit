# Data Model: Dev-Images nach jedem Merge auf `dev`

There is no database change. The "data" of this feature are image references in the registry `ghcr.io/efrod/jarit/{backend,frontend}`.

## Tag namespace per image

| Tag | Kind | Written by | Points to | Changes when |
|-----|------|------------|-----------|--------------|
| `X.Y.Z` | immutable | `release.yml` | release build | never |
| `X.Y` | moving | `release.yml`, `ytdlp-refresh.yml` | latest release of the minor version, refreshed weekly | release or Monday refresh |
| `latest` | moving | `release.yml`, `ytdlp-refresh.yml` | latest release, refreshed weekly | release or Monday refresh |
| `buildcache` | cache | `release.yml`, `ytdlp-refresh.yml` | release build cache | release or refresh |
| **`dev-<sha7>`** | **immutable (new)** | `dev-images.yml` / `build` | build of `dev` commit `<sha7>` | never |
| **`dev`** | **moving (new)** | `dev-images.yml` / `promote` | the newest `dev-<sha7>` for which **both** images built | after every successful run |
| **`buildcache-dev`** | **cache (new)** | `dev-images.yml` / `build` | dev build cache | every run |

**Invariants**
- I1: `dev-images.yml` never writes `latest`, `X.Y`, `X.Y.Z` or `buildcache` (FR-006).
- I2: `backend:dev` and `frontend:dev` refer to the same `<sha7>` once a run has finished (FR-008; see the short window in [research R3](./research.md#r3--consistent-dev-across-both-images-and-architectures-fr-007-fr-008-sc-005)).
- I3: every `dev` and `dev-<sha7>` is a manifest list with `linux/amd64` and `linux/arm64` (FR-003).
- I4: the commit that `dev` points to is never older than the commit of an earlier successful run (FR-007).

## Image metadata (OCI labels)

| Label | Value |
|-------|-------|
| `org.opencontainers.image.revision` | full commit SHA |
| `org.opencontainers.image.created` | build time (ISO 8601) |
| `org.opencontainers.image.version` | `dev-<sha7>` |
| `org.opencontainers.image.source` | repository URL |

## State of `:dev` per run

```text
push to dev ─▶ build(backend) ┐
              build(frontend) ┴─▶ both ok? ── yes ─▶ promote: dev := dev-<sha7>
                                     │
                                     no / cancelled ─▶ dev unchanged
```
