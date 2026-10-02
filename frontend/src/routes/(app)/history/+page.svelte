<!-- src/routes/(app)/history/+page.svelte -->
<script lang="ts">
	import JobHistory from '$lib/components/JobHistory.svelte';
	import { t } from '$lib/i18n';
</script>

<main class="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
	<div class="mb-8">
		<h1 class="mb-2 text-4xl font-bold text-gray-900">{$t.history_title}</h1>
		<p class="text-lg text-gray-600">{$t.history_subtitle}</p>
	</div>
	<JobHistory />
</main>
