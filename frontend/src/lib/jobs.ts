// src/lib/jobs.ts

import { api } from './api';
import type { Messages } from './i18n';
import type { ExtractionJob, FailureReason, JobStatus } from './types';

export function statusLabel(status: JobStatus, m: Messages): string {
	return m[`jobs_status_${status}`];
}

export function isTerminal(status: JobStatus): boolean {
	return status === 'COMPLETED' || status === 'FAILED';
}

export function failureLabel(reason: FailureReason | null, m: Messages): string {
	return m[`jobs_failure_${reason ?? 'UNKNOWN'}`];
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
