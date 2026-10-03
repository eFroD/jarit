---

description: "Task list for dev images built after every merge to dev"
---

# Tasks: Dev-Images nach jedem Merge auf `dev`

**Input**: Design documents from `specs/004-dev-image-builds/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: There are no automated tests ([research R10](./research.md#r10--tests)). Checks are static: `actionlint`, `docker compose config` and a grep for forbidden tags. After the merge, [quickstart.md](./quickstart.md) covers the end-to-end validation on GitHub.

**Organization**: Tasks are grouped by user story (US1–US3 from spec.md), so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: The user story the task belongs to

## Path Conventions

The feature touches only `.github/workflows/dev-images.yml` (new), `docker-compose.yml` and `README.md`. Shared names used throughout:

- Registry `ghcr.io`; image names `ghcr.io/${GITHUB_REPOSITORY@L}/backend` and `…/frontend`. For this repo that is `ghcr.io/efrod/jarit/{backend,frontend}`.
- Tags: `dev-<sha7>` (immutable), `dev` (moving), `buildcache-dev` (cache). Release tags `latest`, `X.Y`, `X.Y.Z` and the cache `buildcache` are **read-only** for this workflow ([data-model.md](./data-model.md), invariant I1).
- Compose variable: `JARIT_IMAGE_TAG`, default `latest`.
- Action versions: exactly the ones in `.github/workflows/release.yml` (`actions/checkout@v4`, `docker/setup-qemu-action@v3`, `docker/setup-buildx-action@v3`, `docker/login-action@v3`, `docker/metadata-action@v5`, `docker/build-push-action@v5`).
- Comment style in workflows: short `#` comments explaining *why*, as in `release.yml` and `ytdlp-refresh.yml`.

---

## Phase 1: Setup

- [X] T001 Create branch `feature/004-dev-image-builds` from `dev` (currently `4ea078e`) and check that `git status` is clean.
- [X] T002 Run `actionlint` on the existing workflows to get a baseline: `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest -color`, or a local `actionlint` binary. Note any pre-existing findings in `.github/workflows/*.yml`, so new findings can be told apart later.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The workflow file with trigger, guard, concurrency and permissions. Every story builds on it.

