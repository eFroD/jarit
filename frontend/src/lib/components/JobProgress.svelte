<!-- JobProgress.svelte -->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api, ApiError } from '$lib/api';
	import { failureLabel, pollJob, STATUS_LABELS } from '$lib/jobs';
	import { currentJobId, extractedRecipe, suggestedRecipe } from '$lib/store';
	import type { ExtractionJob, JobStatus } from '$lib/types';

	export let jobId: string;

	const STEPS: JobStatus[] = ['QUEUED', 'FETCHING_DESCRIPTION', 'TRANSCRIBING', 'EXTRACTING'];

	let job: ExtractionJob | null = null;
	let notFound = false;
	let connectionProblem = false;
	let retrying = false;
	let retryError = '';
	let now = Date.now();
	// Statuses seen while polling; transcription may come after extraction started.
	let seen = new Set<JobStatus>();
	let stopPolling: () => void = () => {};

	const clock = setInterval(() => (now = Date.now()), 1000);

	function start() {
		stopPolling();
		stopPolling = pollJob(jobId, handleUpdate, handleError);
	}

	function handleUpdate(update: ExtractionJob) {
		job = update;
		connectionProblem = false;
		seen = new Set([...seen, update.status]);

		if (update.status === 'COMPLETED' && update.result?.recipe) {
			extractedRecipe.set(update.result.recipe);
			suggestedRecipe.set(update.result.suggested_version);
			currentJobId.set(update.id);
			goto(resolve('/(app)/jobs/[id]/recipe', { id: update.id }));
		}
	}

	function handleError(err: unknown) {
		if (err instanceof ApiError && err.status === 404) {
			notFound = true;
			stopPolling();
		} else {
			connectionProblem = true;
		}
	}

	async function handleRetry() {
		retrying = true;
		retryError = '';
		try {
			job = await api.retryExtractionJob(jobId);
			seen = new Set(['QUEUED']);
			start();
		} catch (err) {
			retryError = err instanceof Error ? err.message : 'Could not restart the extraction';
		} finally {
			retrying = false;
		}
	}

	type StepState = 'done' | 'current' | 'skipped' | 'pending';

	function stepState(step: JobStatus, current: ExtractionJob | null): StepState {
		if (!current) return 'pending';
		const status = current.status;
		if (status === step) return 'current';
		if (step === 'TRANSCRIBING') {
			if (seen.has('TRANSCRIBING')) return 'done';
			return status === 'COMPLETED' ? 'skipped' : 'pending';
		}
		if (status === 'COMPLETED') return 'done';
		const order = STEPS.indexOf(step);
		const reached = Math.max(...[...seen].map((s) => STEPS.indexOf(s)));
		return order < reached ? 'done' : 'pending';
	}

	function elapsed(since: string, until: number): string {
		const seconds = Math.max(0, Math.round((until - new Date(since).getTime()) / 1000));
		const minutes = Math.floor(seconds / 60);
		return minutes > 0 ? `${minutes} min ${seconds % 60} s` : `${seconds} s`;
	}

	start();

	onDestroy(() => {
		stopPolling();
		clearInterval(clock);
	});
</script>

<div class="rounded-lg bg-white p-8 shadow-md">
	{#if notFound}
		<h2 class="mb-2 text-2xl font-bold text-gray-900">Extraction not found</h2>
		<p class="mb-6 text-gray-600">This extraction does not exist.</p>
		<a href={resolve('/history')} class="font-medium text-cyan-600 hover:text-cyan-700"
			>Go to your history</a
		>
	{:else}
		<h2 class="mb-2 text-2xl font-bold text-gray-900">Extracting recipe</h2>
		{#if job}
			<p class="mb-1 font-mono text-sm break-all text-gray-600">{job.video_url}</p>
			{#if job.status !== 'FAILED' && job.status !== 'COMPLETED'}
				<p class="mb-6 text-sm text-gray-500">
					Running for {elapsed(job.started_at, now)} · you can leave this page and come back later
				</p>
			{:else}
				<div class="mb-6"></div>
			{/if}

			<ol class="space-y-3">
				{#each STEPS as step (step)}
					{@const state = stepState(step, job)}
					<li class="flex items-center gap-3">
						{#if state === 'done'}
							<span
								class="flex h-7 w-7 items-center justify-center rounded-full bg-green-100 text-green-700"
								>✓</span
							>
						{:else if state === 'current'}
							<span
								class="flex h-7 w-7 items-center justify-center rounded-full bg-cyan-100 text-cyan-700"
							>
								<span
									class="h-3 w-3 animate-spin rounded-full border-2 border-cyan-600 border-t-transparent"
								></span>
							</span>
						{:else}
							<span
								class="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-gray-400"
								>·</span
							>
						{/if}
						<span
							class:font-semibold={state === 'current'}
							class:text-gray-900={state === 'current' || state === 'done'}
							class:text-gray-400={state === 'pending' || state === 'skipped'}
						>
							{STATUS_LABELS[step]}
							{#if state === 'skipped'}<span class="text-xs">(not needed)</span>{/if}
						</span>
					</li>
				{/each}
			</ol>

			{#if job.status === 'COMPLETED'}
				<p class="mt-6 text-green-700">✓ Done, opening the recipe…</p>
			{/if}

			{#if job.status === 'FAILED'}
				<div class="mt-6 rounded-lg border border-red-200 bg-red-50 p-4">
					<p class="mb-3 text-red-800">
						<strong>✗ {failureLabel(job.failure_reason)}</strong>
					</p>
					{#if retryError}
						<p class="mb-3 text-sm text-red-700">{retryError}</p>
					{/if}
					<button
						on:click={handleRetry}
						disabled={retrying}
						class="rounded-lg bg-cyan-600 px-4 py-2 font-medium text-white hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-50"
					>
						{retrying ? 'Restarting…' : 'Try again'}
					</button>
				</div>
			{/if}
		{:else}
			<p class="text-gray-500">Loading…</p>
		{/if}

		{#if connectionProblem}
			<p class="mt-4 text-sm text-yellow-700">Connection problem, retrying…</p>
		{/if}
	{/if}
</div>

<style>
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.animate-spin {
		animation: spin 1s linear infinite;
	}
</style>
