<!-- src/routes/recipe-preview/+page.svelte -->
<script lang="ts">
  import RecipePreview from '$lib/components/RecipePreview.svelte';
  import { authToken } from '$lib/store';
  import { goto } from '$app/navigation';

  // Require authentication
  $: if (!$authToken && typeof window !== 'undefined') {
    goto('/login');
  }
</script>

<div class="min-h-screen bg-gray-50">
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <RecipePreview />
  </main>
</div>