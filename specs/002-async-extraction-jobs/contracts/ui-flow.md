# Contract: Frontend flow

SvelteKit with the static adapter (`fallback: 'index.html'`); nginx already serves `index.html` for unknown paths, so dynamic routes work on reload and deep links. UI language stays English, as today.

## Routes

| Route | New/changed | Purpose |
|---|---|---|
| `/dashboard` | changed | `RecipeExtractor` submits a job and navigates to `/jobs/{id}`. New `ActiveJobs` block lists the user's `QUEUED`/active jobs with a link to their progress page (FR-009b). |
| `/jobs/[id]` | new | Progress view (`JobProgress` component). |
| `/jobs/{id}/recipe` | changed | Editor for one completed job. |
| `/history` | new | History list (`JobHistory` component). |
| navigation | changed | "History" link next to the existing entries (desktop and mobile). |

## `/jobs/[id]` — progress (Story 2, FR-009, FR-009a)

- Loads the job on mount, then polls `GET /extraction-jobs/{id}` every **2 s** while the status is `QUEUED` or active. Polling stops on a terminal status and when the page is left (`onDestroy`).
- Shows a step list: Waiting → Fetching video description → Transcribing audio → Extracting recipe. The current step is highlighted, earlier ones are checked. "Transcribing audio" can appear after "Extracting recipe" (the model decides late that it needs the transcript); it is shown as skipped only when the job completes without it.
- Shows the URL and how long the job has been running.
- `COMPLETED` → sets `extractedRecipe`, `suggestedRecipe` and `currentJobId` from the job and navigates to `/jobs/{id}/recipe` (same behavior as the old synchronous flow).
- `FAILED` → shows the reason text (table in [data-model.md](../data-model.md#failurereason)) and a **Try again** button (`POST …/retry`, then polling resumes on the same page). The button is disabled while the request is in flight.
- `404` → "This extraction does not exist." with a link to `/history`.
- Network error during polling → keeps the last known state, shows a small "Connection problem, retrying…" hint, keeps polling.

## `/jobs/{id}/recipe` — editor (Story 7, FR-022 to FR-024)

- If the stores are empty or hold another job (reload, coming from history), loads the job. A job that is not `COMPLETED` redirects to `/jobs/{id}`.
- **Save** button: `PUT …/recipe` with the current editor state. A "saved" or "unsaved changes" indicator is shown.
- **Upload to Mealie**: saves first if there are unsaved changes, then `POST …/upload-mealie`. If `uploaded_to_mealie_at` is already set, a confirmation dialog appears first: "This recipe was already uploaded on {date}. Upload again? This creates another copy in Mealie."
- Without a configured Mealie key: same message as today.
- **Discard** (existing button) now goes back without deleting the job; the job stays in the history.
- The old `/recipe-preview` route is removed; the job id is part of the path. Route ids in `resolve()` include the group: `resolve('/(app)/jobs/[id]/recipe', { id })`.

## `/history` — list (Story 6, FR-021, FR-025)

- `GET /extraction-jobs` on mount. Newest first.
- Each row: title, or the URL (truncated) if there is no title; relative time with the absolute time as a tooltip; status badge; "In Mealie" badge with date if `uploaded_to_mealie_at` is set.
- Row action by status:
  - `COMPLETED`: **Open** → `/jobs/{id}/recipe`.
  - `QUEUED`/active: **View progress** → `/jobs/{id}`.
  - `FAILED`: reason text + **Try again** (retry, then `/jobs/{id}`).
- **Delete** (with confirmation) is shown for `COMPLETED` and `FAILED` only. On `409` it shows the server message.
- Empty state: "No extractions yet" with a link to the dashboard.
- If any listed job is non-terminal, the list refreshes every 5 s so the badges update; otherwise no polling.

## Client code

- `src/lib/types.ts`: `JobStatus`, `FailureReason`, `ExtractionJobSummary`, `ExtractionJob`. `ExtractRecipeResponse` is kept as the type of `result`.
- `src/lib/api.ts`: `createExtractionJob`, `getExtractionJob`, `listExtractionJobs`, `saveJobRecipe`, `uploadJobToMealie`, `retryExtractionJob`, `deleteExtractionJob`. `extractRecipe` and `uploadToMealie` are removed.
- `src/lib/jobs.ts`: `STATUS_LABELS`, `FAILURE_REASON_LABELS`, `isTerminal(status)`, and a small `pollJob(id, onUpdate, intervalMs = 2000)` helper that returns a stop function.
- `src/lib/store.ts`: new `currentJobId` writable, cleared on `logout()`.
