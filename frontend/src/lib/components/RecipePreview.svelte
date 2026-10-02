<!-- RecipePreview.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import {
		currentJobId,
		extractedRecipe,
		suggestedRecipe,
		error,
		isLoading,
		mealieKey
	} from '$lib/store';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import type { ExtractionJob, Recipe } from '$lib/types';

	export let jobId: string;

	let recipe: Recipe | null = null;
	let job: ExtractionJob | null = null;
	let showSuccessMessage = false;
	let dirty = false;
	let saving = false;

	$: recipe = $extractedRecipe;

	onMount(async () => {
		try {
			const loaded = await api.getExtractionJob(jobId);
			if (loaded.status !== 'COMPLETED' || !loaded.result?.recipe) {
				goto(resolve('/(app)/jobs/[id]', { id: jobId }));
				return;
			}
			job = loaded;
			// Keep unsaved edits if this job is already in the editor (e.g. back navigation).
			if ($currentJobId !== jobId || !$extractedRecipe) {
				extractedRecipe.set(loaded.result.recipe);
				suggestedRecipe.set(loaded.result.suggested_version);
				currentJobId.set(jobId);
				dirty = false;
			}
		} catch {
			// request() already put the message into the error store
		}
	});

	function changed(updated: Recipe) {
		extractedRecipe.set(updated);
		dirty = true;
	}

	function editField(field: keyof Recipe, value: string) {
		if (recipe) {
			recipe = Object.assign(recipe, { [field]: value });
			changed(recipe);
		}
	}

	function editIngredient(index: number, value: string) {
		if (recipe && recipe.recipeIngredient) {
			recipe.recipeIngredient[index] = value;
			changed(recipe);
		}
	}

	function addIngredient() {
		if (recipe) {
			if (!recipe.recipeIngredient) recipe.recipeIngredient = [];
			recipe.recipeIngredient = [...recipe.recipeIngredient, ''];
			changed(recipe);
		}
	}

	function removeIngredient(index: number) {
		if (recipe && recipe.recipeIngredient) {
			recipe.recipeIngredient = recipe.recipeIngredient.filter((_, i) => i !== index);
			changed(recipe);
		}
	}

	function editInstruction(index: number, value: string) {
		if (recipe && recipe.recipeInstructions) {
			const instruction = recipe.recipeInstructions[index];
			if (instruction && '@type' in instruction && instruction['@type'] === 'HowToStep') {
				instruction.text = value;
				recipe.recipeInstructions = [...recipe.recipeInstructions];
				changed(recipe);
			}
		}
	}

	function addInstruction() {
		if (recipe) {
			if (!recipe.recipeInstructions) recipe.recipeInstructions = [];
			recipe.recipeInstructions = [
				...recipe.recipeInstructions,
				{ '@type': 'HowToStep', text: '' }
			];
			changed(recipe);
		}
	}

	function removeInstruction(index: number) {
		if (recipe && recipe.recipeInstructions) {
			recipe.recipeInstructions = recipe.recipeInstructions.filter((_, i) => i !== index);
			changed(recipe);
		}
	}

	async function save(): Promise<boolean> {
		if (!recipe || !jobId) return false;
		saving = true;
		try {
			job = await api.saveJobRecipe(jobId, recipe);
			dirty = false;
			return true;
		} catch {
			return false;
		} finally {
			saving = false;
		}
	}

	async function handleUpload() {
		if (!recipe || !jobId) return;

		if (!$mealieKey) {
			error.set('Please configure Mealie API key first');
			return;
		}

		if (job?.uploaded_to_mealie_at) {
			const when = new Date(job.uploaded_to_mealie_at).toLocaleString();
			const again = confirm(
				`This recipe was already uploaded on ${when}. Upload again? This creates another copy in Mealie.`
			);
			if (!again) return;
		}

		isLoading.set(true);
		error.set(null);

		try {
			// The server uploads the stored version, so unsaved edits go first.
			if (dirty && !(await save())) return;
			const result = await api.uploadJobToMealie(jobId);
			if (job) job = { ...job, uploaded_to_mealie_at: result.uploaded_to_mealie_at };
			showSuccessMessage = true;
			error.set(null);

			setTimeout(() => {
				showSuccessMessage = false;
				goto(resolve('/history'));
			}, 2000);
		} catch (err) {
			error.set(err instanceof Error ? err.message : 'Upload failed');
		} finally {
			isLoading.set(false);
		}
	}

	function handleCancel() {
		// The job stays in the history; only leave the editor.
		goto(resolve('/history'));
	}
