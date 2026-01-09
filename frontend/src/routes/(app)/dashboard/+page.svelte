<!-- src/routes/(app)/dashboard/+page.svelte -->
<script lang="ts">
  import RecipeExtractor from '$lib/components/RecipeExtractor.svelte';
  import MealieConfig from '$lib/components/MealieConfig.svelte';
</script>

<div class="min-h-screen bg-gray-50">
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-8">
      <h1 class="text-4xl font-bold text-gray-900 mb-2">Dashboard</h1>
      <p class="text-lg text-gray-600">
        Extract recipes from videos and automatically upload them to your Mealie instance
      </p>
    </div>

    <div class="space-y-8">
      <RecipeExtractor />
      <MealieConfig />
    </div>
  </main>
</div>