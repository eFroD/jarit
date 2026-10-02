<!-- MealieConfig.svelte -->
<script lang="ts">
	import { api } from '$lib/api';
	import { mealieKey, apiKeys, error, isLoading } from '$lib/store';

	let baseUrl = '';
	let apiKey = '';
	let showForm = false;
	let localError = '';
	let localSuccess = '';

	$: if ($mealieKey) {
		baseUrl = $mealieKey.base_url || '';
		showForm = false;
	}

	async function handleSave(e: Event) {
		e.preventDefault();
		localError = '';
		localSuccess = '';

		if (!baseUrl.trim() || !apiKey.trim()) {
			localError = 'Please fill in all fields';
			return;
		}

		isLoading.set(true);

		try {
			await api.createApiKey('mealie', apiKey, baseUrl);

			const keys = await api.listApiKeys();
			apiKeys.set(keys);
			mealieKey.set(keys.find((k) => k.service_name === 'mealie') || null);

			localSuccess = 'Mealie configuration saved successfully!';
			apiKey = '';
			showForm = false;
			error.set(null);

			setTimeout(() => {
				localSuccess = '';
			}, 3000);
		} catch (err) {
			localError = err instanceof Error ? err.message : 'Failed to save configuration';
			error.set(localError);
		} finally {
			isLoading.set(false);
		}
	}

	async function handleDelete() {
		if (!confirm('Are you sure you want to delete the Mealie API key?')) return;

		isLoading.set(true);
		localError = '';

		try {
			await api.deleteApiKey('mealie');

			const keys = await api.listApiKeys();
			apiKeys.set(keys);
			mealieKey.set(null);

			localSuccess = 'Mealie configuration removed.';
			showForm = false;
			error.set(null);

			setTimeout(() => {
				localSuccess = '';
			}, 2000);
		} catch (err) {
			localError = err instanceof Error ? err.message : 'Failed to delete key';
			error.set(localError);
		} finally {
			isLoading.set(false);
		}
	}
</script>

<div class="rounded-lg bg-white p-8 shadow-md">
	<h2 class="mb-2 text-2xl font-bold text-gray-900">Mealie Configuration</h2>
	<p class="mb-6 text-gray-600">
		Configure your Mealie instance to automatically upload extracted recipes
	</p>

	{#if localError}
		<div class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
			<p class="text-sm text-red-800">
				<strong>✗ Error:</strong>
				{localError}
			</p>
		</div>
	{/if}

	{#if localSuccess}
		<div class="mb-4 rounded-lg border border-green-200 bg-green-50 p-4">
			<p class="text-sm text-green-800">
				<strong>✓ Success:</strong>
				{localSuccess}
			</p>
		</div>
	{/if}

	{#if $mealieKey && !showForm}
		<div class="mb-6 rounded-lg border border-green-200 bg-green-50 p-4">
			<div class="flex items-start justify-between">
				<div>
					<p class="mb-1 font-medium text-green-800">✓ Mealie API Key Configured</p>
					<p class="text-sm text-green-700">
						Base URL: <code class="rounded bg-green-100 px-2 py-1 font-mono text-xs">{baseUrl}</code
						>
					</p>
					<p class="mt-2 text-xs text-green-700">
						Last updated: {new Date($mealieKey.created_at).toLocaleDateString()}
					</p>
				</div>
				<button
					type="button"
					on:click={() => (showForm = true)}
					class="text-sm font-medium text-green-700 underline hover:text-green-900"
				>
					Edit
				</button>
			</div>
		</div>

		<div class="flex gap-3">
			<button
				type="button"
				on:click={() => (showForm = true)}
				class="flex-1 rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-cyan-700"
			>
				Update Key
			</button>
			<button
				type="button"
				on:click={handleDelete}
				disabled={$isLoading}
				class="flex-1 rounded-lg bg-red-100 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-200 disabled:opacity-50"
			>
				Remove
			</button>
		</div>
	{/if}

	{#if !$mealieKey || showForm}
		<form on:submit={handleSave} class="space-y-4">
			<div>
				<label for="mealieUrl" class="mb-2 block text-sm font-medium text-gray-700">
					Mealie Base URL <span class="text-red-500">*</span>
				</label>
				<input
					id="mealieUrl"
					type="url"
					bind:value={baseUrl}
					placeholder="https://mealie.example.com"
					required
					disabled={$isLoading}
					class="w-full rounded-lg border border-gray-300 px-4 py-2 font-mono text-sm focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
				/>
				<p class="mt-1 text-xs text-gray-500">
					The URL where your Mealie instance is running (e.g., https://mealie.yourdomain.com)
				</p>
			</div>

			<div>
				<label for="mealieApiKey" class="mb-2 block text-sm font-medium text-gray-700">
					Mealie API Key <span class="text-red-500">*</span>
				</label>
				<input
					id="mealieApiKey"
					type="password"
					bind:value={apiKey}
					placeholder="Paste your Mealie API key here"
					required
					disabled={$isLoading}
					class="w-full rounded-lg border border-gray-300 px-4 py-2 font-mono text-sm focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
				/>
				<p class="mt-1 text-xs text-gray-500">Generate this in Mealie: Settings → API Tokens</p>
			</div>

			<div class="flex gap-3">
				<button
					type="submit"
					disabled={$isLoading}
					class="flex-1 rounded-lg bg-cyan-600 py-2 font-medium text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-50"
				>
					{$isLoading ? 'Saving...' : 'Save Configuration'}
				</button>
				{#if $mealieKey}
					<button
						type="button"
						on:click={() => (showForm = false)}
						disabled={$isLoading}
						class="flex-1 rounded-lg bg-gray-300 py-2 font-medium text-gray-900 transition hover:bg-gray-400 disabled:opacity-50"
					>
						Cancel
					</button>
				{/if}
			</div>
		</form>

		<div class="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
			<p class="mb-2 text-sm text-blue-900">
				<strong>📖 Need help?</strong>
			</p>
			<ol class="list-inside list-decimal space-y-1 text-sm text-blue-900">
				<li>Go to your Mealie instance (Settings → Profile)</li>
				<li>Generate a new API token under "Long-lived tokens"</li>
				<li>Copy and paste the token above</li>
				<li>Save and you're ready to upload recipes!</li>
			</ol>
		</div>
	{/if}
</div>
