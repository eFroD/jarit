<!-- src/routes/recipe-preview/+page.svelte -->
<script lang="ts">
	import RecipePreview from '$lib/components/RecipePreview.svelte';
	import { authToken } from '$lib/store';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';

	// Require authentication
	$: if (!$authToken && typeof window !== 'undefined') {
		goto(resolve('/login'));
	}
</script>

<div class="min-h-screen bg-gray-50">
	<main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
		<RecipePreview />
	</main>
</div>
