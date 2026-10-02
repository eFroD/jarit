<!-- RecipeExtractor.svelte -->
<script lang="ts">
	import { api } from '$lib/api';
	import { extractedRecipe, suggestedRecipe, error, isLoading } from '$lib/store';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';

	let videoUrl = '';
	let targetLanguage = 'english';
	let localError = '';

	async function handleExtract(e: Event) {
		e.preventDefault();
		localError = '';
		error.set(null);

		if (!videoUrl.trim()) {
			localError = 'Please enter a video URL';
			error.set(localError);
			return;
		}

		isLoading.set(true);

		try {
			const result = await api.extractRecipe(videoUrl, targetLanguage);

			if (result.recipe) {
				extractedRecipe.set(result.recipe);
				suggestedRecipe.set(result.suggested_version);

				if (result.error_info?.error) {
					error.set(`Warning: ${result.error_info.error}`);
				}

				goto(resolve('/recipe-preview'));
			} else {
				throw new Error('Failed to extract recipe. Please check the URL and try again.');
			}
		} catch (err) {
			localError = err instanceof Error ? err.message : 'Extraction failed';
			error.set(localError);
		} finally {
			isLoading.set(false);
		}
	}
</script>

<div class="rounded-lg bg-white p-8 shadow-md">
	<h2 class="mb-2 text-2xl font-bold text-gray-900">Extract Recipe from Video</h2>
	<p class="mb-6 text-gray-600">
		Paste a video URL from YouTube, TikTok, or other social media platforms
	</p>

	{#if localError}
		<div class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
			<p class="text-sm text-red-800">
				<strong>✗ Error:</strong>
				{localError}
			</p>
		</div>
	{/if}

	<form on:submit={handleExtract} class="space-y-4">
		<div>
			<label for="videoUrl" class="mb-2 block text-sm font-medium text-gray-700">
				Video URL <span class="text-red-500">*</span>
			</label>
			<input
				id="videoUrl"
				type="url"
				bind:value={videoUrl}
				placeholder="https://www.youtube.com/watch?v=... or https://www.tiktok.com/video/..."
				required
				disabled={$isLoading}
				class="w-full rounded-lg border border-gray-300 px-4 py-3 font-mono text-sm focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
			/>
			<p class="mt-1 text-xs text-gray-500">
				Supports YouTube, TikTok, Instagram, and other video platforms
			</p>
		</div>

		<div>
			<label for="language" class="mb-2 block text-sm font-medium text-gray-700">
				Target Language
			</label>
			<select
				id="language"
				bind:value={targetLanguage}
				disabled={$isLoading}
				class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
			>
				<option value="english">🇬🇧 English</option>
				<option value="german">🇩🇪 Deutsch</option>
				<option value="spanish">🇪🇸 Español</option>
				<option value="french">🇫🇷 Français</option>
				<option value="italian">🇮🇹 Italiano</option>
			</select>
			<p class="mt-1 text-xs text-gray-500">The recipe will be extracted in this language</p>
		</div>

		<button
			type="submit"
			disabled={$isLoading}
			class="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-600 py-3 font-medium text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-50"
		>
			{#if $isLoading}
				<div class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
				<span>Extracting...</span>
			{:else}
				<span>🎥 Extract Recipe</span>
			{/if}
		</button>
	</form>

	<div class="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
		<p class="text-sm text-blue-900">
			<strong>💡 Tip:</strong> Make sure the video contains a clear recipe with ingredients and instructions.
			The AI will extract structured recipe data in JSON format.
		</p>
	</div>
</div>

<style>
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	:global(.animate-spin) {
		animation: spin 1s linear infinite;
	}
</style>
