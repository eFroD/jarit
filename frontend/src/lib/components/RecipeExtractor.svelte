<!-- RecipeExtractor.svelte -->
<script lang="ts">
	import { api } from '$lib/api';
	import { error, isLoading, user } from '$lib/store';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { errorMessage, LANGUAGES, t, type Locale } from '$lib/i18n';

	let videoUrl = '';
	// Chosen for this submission only; until then the user's own language is preselected.
	let chosenLanguage: Locale | null = null;
	let localError = '';

	$: targetLanguage = chosenLanguage ?? $user?.language ?? 'en';

	async function handleExtract(e: Event) {
		e.preventDefault();
		localError = '';
		error.set(null);

		if (!videoUrl.trim()) {
			localError = $t.extract_missingUrl;
			error.set(localError);
			return;
		}

		isLoading.set(true);

		try {
			// The extraction runs in the background; follow it on its progress page.
			const job = await api.createExtractionJob(videoUrl, targetLanguage);
			chosenLanguage = null;
			goto(resolve('/(app)/jobs/[id]', { id: job.id }));
		} catch (err) {
			localError = errorMessage(err, $t);
			error.set(localError);
		} finally {
			isLoading.set(false);
		}
	}
</script>

<div class="rounded-lg bg-white p-8 shadow-md">
	<h2 class="mb-2 text-2xl font-bold text-gray-900">{$t.extract_title}</h2>
	<p class="mb-6 text-gray-600">{$t.extract_subtitle}</p>

	{#if localError}
		<div class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
			<p class="text-sm text-red-800">
				<strong>✗ {$t.common_error}</strong>
				{localError}
			</p>
		</div>
	{/if}

	<form on:submit={handleExtract} class="space-y-4">
		<div>
			<label for="videoUrl" class="mb-2 block text-sm font-medium text-gray-700">
				{$t.extract_videoUrl} <span class="text-red-500">*</span>
			</label>
			<input
				id="videoUrl"
				type="url"
				bind:value={videoUrl}
				placeholder={$t.extract_videoUrlPlaceholder}
				required
				disabled={$isLoading}
				class="w-full rounded-lg border border-gray-300 px-4 py-3 font-mono text-sm focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
			/>
			<p class="mt-1 text-xs text-gray-500">{$t.extract_videoUrlHint}</p>
		</div>

		<div>
			<label for="language" class="mb-2 block text-sm font-medium text-gray-700">
				{$t.extract_language}
			</label>
			<select
				id="language"
				value={targetLanguage}
				on:change={(e) => (chosenLanguage = e.currentTarget.value as Locale)}
				disabled={$isLoading}
				class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
			>
				{#each LANGUAGES as language (language.code)}
					<option value={language.code}>{language.name}</option>
				{/each}
			</select>
			<p class="mt-1 text-xs text-gray-500">{$t.extract_languageHint}</p>
		</div>

		<button
			type="submit"
			disabled={$isLoading}
			class="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-600 py-3 font-medium text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-50"
		>
			{#if $isLoading}
				<div class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
				<span>{$t.extract_submitting}</span>
			{:else}
				<span>{$t.extract_submit}</span>
			{/if}
		</button>
	</form>

	<div class="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
		<p class="text-sm text-blue-900">
			<strong>{$t.extract_tipLabel}</strong>
			{$t.extract_tip}
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
