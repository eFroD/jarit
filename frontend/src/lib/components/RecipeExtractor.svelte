<!-- RecipeExtractor.svelte -->
<script lang="ts">
  import { api } from '$lib/api';
  import { extractedRecipe, suggestedRecipe, error, isLoading } from '$lib/store';
  import { goto } from '$app/navigation';

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

        goto('/recipe-preview');
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

<div class="bg-white rounded-lg shadow-md p-8">
  <h2 class="text-2xl font-bold text-gray-900 mb-2">Extract Recipe from Video</h2>
  <p class="text-gray-600 mb-6">Paste a video URL from YouTube, TikTok, or other social media platforms</p>

  {#if localError}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
      <p class="text-red-800 text-sm">
        <strong>✗ Error:</strong>
        {localError}
      </p>
    </div>
  {/if}

  <form on:submit={handleExtract} class="space-y-4">
    <div>
      <label for="videoUrl" class="block text-sm font-medium text-gray-700 mb-2">
        Video URL <span class="text-red-500">*</span>
      </label>
      <input
        id="videoUrl"
        type="url"
        bind:value={videoUrl}
        placeholder="https://www.youtube.com/watch?v=... or https://www.tiktok.com/video/..."
        required
        disabled={$isLoading}
        class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50 font-mono text-sm"
      />
      <p class="text-xs text-gray-500 mt-1">Supports YouTube, TikTok, Instagram, and other video platforms</p>
    </div>

    <div>
      <label for="language" class="block text-sm font-medium text-gray-700 mb-2">
        Target Language
      </label>
      <select
        id="language"
        bind:value={targetLanguage}
        disabled={$isLoading}
        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50"
      >
        <option value="english">🇬🇧 English</option>
        <option value="german">🇩🇪 Deutsch</option>
        <option value="spanish">🇪🇸 Español</option>
        <option value="french">🇫🇷 Français</option>
        <option value="italian">🇮🇹 Italiano</option>
      </select>
      <p class="text-xs text-gray-500 mt-1">The recipe will be extracted in this language</p>
    </div>

    <button
      type="submit"
      disabled={$isLoading}
      class="w-full bg-cyan-600 text-white py-3 rounded-lg font-medium hover:bg-cyan-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
    >
      {#if $isLoading}
        <div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        <span>Extracting...</span>
      {:else}
        <span>🎥 Extract Recipe</span>
      {/if}
    </button>
  </form>

  <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
    <p class="text-blue-900 text-sm">
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