- [X] T003 Create `.github/workflows/dev-images.yml` with this content ([contracts/dev-images-workflow.md](./contracts/dev-images-workflow.md)):
  - A header comment explaining that every change on `dev` is published as `dev-<sha7>` and that `dev` follows the newest commit for which both images built. It also says the workflow never touches release tags.
  - `name: Dev images`
  - `on: push: branches: [dev]` and `workflow_dispatch:`
  - `concurrency: { group: dev-images, cancel-in-progress: true }`, with a comment that the newest commit wins ([R3](./research.md#r3--consistent-dev-across-both-images-and-architectures-fr-007-fr-008-sc-005))
  - top-level `permissions: { contents: read }`
  - `env: REGISTRY: ghcr.io`
  - no jobs yet beyond what is needed for the file to be valid; T004 adds `build`

**Checkpoint**: the file exists and passes `actionlint` once T004 adds the first job.

---

## Phase 3: User Story 1 - Aktuellen `dev`-Stand auf einer Maschine starten (Priority: P1) 🎯 MVP

**Goal**: Every push to `dev` publishes backend and frontend for amd64 and arm64, and `:dev` moves to that commit only after both images succeeded. A machine switches with `JARIT_IMAGE_TAG=dev`.

**Independent Test**: [quickstart.md](./quickstart.md) §1–§3. After a merge, `docker buildx imagetools inspect ghcr.io/efrod/jarit/backend:dev` shows both architectures. With `JARIT_IMAGE_TAG=dev`, the machine runs the merge commit, and `latest` is unchanged.

### Implementation for User Story 1

- [X] T004 [US1] Add job `build` to `.github/workflows/dev-images.yml`:
  - `runs-on: ubuntu-latest`, `timeout-minutes: 45`, job `permissions: { contents: read, packages: write }`
  - `strategy: fail-fast: true`, `matrix.include` with two entries:
    - `image: backend`, `context: .`, `file: ./Dockerfile.backend`
    - `image: frontend`, `context: ./frontend`, `file: ./frontend/Dockerfile`
  - Steps, in order:
    1. A **"Only publish from dev"** step: `if: github.ref != 'refs/heads/dev'` → `run: echo "::error::Dev images are only built from dev" && exit 1` (manual dispatch from another branch, contract §Trigger).
    2. `actions/checkout@v4`.
    3. Set the lowercase repository as in `release.yml`: `echo "repository=${GITHUB_REPOSITORY@L}" >> "$GITHUB_OUTPUT"`, step id `repo`.
    4. `docker/setup-qemu-action@v3`, `docker/setup-buildx-action@v3`.
    5. `docker/login-action@v3` with `registry: ${{ env.REGISTRY }}`, `username: ${{ github.actor }}`, `password: ${{ secrets.GITHUB_TOKEN }}`.
    6. `docker/metadata-action@v5`, id `meta`: `images: ${{ env.REGISTRY }}/${{ steps.repo.outputs.repository }}/${{ matrix.image }}`, `tags: type=sha,prefix=dev-` (only this line, **no** `type=raw,value=dev` and no `latest`).
    7. `docker/build-push-action@v5`:
       - `context`/`file` from the matrix, `platforms: linux/amd64,linux/arm64`, `push: true`
       - `tags: ${{ steps.meta.outputs.tags }}`, `labels: ${{ steps.meta.outputs.labels }}`
       - `build-args: YTDLP_REFRESH=${{ github.run_id }}`. Passing it to both images is harmless (the frontend Dockerfile ignores it). Add a comment like the one in `release.yml` ([R5](./research.md#r5--yt-dlp-in-dev-images-edge-case)).
       - `cache-from` with two lines: `type=registry,ref=…/${{ matrix.image }}:buildcache-dev` and `type=registry,ref=…/${{ matrix.image }}:buildcache`
       - `cache-to: type=registry,ref=…/${{ matrix.image }}:buildcache-dev,mode=max`, with a comment that the release cache is only read ([R4](./research.md#r4--build-cache-must-not-displace-the-release-cache-fr-006-sc-001))
- [X] T005 [US1] Add job `promote` to `.github/workflows/dev-images.yml`:
  - `needs: build`, `runs-on: ubuntu-latest`, `timeout-minutes: 10`, `permissions: { contents: read, packages: write }`
  - Steps: lowercase repository (as in T004), `docker/setup-buildx-action@v3`, `docker/login-action@v3` (same inputs), then one step that computes `sha7="${GITHUB_SHA::7}"` and, for `image in backend frontend`, runs `docker buildx imagetools create --tag "$REGISTRY/$repository/$image:dev" "$REGISTRY/$repository/$image:dev-$sha7"`.
  - Add a comment: `:dev` only moves after both images built, so it never points to a mixed or partial pair (FR-008); `imagetools create` copies manifests only.
  - Pass `REGISTRY`, the repository output and `GITHUB_SHA` through `env:` on the step, not by inline `${{ }}` in the script.
- [X] T006 [P] [US1] In `docker-compose.yml`, change `image: ghcr.io/efrod/jarit/backend:latest` to `ghcr.io/efrod/jarit/backend:${JARIT_IMAGE_TAG:-latest}`, and the same for the frontend ([contracts/dev-images-workflow.md](./contracts/dev-images-workflow.md#contract-compose-image-tag)). Leave `docker-compose.dev.yml` untouched.
- [X] T007 [P] [US1] Apply the same two-line change to the compose snippet in `README.md` (section "Without Cloning the Repo", the `backend` and `frontend` `image:` lines).
- [X] T008 [US1] Validate: run `actionlint` on `.github/workflows/dev-images.yml` with no new findings compared to T002. Run `docker compose config --images` with no `JARIT_IMAGE_TAG` and expect `…:latest` for both images, then with `JARIT_IMAGE_TAG=dev` and expect `…:dev`. Use a dummy `.env` or `--env-file /dev/null` if needed.

**Checkpoint**: US1 is complete. After merge, `:dev` is published and a machine can run it.

---

## Phase 4: User Story 2 - Getesteten Stand eindeutig zuordnen und festhalten (Priority: P2)

**Goal**: Each build is identifiable: `dev-<sha7>` already exists from T004. The images now also carry the commit and build time, and the run summary names what was published.

**Independent Test**: [quickstart.md](./quickstart.md) §3 (read `org.opencontainers.image.revision` from a running container) and §4 (two merges: `:dev` points to the second, `dev-<first sha7>` still pullable).

### Implementation for User Story 2

- [X] T009 [US2] In job `build` of `.github/workflows/dev-images.yml`, add `labels: org.opencontainers.image.version=dev-{{sha}}` to the `metadata-action` step. Its defaults already set `revision`, `created` and `source` ([R2](./research.md#r2--tags-and-labels-fr-002-fr-004-fr-005-fr-006)). `{{sha}}` is the short SHA of `metadata-action`, so it matches the tag.
- [X] T010 [US2] In job `promote` of `.github/workflows/dev-images.yml`, append a summary to `$GITHUB_STEP_SUMMARY` after the `imagetools create` loop:
  - the full commit SHA and the `dev-<sha7>` tag
  - for each image, the `:dev` reference and its digest (`docker buildx imagetools inspect "<ref>:dev" --format '{{json .Manifest.Digest}}'`)
  - a one-line hint: `JARIT_IMAGE_TAG=dev-<sha7>` pins this build

**Checkpoint**: US1 and US2 work; any running dev image can be traced to its commit.

---

## Phase 5: User Story 3 - Dev-Kanal ist dokumentiert, inklusive Risiken (Priority: P3)

**Goal**: Operators can switch to `dev` and back from the README alone and know the migration risk.

**Independent Test**: [quickstart.md](./quickstart.md) §6. Following only the README, switch a machine `latest` → `dev` → `latest`; the section names the migration risk and how to protect against it.

### Implementation for User Story 3

- [X] T011 [US3] Add a section `### Testing the Development Version (dev)` to `README.md`, directly after "Updates and yt-dlp" ([R8](./research.md#r8--migration-risk-fr-010-user-story-3)). Contents:
  - what `dev` and `dev-<sha7>` are (built after every change on `dev`, amd64 and arm64)
  - that `dev` is unstable and not for production
  - switching: `JARIT_IMAGE_TAG=dev` in `.env`, then `docker compose pull && docker compose up -d`; pinning with `JARIT_IMAGE_TAG=dev-<sha7>`
  - reading the running commit: `docker inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' $(docker compose ps -q backend)`
  - a **migration warning**: migrations run on start (link to "Background Extraction and Database Migrations") and are not undone when switching back, and an older release may not start on a newer schema
  - the two safe options:
    1. a separate test instance: own directory, own `.env`, its own compose project name so it gets its own `postgres_data` volume
    2. a backup before switching: `docker compose exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql`
  - switching back: remove `JARIT_IMAGE_TAG` (or set `latest`), restore the backup if `dev` changed the schema, then pull and up

  Keep the tone and length of the surrounding README sections.
- [X] T012 [US3] In `README.md`, add the new section to the table of contents next to the existing entries (same indentation and anchor style). In the "Updates and yt-dlp" section, add one sentence that the weekly refresh does not touch `dev`.

**Checkpoint**: All stories complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T013 Check invariant I1 statically: `grep -nE 'latest|buildcache[^-]|semver|type=raw' .github/workflows/dev-images.yml` should only match the `cache-from` line that reads `:buildcache` and comments. Nothing may write those tags. Confirm with `git diff --stat dev` that `release.yml`, `ci.yml` and `ytdlp-refresh.yml` are unchanged (FR-011).
- [X] T014 Re-run `actionlint` on all workflows and `docker compose config --images` (T008) after all edits. Proofread the README changes and check that the new anchors resolve.
- [ ] T015 Commit the feature with a message in the repo's style (see `git log`), e.g. `ci: publish dev images after every push to dev`, and open a PR against `dev`. The PR description lists the [quickstart.md](./quickstart.md) checks to do after merge.
- [ ] T016 After the merge (manual, on GitHub): run [quickstart.md](./quickstart.md) §1–§5 and record the run time against SC-001 (≤ 30 min). If the GHCR package settings restrict which workflows may push, grant this workflow write access to both packages and re-run with "Run workflow" on `dev`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: T003 depends on T001.
- **US1 (Phase 3)**: T004 → T005, both in the same file and after T003. T006 and T007 are independent of the workflow and can start right after T001. T008 needs T004–T007.
- **US2 (Phase 4)**: T009 needs T004, and T010 needs T005. Both are in the same file, so run them sequentially.
- **US3 (Phase 5)**: T011 and T012 are both in `README.md` and need T007 so the compose snippet is already updated. They don't depend on the workflow.
- **Polish (Phase 6)**: after all stories. T016 only after the PR is merged.

### User Story Dependencies

- **US1**: the MVP; it depends only on T003.
- **US2**: builds on the jobs from US1 (same file).
- **US3**: independent of US1 and US2 in code, but documents their behavior. Writing it before the workflow exists is fine.

### Parallel Opportunities

- T006 and T007 (two different files) can run in parallel with T003–T005.
- T011 and T012 can be drafted while the workflow tasks are in progress. They share `README.md` with T007, so apply them after it.

---

## Parallel Example: User Story 1

```text
Workflow track:  T003 → T004 → T005
Compose track:   T006 (docker-compose.yml) ∥ T007 (README.md compose snippet)
Join:            T008 validation
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. T001–T003.
2. T004–T008: `:dev` is published after each merge and machines can switch.
3. **Stop and validate** with quickstart §1–§3 after merging. This alone answers the original request.

### Incremental Delivery

1. US1 → merge → `:dev` available.
2. US2 → labels and run summary → traceability.
3. US3 → README section → operators know the risks.

All three are small enough to ship in one PR; the order above is the recommended order of work within it.
