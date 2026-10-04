<!-- src/routes/(app)/jobs/[id]/recipe/+page.svelte -->
<script lang="ts">
	import RecipePreview from '$lib/components/RecipePreview.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
	{#key data.jobId}
		<RecipePreview jobId={data.jobId} />
	{/key}
</main>
