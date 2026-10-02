<!-- src/routes/(app)/dashboard/+page.svelte -->
<script lang="ts">
	import RecipeExtractor from '$lib/components/RecipeExtractor.svelte';
	import MealieConfig from '$lib/components/MealieConfig.svelte';
	import ActiveJobs from '$lib/components/ActiveJobs.svelte';
	import LanguageSettings from '$lib/components/LanguageSettings.svelte';
	import { t } from '$lib/i18n';
</script>

<div class="min-h-screen bg-gray-50">
	<main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
		<div class="mb-8">
			<h1 class="mb-2 text-4xl font-bold text-gray-900">{$t.dashboard_title}</h1>
			<p class="text-lg text-gray-600">{$t.dashboard_subtitle}</p>
		</div>

		<div class="space-y-8">
			<ActiveJobs />
			<RecipeExtractor />
			<MealieConfig />
			<LanguageSettings />
		</div>
	</main>
</div>
