<!-- JobHistory.svelte -->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api } from '$lib/api';
	import { errorMessage, locale, t } from '$lib/i18n';
	import { formatDate, formatDateTime, formatRelative } from '$lib/i18n/format';
	import { failureLabel, isTerminal, statusLabel } from '$lib/jobs';
	import type { ExtractionJobSummary, JobStatus } from '$lib/types';

	let jobs: ExtractionJobSummary[] = [];
	let loading = true;
	let loadError = '';
	let actionError = '';
	const busy = new SvelteSet<string>();
	let timer: ReturnType<typeof setTimeout> | undefined;
	let destroyed = false;

	async function load() {
		try {
			jobs = await api.listExtractionJobs();
			loadError = '';
		} catch (err) {
			loadError = errorMessage(err, $t);
		} finally {
			loading = false;
		}
		// Refresh while something is still running, so badges update.
		clearTimeout(timer);
		if (!destroyed && jobs.some((j) => !isTerminal(j.status))) {
			timer = setTimeout(load, 5000);
		}
	}

	function setBusy(id: string, value: boolean) {
		if (value) busy.add(id);
		else busy.delete(id);
	}

	async function retry(job: ExtractionJobSummary) {
		actionError = '';
		setBusy(job.id, true);
		try {
			await api.retryExtractionJob(job.id);
			goto(resolve('/(app)/jobs/[id]', { id: job.id }));
		} catch (err) {
			actionError = errorMessage(err, $t);
			setBusy(job.id, false);
		}
	}

	async function remove(job: ExtractionJobSummary) {
		if (!confirm($t.history_confirmDelete({ name: job.title ?? job.video_url }))) return;
		actionError = '';
		setBusy(job.id, true);
		try {
			await api.deleteExtractionJob(job.id);
			jobs = jobs.filter((j) => j.id !== job.id);
		} catch (err) {
			actionError = errorMessage(err, $t);
		} finally {
			setBusy(job.id, false);
		}
	}

	const BADGE: Record<JobStatus, string> = {
		QUEUED: 'bg-gray-100 text-gray-700',
		FETCHING_DESCRIPTION: 'bg-cyan-100 text-cyan-800',
		TRANSCRIBING: 'bg-cyan-100 text-cyan-800',
		EXTRACTING: 'bg-cyan-100 text-cyan-800',
		COMPLETED: 'bg-green-100 text-green-800',
		FAILED: 'bg-red-100 text-red-800'
	};

	onMount(load);
	onDestroy(() => {
		destroyed = true;
		clearTimeout(timer);
	});
</script>

<div class="rounded-lg bg-white shadow-md">
	{#if actionError}
		<div class="border-b border-red-200 bg-red-50 p-4 text-sm text-red-800">{actionError}</div>
	{/if}

	{#if loading}
		<p class="p-8 text-gray-500">{$t.common_loading}</p>
	{:else if loadError}
		<p class="p-8 text-red-700">{loadError}</p>
	{:else if jobs.length === 0}
		<div class="p-8 text-center">
			<p class="mb-4 text-gray-600">{$t.history_empty}</p>
			<a href={resolve('/dashboard')} class="font-medium text-cyan-600 hover:text-cyan-700"
				>{$t.history_firstRecipe}</a
			>
		</div>
	{:else}
		<ul class="divide-y divide-gray-200">
			{#each jobs as job (job.id)}
				<li class="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
					<div class="min-w-0">
						{#if job.title}
							<p class="truncate font-semibold text-gray-900">{job.title}</p>
						{:else}
							<p class="truncate font-mono text-sm text-gray-700" title={job.video_url}>
								{job.video_url}
							</p>
						{/if}
						<div class="mt-1 flex flex-wrap items-center gap-2 text-xs">
							<span class="text-gray-500" title={formatDateTime(job.created_at, $locale)}>
								{formatRelative(job.created_at, $locale)}
							</span>
							<span class="rounded-full px-2 py-0.5 font-medium {BADGE[job.status]}">
								{statusLabel(job.status, $t)}
							</span>
							{#if job.uploaded_to_mealie_at}
								<span
									class="rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-800"
									title={formatDateTime(job.uploaded_to_mealie_at, $locale)}
								>
									{$t.history_inMealie({ date: formatDate(job.uploaded_to_mealie_at, $locale) })}
								</span>
							{/if}
							{#if job.status === 'FAILED'}
								<span class="text-red-700">{failureLabel(job.failure_reason, $t)}</span>
							{/if}
						</div>
					</div>

					<div class="flex shrink-0 gap-2">
						{#if job.status === 'COMPLETED'}
							<a
								href={resolve('/(app)/jobs/[id]/recipe', { id: job.id })}
								class="rounded-lg bg-cyan-600 px-3 py-1.5 text-sm font-medium !text-white no-underline hover:bg-cyan-700"
								>{$t.history_open}</a
							>
						{:else if job.status === 'FAILED'}
							<button
								on:click={() => retry(job)}
								disabled={busy.has(job.id)}
								class="rounded-lg bg-cyan-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-cyan-700 disabled:opacity-50"
								>{$t.common_tryAgain}</button
							>
						{:else}
							<a
								href={resolve('/(app)/jobs/[id]', { id: job.id })}
								class="rounded-lg bg-gray-200 px-3 py-1.5 text-sm font-medium text-gray-900 no-underline hover:bg-gray-300"
								>{$t.common_viewProgress}</a
							>
						{/if}
						{#if isTerminal(job.status)}
							<button
								on:click={() => remove(job)}
								disabled={busy.has(job.id)}
								class="rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 hover:text-red-800 disabled:opacity-50"
								>{$t.common_delete}</button
							>
						{/if}
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>
