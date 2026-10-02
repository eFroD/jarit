<!-- LanguageSettings.svelte -->
<script lang="ts">
	import { api } from '$lib/api';
	import { user } from '$lib/store';
	import { errorMessage, LANGUAGES, t, type Locale } from '$lib/i18n';

	let saving = false;
	let saved = false;
	let localError = '';

	async function handleChange(e: Event & { currentTarget: HTMLSelectElement }) {
		const select = e.currentTarget;
		const language = select.value as Locale;
		saving = true;
		saved = false;
		localError = '';
		try {
			// Setting the user switches the app language (see $lib/i18n).
			user.set(await api.updateMe(language));
			saved = true;
			setTimeout(() => (saved = false), 2000);
		} catch (err) {
			localError = errorMessage(err, $t);
			// Keep showing the language that is actually stored.
			select.value = $user?.language ?? 'en';
		} finally {
			saving = false;
		}
	}
</script>

<div class="rounded-lg bg-white p-8 shadow-md">
	<h2 class="mb-2 text-2xl font-bold text-gray-900">{$t.language_title}</h2>
	<p class="mb-6 text-gray-600">{$t.language_subtitle}</p>

	{#if localError}
		<div class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
			<p class="text-sm text-red-800">
				<strong>✗ {$t.common_error}</strong>
				{localError}
			</p>
		</div>
	{/if}

	<label for="userLanguage" class="mb-2 block text-sm font-medium text-gray-700">
		{$t.language_label}
	</label>
	<div class="flex items-center gap-3">
		<select
			id="userLanguage"
			value={$user?.language ?? 'en'}
			on:change={handleChange}
			disabled={saving || !$user}
			class="w-full max-w-xs rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
		>
			{#each LANGUAGES as language (language.code)}
				<option value={language.code}>{language.name}</option>
			{/each}
		</select>
		{#if saved}
			<span class="text-sm text-green-700">✓ {$t.language_saved}</span>
		{/if}
	</div>
</div>
