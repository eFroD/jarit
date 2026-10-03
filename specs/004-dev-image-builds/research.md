# Research: Dev-Images nach jedem Merge auf `dev`

Decisions for [spec.md](./spec.md). Each entry: decision, rationale, alternatives.

## R1 – Trigger (FR-001, FR-009)

**Decision**: New workflow `.github/workflows/dev-images.yml` with `on: push: branches: [dev]` and `workflow_dispatch`. No `paths` filter.

**Rationale**: A merged PR is a push to `dev`, and so is a direct push, which matches the edge case in the spec. Without a paths filter, every `dev` commit has a matching `dev-<sha>` tag. "Which commit does this image belong to?" then always has a direct answer (SC-003). The cost is one extra build for docs-only merges, which in this repo are rare and usually come with a feature anyway. `workflow_dispatch` covers rebuilding after a failed run. When started manually on another branch, the workflow stops at once (see [contracts/dev-images-workflow.md](./contracts/dev-images-workflow.md#trigger)), so only `dev` ever reaches `:dev`.

**Alternatives**:
- `pull_request: types: [closed]` with a `merged == true` check: misses direct pushes and runs in PR context. Rejected.
- `paths-ignore: ['specs/**', '**.md']`: saves builds but leaves gaps in the commit-tag series. Rejected for now.

## R2 – Tags and labels (FR-002, FR-004, FR-005, FR-006)

**Decision**: Per image:
- immutable `dev-<sha7>` via `docker/metadata-action` `type=sha,prefix=dev-` (7 characters by default)
- moving `dev`, set only by the promote step (R3)

Labels come from `metadata-action`. Its defaults already include `org.opencontainers.image.revision` (full commit SHA), `org.opencontainers.image.created` and `org.opencontainers.image.source`. We additionally set `org.opencontainers.image.version=dev-<sha7>`; otherwise it would take the tag with the highest priority.

**Rationale**: These are the same action and image names as `release.yml`, only with different tag rules. `latest`, `X.Y.Z` and `X.Y` never appear in this workflow, so FR-006 holds by construction. The labels can be read with `docker inspect` or `docker buildx imagetools inspect` without starting the app.

**Alternatives**:
- `type=edge`: produces `edge`, and the default branch is `main`, not `dev`. Rejected for naming.
- A long SHA tag: unwieldy, and 7 characters are unique enough in this repo. Rejected.
- `dev-<run_number>`: not tied to a commit. Rejected.

## R3 – Consistent `:dev` across both images and architectures (FR-007, FR-008, SC-005)

**Decision**: Two jobs.
1. **`build`**: a matrix over `backend` and `frontend`. Each image is built for `linux/amd64,linux/arm64` and pushed **only** as `dev-<sha7>`.
2. **`promote`**: `needs: build`. Runs `docker buildx imagetools create` to point `backend:dev` and `frontend:dev` at the two `dev-<sha7>` manifests. This copies manifests only; no layers are transferred, and it takes seconds.

Workflow-level `concurrency: { group: dev-images, cancel-in-progress: true }`.

**Rationale**:
- A multi-arch push from `build-push-action` is atomic per image: the manifest list is written last. Because `:dev` is moved only after **both** images succeeded, a failed or cancelled build never changes `:dev`. Only the commit tag of the image that did build would exist, and that tag is harmless.
- The concurrency group allows one run at a time. A newer push cancels the older run, so `:dev` cannot be set back to an older commit.
- Remaining window: if a newer push cancels a run in the middle of `promote` (between its two `imagetools` calls), `backend:dev` may briefly be newer than `frontend:dev`. The new run starts right away and promotes both, so the final state is consistent. Closing that gap would need extra concurrency settings at job level. That is not worth the complexity; we note it in [quickstart.md](./quickstart.md).
- Running the matrix in parallel roughly halves the wall time compared with the sequential `release.yml` (SC-001).

**Alternatives**:
- A single job like `release.yml`, pushing `dev` directly: backend `:dev` would be updated before the frontend build has even started, and a frontend failure would leave a mismatched pair. Rejected (FR-008).
- `cancel-in-progress: false`: GitHub keeps only the newest pending run anyway, so order is preserved, but a stale build runs to the end before the newest starts. That is slower and gains nothing. Rejected.

## R4 – Build cache must not displace the release cache (FR-006, SC-001)

**Decision**:
- `cache-from`: both `…/<image>:buildcache-dev` and `…/<image>:buildcache` (the release cache)
- `cache-to`: `…/<image>:buildcache-dev,mode=max` only

**Rationale**: Reading the release cache makes the first dev build fast, and the release cache stays exactly as releases left it. The GHA cache (`type=gha`) is shared with the PR CI and limited to 10 GB per repo. The multi-arch layers would evict the CI cache. Rejected.

**Alternatives**: no cache, which makes builds with QEMU-emulated arm64 slow, particularly `npm ci` and `uv sync`. Rejected.

## R5 – yt-dlp in dev images (edge case)

**Decision**: Pass `YTDLP_REFRESH=${{ github.run_id }}` like `release.yml`. `ytdlp-refresh.yml` stays unchanged.

**Rationale**: Dev images should behave like a fresh release. `ytdlp-refresh.yml` only writes `latest` and the minor tag, so it already leaves `dev` alone. Dev images get a new yt-dlp with every merge.

## R6 – New workflow file vs. a shared reusable workflow (FR-011)

**Decision**: A separate `dev-images.yml`; `release.yml` stays untouched.

**Rationale**: FR-011 requires release and PR CI to keep working unchanged. Turning `release.yml` into a reusable workflow would touch the release path for a feature that does not need it. The duplication is about 40 lines of action setup, and Dependabot (`github-actions` ecosystem) updates the action versions in both files in the same grouped PR, so they cannot drift apart.

**Alternatives**: `workflow_call` reusable build with an `inputs.tags` parameter. Worth doing once a third publishing workflow appears. Deferred.

## R7 – Switching a machine to `dev` (FR-010, SC-002)

**Decision**: Make the image tag in `docker-compose.yml` configurable: `ghcr.io/efrod/jarit/backend:${JARIT_IMAGE_TAG:-latest}`, and the same for the frontend. Mirror this in the README compose snippet. Switching means setting `JARIT_IMAGE_TAG=dev` in `.env`, then `docker compose pull && docker compose up -d`. Switching back means removing the line or setting it to `latest`.

**Rationale**: This is a one-line change in `.env` and needs no edits to the compose file. Without the variable, behavior is unchanged (`latest`). The same variable also pins a commit (`dev-abc1234`) or a release (`1.2.0`). Compose interpolation with a default has long been supported. Dependabot's `docker-compose` ecosystem does not touch our own images, which have no versioned tags, so nothing changes there.

**Alternatives**:
- Documenting a manual edit of `image:`: works, but is easy to forget when switching back. Rejected.
- A separate `docker-compose.dev-image.yml` override: one more file to maintain. Rejected.

## R8 – Migration risk (FR-010, User Story 3)

**Decision**: A new README section, "Testing the development version (`dev`)", which:
- states that `dev` is unstable and not meant for production
- says that migrations run automatically on start (see the existing "Background Extraction and Database Migrations" section) and are **not** undone when switching back
- recommends either a separate database and volume (separate compose project) or a `pg_dump` backup before switching, with the restore steps for going back
- shows how to read the running commit (`docker inspect … org.opencontainers.image.revision`)

**Rationale**: The backend runs Alembic `upgrade head` at startup. An older release cannot read a schema that a newer `dev` revision has changed, and it has no downgrade path at runtime.

## R9 – Permissions and secrets

**Decision**:
- `permissions: { contents: read, packages: write }`, scoped like `release.yml`
- login with `GITHUB_TOKEN`
- no new secrets

**Rationale**: `push` events from `dev` run in the base repo context. Fork PRs do not trigger `push`, so untrusted code never gets `packages: write`.

## R10 – Tests

**Decision**: There are no unit tests for the workflow. Validation:
- `actionlint` locally, if available, optional
- the end-to-end checks in [quickstart.md](./quickstart.md) after the first merge

**Rationale**: A workflow can only be proven by running it on GitHub. The PR CI `docker` job keeps checking that both Dockerfiles build, so a dev build only fails on registry or arm64 issues.
