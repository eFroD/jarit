<!-- LoginForm.svelte -->
<script lang="ts">
	import { api } from '$lib/api';
	import { user, authToken, error, isLoading, apiKeys, mealieKey } from '$lib/store';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';

	let username = '';
	let password = '';
	let localError = '';

	async function handleLogin(e: Event) {
		e.preventDefault();
		localError = '';
		isLoading.set(true);

		try {
			if (!username || !password) {
				throw new Error('Please enter username and password');
			}

			const response = await api.login(username, password);
			authToken.set(response.access_token);

			const currentUser = await api.getCurrentUser();
			user.set(currentUser);

			const keys = await api.listApiKeys();
			apiKeys.set(keys);
			mealieKey.set(keys.find((k) => k.service_name === 'mealie') || null);

			error.set(null);
			goto(resolve('/dashboard'));
		} catch (err) {
			localError = err instanceof Error ? err.message : 'Login failed';
			error.set(localError);
		} finally {
			isLoading.set(false);
		}
	}

	function goToRegister() {
		goto(resolve('/register'));
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
	<div class="w-full max-w-md">
		<div class="rounded-lg bg-white p-8 shadow-md">
			<div class="mb-8 text-center">
				<h1 class="mb-2 flex items-center text-3xl font-bold text-cyan-600">
					<img src="/logo_800.png" alt="JarIt" class="mr-2 h-8 w-auto" /> JarIt
				</h1>
				<p class="text-gray-600">Extract recipes from videos to Mealie</p>
			</div>

			<h2 class="mb-6 text-2xl font-bold text-gray-900">Sign In</h2>

			{#if localError}
				<div class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
					<p class="text-sm text-red-800">
						<strong>✗ Error:</strong>
						{localError}
					</p>
				</div>
			{/if}

			<form on:submit={handleLogin} class="space-y-4">
				<div>
					<label for="username" class="mb-1 block text-sm font-medium text-gray-700">
						Username
					</label>
					<input
						id="username"
						type="text"
						bind:value={username}
						required
						disabled={$isLoading}
						class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
					/>
				</div>

				<div>
					<label for="password" class="mb-1 block text-sm font-medium text-gray-700">
						Password
					</label>
					<input
						id="password"
						type="password"
						bind:value={password}
						required
						disabled={$isLoading}
						class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
					/>
				</div>

				<button
					type="submit"
					disabled={$isLoading}
					class="w-full rounded-lg bg-cyan-600 py-2 font-medium text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-50"
				>
					{$isLoading ? 'Signing In...' : 'Sign In'}
				</button>
			</form>

			<p class="mt-6 text-center text-sm text-gray-600">
				Don't have an account?
				<button
					on:click={goToRegister}
					class="font-medium text-cyan-600 underline hover:text-cyan-700"
				>
					Register here
				</button>
			</p>
		</div>
	</div>
</div>

<style>
	:global(body) {
		background-color: #f9fafb;
	}
</style>
