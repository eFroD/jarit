# Implementation Plan: Dev-Images nach jedem Merge auf `dev`

**Branch**: `feature/004-dev-image-builds` (from `dev` at `4ea078e`, not yet created) | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-dev-image-builds/spec.md`

## Summary

A new workflow `.github/workflows/dev-images.yml` runs on every push to `dev` and on manual dispatch. It works in two jobs:

- **`build`**: a matrix over backend and frontend. Each image is built for amd64 and arm64 and pushed only under the immutable tag `dev-<sha7>`, with OCI labels for commit and build time ([R2](./research.md#r2--tags-and-labels-fr-002-fr-004-fr-005-fr-006)).
- **`promote`**: runs only if both legs succeeded. It moves `:dev` of both images to that commit with a manifest-only `imagetools create` ([R3](./research.md#r3--consistent-dev-across-both-images-and-architectures-fr-007-fr-008-sc-005)).

A workflow-wide concurrency group with `cancel-in-progress` makes sure the newest commit wins. Dev builds use their own registry cache `buildcache-dev` and read the release cache without writing to it ([R4](./research.md#r4--build-cache-must-not-displace-the-release-cache-fr-006-sc-001)).

`docker-compose.yml` and the README compose snippet get `${JARIT_IMAGE_TAG:-latest}`, so a machine switches by setting one line in `.env` ([R7](./research.md#r7--switching-a-machine-to-dev-fr-010-sc-002)). The README gets a section on the dev channel, including the migration risk and how to switch back ([R8](./research.md#r8--migration-risk-fr-010-user-story-3)).

`release.yml`, `ci.yml` and `ytdlp-refresh.yml` stay unchanged.

## Technical Context

**Language/Version**: GitHub Actions workflow YAML; Docker Compose file format

**Primary Dependencies**: the actions `release.yml` already uses: `actions/checkout@v4`, `docker/setup-qemu-action@v3`, `docker/setup-buildx-action@v3`, `docker/login-action@v3`, `docker/metadata-action@v5`, `docker/build-push-action@v5`. **No new actions**; `docker buildx imagetools` comes with Buildx.

**Storage**: GHCR `ghcr.io/efrod/jarit/{backend,frontend}`. New tags: `dev`, `dev-<sha7>`, `buildcache-dev` ([data-model.md](./data-model.md)).

**Testing**: no automated tests for the workflow (R10). The PR CI keeps checking that both Dockerfiles build. End-to-end validation follows [quickstart.md](./quickstart.md) after the first merge. `actionlint` locally is optional.

**Target Platform**: GitHub-hosted `ubuntu-latest` runners; target machines are linux/amd64 and linux/arm64 with Docker Compose

**Project Type**: Web application (FastAPI backend, SvelteKit frontend); this feature only touches CI/CD and deployment docs

**Performance Goals**: `:dev` is pullable ≤ 30 min after the merge (SC-001). Parallel matrix legs and the shared cache keep a typical run well below that.

**Constraints**:
- Release tags and the release cache are never written (FR-006, invariant I1).
- `:dev` changes only after both images succeed (FR-008).
- Existing workflows are unchanged (FR-011).
- Without `JARIT_IMAGE_TAG`, compose behaves exactly as today.

**Scale/Scope**: 1 new workflow (~90 lines), 2 lines in `docker-compose.yml`, the README compose snippet plus one new section.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, so there are no ratified principles to check. **PASS (vacuous).**

The plan follows the conventions of 001–003:
- Dependabot keeps actions current, targeting `dev`.
- Image builds stay multi-arch, with the newest yt-dlp at build time.
- The README is the operator documentation.
- No secrets beyond `GITHUB_TOKEN`.

**Post-design re-check**: still PASS. No new dependencies, no new secrets, no changes to the application code.

## Project Structure

### Documentation (this feature)

```text
specs/004-dev-image-builds/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R10
├── data-model.md        # Phase 1: tag namespace, invariants, labels
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   └── dev-images-workflow.md   # workflow contract + compose image tag contract
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
.github/workflows/
├── dev-images.yml       # NEW: build (matrix backend/frontend → dev-<sha7>) + promote (→ dev)
├── release.yml          # unchanged
├── ci.yml               # unchanged
└── ytdlp-refresh.yml    # unchanged
docker-compose.yml       # image tags → ${JARIT_IMAGE_TAG:-latest}
README.md                # compose snippet as above; new section "Testing the development version (dev)"
```

**Structure Decision**: The feature lives entirely in CI configuration, the production compose file and the README. `docker-compose.dev.yml` (local build) and the application code are not touched.

## Complexity Tracking

No constitution violations.