</script>

{#if recipe}
	<div class="space-y-6">
		<div class="flex items-center justify-between">
			<h1 class="text-3xl font-bold text-gray-900">Review & Edit Recipe</h1>
			<button
				on:click={handleCancel}
				type="button"
				class="rounded-lg bg-gray-300 px-4 py-2 font-medium text-gray-900 transition hover:bg-gray-400"
			>
				← Back
			</button>
		</div>

		{#if showSuccessMessage}
			<div class="rounded-lg border border-green-200 bg-green-50 p-6 text-center">
				<p class="mb-2 font-medium text-green-800">✓ Recipe uploaded successfully!</p>
				<p class="text-sm text-green-700">Redirecting to your history...</p>
			</div>
		{/if}

		{#if $error}
			<div class="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
				<p class="text-yellow-800">
					<strong>⚠ Warning:</strong>
					{$error}
				</p>
			</div>
		{/if}

		<div class="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
			<!-- Edit Form -->
			<div class="order-2 space-y-6 lg:order-1 lg:col-span-2">
				<!-- Recipe Metadata -->
				<div class="space-y-4 rounded-lg bg-white p-6 shadow-md">
					<h2 class="border-b pb-3 text-xl font-bold text-gray-900">Recipe Metadata</h2>

					<div>
						<label class="mb-2 block text-sm font-medium text-gray-700">Recipe Name</label>
						<input
							type="text"
							value={recipe.name}
							on:change={(e) => editField('name', e.currentTarget.value)}
							class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500"
						/>
					</div>

					<div>
						<label class="mb-2 block text-sm font-medium text-gray-700">Description</label>
						<textarea
							value={recipe.description || ''}
							on:change={(e) => editField('description', e.currentTarget.value)}
							rows="3"
							class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500"
						/>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="mb-2 block text-sm font-medium text-gray-700">Category</label>
							<input
								type="text"
								value={recipe.recipeCategory || ''}
								on:change={(e) => editField('recipeCategory', e.currentTarget.value)}
								placeholder="e.g., Breakfast"
								class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500"
							/>
						</div>
						<div>
							<label class="mb-2 block text-sm font-medium text-gray-700">Cuisine</label>
							<input
								type="text"
								value={recipe.recipeCuisine || ''}
								on:change={(e) => editField('recipeCuisine', e.currentTarget.value)}
								placeholder="e.g., Italian"
								class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500"
							/>
						</div>
					</div>
				</div>

				<!-- Timing -->
				<div class="space-y-4 rounded-lg bg-white p-6 shadow-md">
					<h2 class="border-b pb-3 text-xl font-bold text-gray-900">Timing & Yield</h2>

					<div class="grid grid-cols-3 gap-4">
						<div>
							<label class="mb-2 block text-sm font-medium text-gray-700">Prep Time</label>
							<input
								type="text"
								value={recipe.prepTime || ''}
								on:change={(e) => editField('prepTime', e.currentTarget.value)}
								placeholder="PT15M"
								class="w-full rounded-lg border border-gray-300 px-4 py-2 font-mono text-sm focus:border-transparent focus:ring-2 focus:ring-cyan-500"
							/>
							<p class="mt-1 text-xs text-gray-500">ISO 8601 format</p>
						</div>
						<div>
							<label class="mb-2 block text-sm font-medium text-gray-700">Cook Time</label>
							<input
								type="text"
								value={recipe.cookTime || ''}
								on:change={(e) => editField('cookTime', e.currentTarget.value)}
								placeholder="PT30M"
								class="w-full rounded-lg border border-gray-300 px-4 py-2 font-mono text-sm focus:border-transparent focus:ring-2 focus:ring-cyan-500"
							/>
						</div>
						<div>
							<label class="mb-2 block text-sm font-medium text-gray-700">Yield</label>
							<input
								type="text"
								value={recipe.recipeYield || ''}
								on:change={(e) => editField('recipeYield', e.currentTarget.value)}
								placeholder="4 servings"
								class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500"
							/>
						</div>
					</div>
				</div>

				<!-- Ingredients -->
				<div class="space-y-4 rounded-lg bg-white p-6 shadow-md">
					<div class="flex items-center justify-between border-b pb-3">
						<h2 class="text-xl font-bold text-gray-900">Ingredients</h2>
						<button
							type="button"
							on:click={addIngredient}
							class="rounded bg-cyan-100 px-3 py-1 text-xs font-medium text-cyan-700 hover:bg-cyan-200"
						>
							+ Add
						</button>
					</div>

					<div class="max-h-96 space-y-2 overflow-y-auto">
						{#if recipe.recipeIngredient && recipe.recipeIngredient.length > 0}
							{#each recipe.recipeIngredient as ingredient, i (i)}
								<div class="flex gap-2">
									<input
										type="text"
										value={ingredient}
										on:change={(e) => editIngredient(i, e.currentTarget.value)}
										class="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500"
									/>
									<button
										type="button"
										on:click={() => removeIngredient(i)}
										class="px-3 py-2 font-medium text-red-600 hover:text-red-800"
									>
										✕
									</button>
								</div>
							{/each}
						{:else}
							<p class="py-4 text-sm text-gray-500">No ingredients added</p>
						{/if}
					</div>
				</div>

				<!-- Instructions -->
				<div class="space-y-4 rounded-lg bg-white p-6 shadow-md">
					<div class="flex items-center justify-between border-b pb-3">
						<h2 class="text-xl font-bold text-gray-900">Instructions</h2>
						<button
							type="button"
							on:click={addInstruction}
							class="rounded bg-cyan-100 px-3 py-1 text-xs font-medium text-cyan-700 hover:bg-cyan-200"
						>
							+ Add Step
						</button>
					</div>

					<div class="max-h-96 space-y-3 overflow-y-auto">
						{#if recipe.recipeInstructions && recipe.recipeInstructions.length > 0}
							{#each recipe.recipeInstructions as instruction, i (i)}
								{#if instruction && '@type' in instruction && instruction['@type'] === 'HowToStep'}
									<div class="flex gap-2">
										<span
											class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-cyan-100 text-sm font-semibold text-cyan-700"
										>
											{i + 1}
										</span>
										<textarea
											value={instruction.text}
											on:change={(e) => editInstruction(i, e.currentTarget.value)}
											rows="2"
											class="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500"
											placeholder="Enter step instructions..."
										/>
										<button
											type="button"
											on:click={() => removeInstruction(i)}
											class="px-3 py-2 font-medium text-red-600 hover:text-red-800"
										>
											✕
										</button>
									</div>
								{/if}
							{/each}
						{:else}
							<p class="py-4 text-sm text-gray-500">No instructions added</p>
						{/if}
					</div>
				</div>
			</div>

			<!-- Preview Sidebar -->
			<div class="order-1 lg:sticky lg:top-20 lg:col-span-1 lg:max-h-screen lg:overflow-y-auto">
				<div class="sticky top-20 space-y-4 rounded-lg bg-white p-6 shadow-md">
					<h3 class="text-lg font-bold text-gray-900">Preview</h3>

					{#if recipe.image}
						<img
							src={Array.isArray(recipe.image) ? recipe.image[0] : recipe.image}
							alt={recipe.name}
							class="h-48 w-full rounded-lg object-cover"
						/>
					{/if}

					<div class="space-y-3 text-sm">
						<div>
							<p class="font-semibold text-gray-700">Name</p>
							<p class="break-words text-gray-600">{recipe.name || 'Untitled'}</p>
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

					<div class="space-y-2 border-t pt-4">
						<p class="text-xs" class:text-gray-500={!dirty} class:text-amber-600={dirty}>
							{dirty ? 'Unsaved changes' : 'All changes saved'}
							{#if job?.uploaded_to_mealie_at}
								· In Mealie since {new Date(job.uploaded_to_mealie_at).toLocaleDateString()}
							{/if}
						</p>
						<button
							on:click={save}
							type="button"
							disabled={!dirty || saving || $isLoading}
							class="w-full rounded-lg bg-cyan-600 py-2 font-medium text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-50"
						>
							{saving ? 'Saving...' : 'Save changes'}
						</button>
						<button
							on:click={handleUpload}
							disabled={$isLoading}
							class="w-full rounded-lg bg-green-600 py-2 font-medium text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
						>
							{$isLoading ? 'Uploading...' : '✓ Upload to Mealie'}
						</button>
						<button
							on:click={handleCancel}
							type="button"
							disabled={$isLoading}
							class="w-full rounded-lg bg-gray-300 py-2 font-medium text-gray-900 transition hover:bg-gray-400 disabled:opacity-50"
						>
							← Back to history
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{:else}
	<div class="py-12 text-center">
		<p class="text-gray-500">No recipe to preview</p>
	</div>
{/if}
