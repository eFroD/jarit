<!-- src/routes/(app)/jobs/[id]/+page.svelte -->
<script lang="ts">
	import JobProgress from '$lib/components/JobProgress.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<main class="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
	{#key data.jobId}
		<JobProgress jobId={data.jobId} />
	{/key}
</main>
