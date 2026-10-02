<!-- ActiveJobs.svelte -->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { api } from '$lib/api';
	import { isTerminal, STATUS_LABELS } from '$lib/jobs';
	import type { ExtractionJobSummary } from '$lib/types';

	// Running extractions, so leaving a progress page never loses track of a job.
	let active: ExtractionJobSummary[] = [];
	let timer: ReturnType<typeof setTimeout> | undefined;
	let destroyed = false;

	async function load() {
		try {
			const jobs = await api.listExtractionJobs();
			active = jobs.filter((j) => !isTerminal(j.status));
		} catch {
			// Not essential for the dashboard; keep the last known list.
		}
		clearTimeout(timer);
		if (!destroyed && active.length > 0) {
			timer = setTimeout(load, 5000);
		}
	}

	onMount(load);
	onDestroy(() => {
		destroyed = true;
		clearTimeout(timer);
	});
</script>

{#if active.length > 0}
	<div class="rounded-lg border border-cyan-200 bg-cyan-50 p-6">
		<h2 class="mb-3 text-lg font-bold text-gray-900">In progress</h2>
		<ul class="space-y-2">
			{#each active as job (job.id)}
				<li class="flex items-center justify-between gap-4">
					<div class="min-w-0">
						<p class="truncate font-mono text-sm text-gray-700">{job.video_url}</p>
						<p class="text-xs text-cyan-800">{STATUS_LABELS[job.status]}</p>
					</div>
					<a
						href={resolve('/(app)/jobs/[id]', { id: job.id })}
						class="shrink-0 rounded-lg bg-cyan-600 px-3 py-1.5 text-sm font-medium !text-white no-underline hover:bg-cyan-700"
						>View progress</a
					>
				</li>
			{/each}
		</ul>
	</div>
{/if}
