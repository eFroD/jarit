# Contract: `.github/workflows/dev-images.yml`

## Trigger

- `push` to `dev`
- `workflow_dispatch`. The first step of `build` fails right away if `github.ref != 'refs/heads/dev'`, so a manual run on another branch never publishes.

## Concurrency and permissions

- `concurrency: { group: dev-images, cancel-in-progress: true }`
- `permissions: { contents: read, packages: write }`

## Job `build`

- Matrix:
  - `image: backend`: context `.`, file `./Dockerfile.backend`, build-arg `YTDLP_REFRESH=${{ github.run_id }}`
  - `image: frontend`: context `./frontend`, file `./frontend/Dockerfile`
- `platforms: linux/amd64,linux/arm64`, with QEMU and Buildx set up as in `release.yml`
- Image name: `ghcr.io/${GITHUB_REPOSITORY@L}/<image>`
- Tags: **only** `dev-<sha7>` (`metadata-action`: `type=sha,prefix=dev-`)
- Labels: from `metadata-action`, plus `org.opencontainers.image.version=dev-<sha7>`
- Cache: from `buildcache-dev` and `buildcache`, to `buildcache-dev` (`mode=max`)
- `fail-fast: true`

## Job `promote`

- `needs: build`; only runs if all matrix legs succeeded
- For each of `backend` and `frontend`: `docker buildx imagetools create -t <name>:dev <name>:dev-<sha7>`
- Writes the result (commit, both refs) to the job summary

## Must not

- write `latest`, `X.Y`, `X.Y.Z` or `buildcache`
- change `release.yml`, `ci.yml` or `ytdlp-refresh.yml`

# Contract: compose image tag

`docker-compose.yml` and the compose snippet in the README:

```yaml
backend:
  image: ghcr.io/efrod/jarit/backend:${JARIT_IMAGE_TAG:-latest}
frontend:
  image: ghcr.io/efrod/jarit/frontend:${JARIT_IMAGE_TAG:-latest}
```

| `JARIT_IMAGE_TAG` | Result |
|-------------------|--------|
| unset | `latest`, same as today |
| `dev` | newest `dev` build |
| `dev-abc1234` | a fixed `dev` commit |
| `1.2.0` | a fixed release |

`docker-compose.dev.yml` (local build) is unaffected.
