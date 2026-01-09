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

<div class="bg-white rounded-lg shadow-md p-8">
  <h2 class="text-2xl font-bold text-gray-900 mb-2">Mealie Configuration</h2>
  <p class="text-gray-600 mb-6">
    Configure your Mealie instance to automatically upload extracted recipes
  </p>

  {#if localError}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
      <p class="text-red-800 text-sm">
        <strong>✗ Error:</strong>
        {localError}
      </p>
    </div>
  {/if}

  {#if localSuccess}
    <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
      <p class="text-green-800 text-sm">
        <strong>✓ Success:</strong>
        {localSuccess}
      </p>
    </div>
  {/if}

  {#if $mealieKey && !showForm}
    <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
      <div class="flex justify-between items-start">
        <div>
          <p class="text-green-800 font-medium mb-1">✓ Mealie API Key Configured</p>
          <p class="text-green-700 text-sm">
            Base URL: <code class="bg-green-100 px-2 py-1 rounded text-xs font-mono">{baseUrl}</code>
          </p>
          <p class="text-green-700 text-xs mt-2">
            Last updated: {new Date($mealieKey.created_at).toLocaleDateString()}
          </p>
        </div>
        <button
          type="button"
          on:click={() => (showForm = true)}
          class="text-green-700 hover:text-green-900 font-medium text-sm underline"
        >
          Edit
        </button>
      </div>
    </div>

    <div class="flex gap-3">
      <button
        type="button"
        on:click={() => (showForm = true)}
        class="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition font-medium text-sm"
      >
        Update Key
      </button>
      <button
        type="button"
        on:click={handleDelete}
        disabled={$isLoading}
        class="flex-1 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition font-medium text-sm disabled:opacity-50"
      >
        Remove
      </button>
    </div>
  {/if}

  {#if !$mealieKey || showForm}
    <form on:submit={handleSave} class="space-y-4">
      <div>
        <label for="mealieUrl" class="block text-sm font-medium text-gray-700 mb-2">
          Mealie Base URL <span class="text-red-500">*</span>
        </label>
        <input
          id="mealieUrl"
          type="url"
          bind:value={baseUrl}
          placeholder="https://mealie.example.com"
          required
          disabled={$isLoading}
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50 font-mono text-sm"
        />
        <p class="text-xs text-gray-500 mt-1">
          The URL where your Mealie instance is running (e.g., https://mealie.yourdomain.com)
        </p>
      </div>

      <div>
        <label for="mealieApiKey" class="block text-sm font-medium text-gray-700 mb-2">
          Mealie API Key <span class="text-red-500">*</span>
        </label>
        <input
          id="mealieApiKey"
          type="password"
          bind:value={apiKey}
          placeholder="Paste your Mealie API key here"
          required
          disabled={$isLoading}
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50 font-mono text-sm"
        />
        <p class="text-xs text-gray-500 mt-1">
          Generate this in Mealie: Settings → API Tokens
        </p>
      </div>

      <div class="flex gap-3">
        <button
          type="submit"
          disabled={$isLoading}
          class="flex-1 bg-cyan-600 text-white py-2 rounded-lg font-medium hover:bg-cyan-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {$isLoading ? 'Saving...' : 'Save Configuration'}
        </button>
        {#if $mealieKey}
          <button
            type="button"
            on:click={() => (showForm = false)}
            disabled={$isLoading}
            class="flex-1 bg-gray-300 text-gray-900 py-2 rounded-lg font-medium hover:bg-gray-400 transition disabled:opacity-50"
          >
            Cancel
          </button>
        {/if}
      </div>
    </form>

    <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
      <p class="text-blue-900 text-sm mb-2">
        <strong>📖 Need help?</strong>
      </p>
      <ol class="text-blue-900 text-sm space-y-1 list-decimal list-inside">
        <li>Go to your Mealie instance (Settings → Profile)</li>
        <li>Generate a new API token under "Long-lived tokens"</li>
        <li>Copy and paste the token above</li>
        <li>Save and you're ready to upload recipes!</li>
      </ol>
    </div>
  {/if}
</div>