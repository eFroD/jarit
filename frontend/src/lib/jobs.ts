// src/lib/jobs.ts

import { api } from './api';
import type { ExtractionJob, FailureReason, JobStatus } from './types';

export const STATUS_LABELS: Record<JobStatus, string> = {
	QUEUED: 'Waiting',
	FETCHING_DESCRIPTION: 'Fetching video description',
	TRANSCRIBING: 'Transcribing audio',
	EXTRACTING: 'Extracting recipe',
	COMPLETED: 'Completed',
	FAILED: 'Failed'
};

export const FAILURE_REASON_LABELS: Record<FailureReason, string> = {
	VIDEO_UNREACHABLE: 'Video unreachable',
	NO_RECIPE_FOUND: 'No recipe found in this video',
	TRANSCRIPTION_FAILED: 'Transcription failed',
	LLM_ERROR: 'Language model error',
	TIMEOUT: 'Timed out',
	RESTARTED: 'Interrupted by an application restart',
	UNKNOWN: 'Unknown error, please try again'
};

export function isTerminal(status: JobStatus): boolean {
	return status === 'COMPLETED' || status === 'FAILED';
}

export function failureLabel(reason: FailureReason | null): string {
	return reason ? FAILURE_REASON_LABELS[reason] : FAILURE_REASON_LABELS.UNKNOWN;
}

/**
 * Poll a job until it reaches a terminal status.
 * onUpdate gets every fresh state, onError every failed request (polling continues).
 * Returns a function that stops polling.
 */
export function pollJob(
	id: string,
	onUpdate: (job: ExtractionJob) => void,
	onError: (err: unknown) => void = () => {},
	intervalMs = 2000
): () => void {
	let stopped = false;
	let timer: ReturnType<typeof setTimeout> | undefined;

	async function tick() {
		if (stopped) return;
		try {
			const job = await api.getExtractionJob(id);
			if (stopped) return;
			onUpdate(job);
			if (isTerminal(job.status)) return;
		} catch (err) {
			if (stopped) return;
			onError(err);
		}
		timer = setTimeout(tick, intervalMs);
	}

	tick();
	return () => {
		stopped = true;
		clearTimeout(timer);
	};
}
