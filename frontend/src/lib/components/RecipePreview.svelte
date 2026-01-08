<!-- RecipePreview.svelte -->
<script lang="ts">
  import { api } from '$lib/api';
  import { extractedRecipe, error, isLoading, mealieKey } from '$lib/store';
  import { goto } from '$app/navigation';
  import type { Recipe } from '$lib/types';

  let recipe: Recipe | null = null;
  let showSuccessMessage = false;

  $: recipe = $extractedRecipe;

  function editField(field: keyof Recipe, value: any) {
    if (recipe) {
      recipe[field] = value;
      extractedRecipe.set(recipe);
    }
  }

  function editIngredient(index: number, value: string) {
    if (recipe && recipe.recipeIngredient) {
      recipe.recipeIngredient[index] = value;
      extractedRecipe.set(recipe);
    }
  }

  function addIngredient() {
    if (recipe) {
      if (!recipe.recipeIngredient) recipe.recipeIngredient = [];
      recipe.recipeIngredient = [...recipe.recipeIngredient, ''];
      extractedRecipe.set(recipe);
    }
  }

  function removeIngredient(index: number) {
    if (recipe && recipe.recipeIngredient) {
      recipe.recipeIngredient = recipe.recipeIngredient.filter((_, i) => i !== index);
      extractedRecipe.set(recipe);
    }
  }

  function editInstruction(index: number, value: string) {
    if (recipe && recipe.recipeInstructions) {
      const instruction = recipe.recipeInstructions[index];
      if (instruction && '@type' in instruction && instruction['@type'] === 'HowToStep') {
        instruction.text = value;
        recipe.recipeInstructions = [...recipe.recipeInstructions];
        extractedRecipe.set(recipe);
      }
    }
  }

  function addInstruction() {
    if (recipe) {
      if (!recipe.recipeInstructions) recipe.recipeInstructions = [];
      recipe.recipeInstructions = [...recipe.recipeInstructions, { '@type': 'HowToStep', text: '' }];
      extractedRecipe.set(recipe);
    }
  }

  function removeInstruction(index: number) {
    if (recipe && recipe.recipeInstructions) {
      recipe.recipeInstructions = recipe.recipeInstructions.filter((_, i) => i !== index);
      extractedRecipe.set(recipe);
    }
  }

  async function handleUpload() {
    if (!recipe) return;

    if (!$mealieKey) {
      error.set('Please configure Mealie API key first');
      return;
    }

    isLoading.set(true);
    error.set(null);

    try {
      await api.uploadToMealie(recipe);
      showSuccessMessage = true;
      error.set(null);

      setTimeout(() => {
        extractedRecipe.set(null);
        showSuccessMessage = false;
        goto('/dashboard');
      }, 2000);
    } catch (err) {
      error.set(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      isLoading.set(false);
    }
  }

  function handleCancel() {
    extractedRecipe.set(null);
    goto('/dashboard');
  }
</script>

{#if recipe}
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold text-gray-900">Review & Edit Recipe</h1>
      <button
        on:click={handleCancel}
        type="button"
        class="px-4 py-2 bg-gray-300 text-gray-900 rounded-lg hover:bg-gray-400 transition font-medium"
      >
        ← Back
      </button>
    </div>

    {#if showSuccessMessage}
      <div class="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
        <p class="text-green-800 font-medium mb-2">✓ Recipe uploaded successfully!</p>
        <p class="text-green-700 text-sm">Redirecting to dashboard...</p>
      </div>
    {/if}

    {#if $error}
      <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p class="text-yellow-800">
          <strong>⚠ Warning:</strong>
          {$error}
        </p>
      </div>
    {/if}

    <div class="grid grid-cols-3 gap-6">
      <!-- Edit Form -->
      <div class="col-span-2 space-y-6">
        <!-- Recipe Metadata -->
        <div class="bg-white rounded-lg shadow-md p-6 space-y-4">
          <h2 class="text-xl font-bold text-gray-900 border-b pb-3">Recipe Metadata</h2>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Recipe Name</label>
            <input
              type="text"
              value={recipe.name}
              on:change={(e) => editField('name', e.currentTarget.value)}
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Description</label>
            <textarea
              value={recipe.description || ''}
              on:change={(e) => editField('description', e.currentTarget.value)}
              rows="3"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Category</label>
              <input
                type="text"
                value={recipe.recipeCategory || ''}
                on:change={(e) => editField('recipeCategory', e.currentTarget.value)}
                placeholder="e.g., Breakfast"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Cuisine</label>
              <input
                type="text"
                value={recipe.recipeCuisine || ''}
                on:change={(e) => editField('recipeCuisine', e.currentTarget.value)}
                placeholder="e.g., Italian"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        <!-- Timing -->
        <div class="bg-white rounded-lg shadow-md p-6 space-y-4">
          <h2 class="text-xl font-bold text-gray-900 border-b pb-3">Timing & Yield</h2>

          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Prep Time</label>
              <input
                type="text"
                value={recipe.prepTime || ''}
                on:change={(e) => editField('prepTime', e.currentTarget.value)}
                placeholder="PT15M"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent text-sm font-mono"
              />
              <p class="text-xs text-gray-500 mt-1">ISO 8601 format</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Cook Time</label>
              <input
                type="text"
                value={recipe.cookTime || ''}
                on:change={(e) => editField('cookTime', e.currentTarget.value)}
                placeholder="PT30M"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent text-sm font-mono"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Yield</label>
              <input
                type="text"
                value={recipe.recipeYield || ''}
                on:change={(e) => editField('recipeYield', e.currentTarget.value)}
                placeholder="4 servings"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        <!-- Ingredients -->
        <div class="bg-white rounded-lg shadow-md p-6 space-y-4">
          <div class="flex justify-between items-center border-b pb-3">
            <h2 class="text-xl font-bold text-gray-900">Ingredients</h2>
            <button
              type="button"
              on:click={addIngredient}
              class="text-xs px-3 py-1 bg-cyan-100 text-cyan-700 rounded hover:bg-cyan-200 font-medium"
            >
              + Add
            </button>
          </div>

          <div class="space-y-2 max-h-96 overflow-y-auto">
            {#if recipe.recipeIngredient && recipe.recipeIngredient.length > 0}
              {#each recipe.recipeIngredient as ingredient, i (i)}
                <div class="flex gap-2">
                  <input
                    type="text"
                    value={ingredient}
                    on:change={(e) => editIngredient(i, e.currentTarget.value)}
                    class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    on:click={() => removeIngredient(i)}
                    class="px-3 py-2 text-red-600 hover:text-red-800 font-medium"
                  >
                    ✕
                  </button>
                </div>
              {/each}
            {:else}
              <p class="text-gray-500 text-sm py-4">No ingredients added</p>
            {/if}
          </div>
        </div>

        <!-- Instructions -->
        <div class="bg-white rounded-lg shadow-md p-6 space-y-4">
          <div class="flex justify-between items-center border-b pb-3">
            <h2 class="text-xl font-bold text-gray-900">Instructions</h2>
            <button
              type="button"
              on:click={addInstruction}
              class="text-xs px-3 py-1 bg-cyan-100 text-cyan-700 rounded hover:bg-cyan-200 font-medium"
            >
              + Add Step
            </button>
          </div>

          <div class="space-y-3 max-h-96 overflow-y-auto">
            {#if recipe.recipeInstructions && recipe.recipeInstructions.length > 0}
              {#each recipe.recipeInstructions as instruction, i (i)}
                {#if instruction && '@type' in instruction && instruction['@type'] === 'HowToStep'}
                  <div class="flex gap-2">
                    <span class="flex-shrink-0 w-8 h-8 bg-cyan-100 text-cyan-700 rounded-full flex items-center justify-center font-semibold text-sm">
                      {i + 1}
                    </span>
                    <textarea
                      value={instruction.text}
                      on:change={(e) => editInstruction(i, e.currentTarget.value)}
                      rows="2"
                      class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent resize-none"
                      placeholder="Enter step instructions..."
                    />
                    <button
                      type="button"
                      on:click={() => removeInstruction(i)}
                      class="px-3 py-2 text-red-600 hover:text-red-800 font-medium"
                    >
                      ✕
                    </button>
                  </div>
                {/if}
              {/each}
            {:else}
              <p class="text-gray-500 text-sm py-4">No instructions added</p>
            {/if}
          </div>
        </div>
      </div>

      <!-- Preview Sidebar -->
      <div class="col-span-1">
        <div class="bg-white rounded-lg shadow-md p-6 sticky top-20 space-y-4">
          <h3 class="text-lg font-bold text-gray-900">Preview</h3>

          {#if recipe.image}
            <img
              src={recipe.image}
              alt={recipe.name}
              class="w-full rounded-lg object-cover h-48"
            />
          {/if}

          <div class="space-y-3 text-sm">
            <div>
              <p class="font-semibold text-gray-700">Name</p>
              <p class="text-gray-600 break-words">{recipe.name || 'Untitled'}</p>
            </div>

            {#if recipe.recipeCategory}
              <div>
                <p class="font-semibold text-gray-700">Category</p>
                <p class="text-gray-600">{recipe.recipeCategory}</p>
              </div>
            {/if}

            {#if recipe.recipeCuisine}
              <div>
                <p class="font-semibold text-gray-700">Cuisine</p>
                <p class="text-gray-600">{recipe.recipeCuisine}</p>
              </div>
            {/if}

            {#if recipe.recipeYield}
              <div>
                <p class="font-semibold text-gray-700">Yield</p>
                <p class="text-gray-600">{recipe.recipeYield}</p>
              </div>
            {/if}

            <div>
              <p class="font-semibold text-gray-700">Ingredients</p>
              <p class="text-gray-600">{recipe.recipeIngredient?.length || 0} items</p>
            </div>

            <div>
              <p class="font-semibold text-gray-700">Instructions</p>
              <p class="text-gray-600">{recipe.recipeInstructions?.length || 0} steps</p>
            </div>
          </div>

          <div class="border-t pt-4 space-y-2">
            <button
              on:click={handleUpload}
              disabled={$isLoading}
              class="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {$isLoading ? 'Uploading...' : '✓ Upload to Mealie'}
            </button>
            <button
              on:click={handleCancel}
              type="button"
              disabled={$isLoading}
              class="w-full bg-gray-300 text-gray-900 py-2 rounded-lg hover:bg-gray-400 transition font-medium disabled:opacity-50"
            >
              ✗ Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{:else}
  <div class="text-center py-12">
    <p class="text-gray-500">No recipe to preview</p>
  </div>
{/if}