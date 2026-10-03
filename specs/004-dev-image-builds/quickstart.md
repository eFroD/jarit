# Quickstart: validating dev images

Prerequisites: the feature is merged to `dev`, and you have a test machine with Docker Compose (amd64 or arm64) and a JarIt `.env`.

## 1. First build runs on merge (FR-001–FR-004, SC-001)

1. Merge the feature PR into `dev`.
2. In GitHub → Actions → "Dev images", the run starts within a minute; the `build` (2 legs) and `promote` jobs turn green.
   **Expected**: total time ≤ 30 min. The job summary lists `backend:dev-<sha7>` and `frontend:dev-<sha7>`.
3. Check the tags and architectures:
   ```bash
   docker buildx imagetools inspect ghcr.io/efrod/jarit/backend:dev
   docker buildx imagetools inspect ghcr.io/efrod/jarit/frontend:dev
   ```
   **Expected**: both list `linux/amd64` and `linux/arm64`, and their digests match the `dev-<sha7>` tags.

## 2. Release tags untouched (FR-006, SC-004)

Note the digests of `backend:latest` and `frontend:latest` before the merge, then compare them afterwards:
```bash
docker buildx imagetools inspect ghcr.io/efrod/jarit/backend:latest --format '{{json .Manifest.Digest}}'
```
**Expected**: unchanged, unless the Monday yt-dlp refresh ran in between.

## 3. Switch a machine to dev (User Story 1, SC-002)

```bash
echo 'JARIT_IMAGE_TAG=dev' >> .env
docker compose pull && docker compose up -d
docker inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' $(docker compose ps -q backend)
```
**Expected**: the app starts; the revision is the merge commit on `dev` (SC-003).

## 4. Successive merges (User Story 2, FR-007, SC-005)

1. Merge two small PRs into `dev` within a few minutes.
2. **Expected**: the first run is cancelled or finishes; after the last run, `:dev` points to the second commit, and the first commit's `dev-<sha7>` is still pullable if its build finished.
3. `JARIT_IMAGE_TAG=dev-<first sha7>`, pull, up: the machine runs the older state.

Note: a cancel that hits the `promote` job between its two steps can leave `backend:dev` and `frontend:dev` on different commits for the seconds until the next run promotes both ([research R3](./research.md#r3--consistent-dev-across-both-images-and-architectures-fr-007-fr-008-sc-005)).

## 5. Failure keeps the last good state (FR-008, FR-009)

When a run fails, or you cancel it during `build`: **Expected**: the `:dev` digests are unchanged and `promote` is skipped. Then use "Run workflow" on `dev`: a new run builds and promotes the current `dev` commit.
Starting "Run workflow" on another branch: **Expected**: the run fails in its first step and publishes nothing.

## 6. Switch back (User Story 3)

Follow the README section "Testing the development version (`dev`)": restore the backup (or use the separate database), remove `JARIT_IMAGE_TAG`, then `docker compose pull && docker compose up -d`. **Expected**: the machine runs `latest` again with the restored data.
