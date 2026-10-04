<!-- RegisterForm.svelte -->
<script lang="ts">
	import { api } from '$lib/api';
	import { error, isLoading } from '$lib/store';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { errorMessage, LANGUAGES, locale, t } from '$lib/i18n';

	let email = '';
	let username = '';
	let password = '';
	let confirmPassword = '';
	let localError = '';
	let localSuccess = '';

	async function handleRegister(e: Event) {
		e.preventDefault();
		localError = '';
		localSuccess = '';
		isLoading.set(true);

		if (password !== confirmPassword) {
			localError = $t.register_passwordMismatch;
			isLoading.set(false);
			return;
		}

		if (password.length < 8) {
			localError = $t.register_passwordTooShort;
			isLoading.set(false);
			return;
		}

		if (username.length < 3 || username.length > 50) {
			localError = $t.register_usernameLength;
			isLoading.set(false);
			return;
		}

		try {
			// The language shown on this page becomes the account's language.
			await api.register(email, username, password, $locale);
			localSuccess = $t.register_success;
			error.set(null);

			setTimeout(() => {
				goto(resolve('/login'));
			}, 1500);
		} catch (err) {
			localError = errorMessage(err, $t);
			error.set(localError);
		} finally {
			isLoading.set(false);
		}
	}

	function goToLogin() {
		goto(resolve('/login'));
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
	<div class="w-full max-w-md">
		<div class="rounded-lg bg-white p-8 shadow-md">
			<div class="mb-8 text-center">
				<h1 class="mb-2 text-3xl font-bold text-cyan-600">JarIt</h1>
				<p class="text-gray-600">{$t.app_tagline}</p>
			</div>

			<h2 class="mb-6 text-2xl font-bold text-gray-900">{$t.register_title}</h2>

			{#if localError}
				<div class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
					<p class="text-sm text-red-800">
						<strong>✗ {$t.common_error}</strong>
						{localError}
					</p>
				</div>
			{/if}

			{#if localSuccess}
				<div class="mb-4 rounded-lg border border-green-200 bg-green-50 p-4">
					<p class="text-sm text-green-800">
						<strong>✓ {$t.common_success}</strong>
						{localSuccess}
					</p>
				</div>
			{/if}

			<form on:submit={handleRegister} class="space-y-4">
				<div>
					<label for="email" class="mb-1 block text-sm font-medium text-gray-700"
						>{$t.register_email}</label
					>
					<input
						id="email"
						type="email"
						bind:value={email}
						required
						disabled={$isLoading}
						class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
					/>
				</div>

				<div>
					<label for="username" class="mb-1 block text-sm font-medium text-gray-700">
						{$t.register_username}
						<span class="text-xs text-gray-500">{$t.register_usernameHint}</span>
					</label>
					<input
						id="username"
						type="text"
						bind:value={username}
						minlength="3"
						maxlength="50"
						required
						disabled={$isLoading}
						class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
					/>
				</div>

				<div>
					<label for="password" class="mb-1 block text-sm font-medium text-gray-700">
						{$t.register_password}
						<span class="text-xs text-gray-500">{$t.register_passwordHint}</span>
					</label>
					<input
						id="password"
						type="password"
						bind:value={password}
						minlength="8"
						required
						disabled={$isLoading}
						class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
					/>
				</div>

				<div>
					<label for="confirmPassword" class="mb-1 block text-sm font-medium text-gray-700">
						{$t.register_confirmPassword}
					</label>
					<input
						id="confirmPassword"
						type="password"
						bind:value={confirmPassword}
						minlength="8"
						required
						disabled={$isLoading}
						class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
					/>
				</div>

				<div>
					<label for="language" class="mb-1 block text-sm font-medium text-gray-700">
						{$t.register_language}
					</label>
					<select
						id="language"
						bind:value={$locale}
						disabled={$isLoading}
						class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
					>
						{#each LANGUAGES as language (language.code)}
							<option value={language.code}>{language.name}</option>
						{/each}
					</select>
					<p class="mt-1 text-xs text-gray-500">{$t.register_languageHint}</p>
				</div>

				<button
					type="submit"
					disabled={$isLoading}
					class="w-full rounded-lg bg-cyan-600 py-2 font-medium text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-50"
				>
					{$isLoading ? $t.register_submitting : $t.register_submit}
				</button>
			</form>

			<p class="mt-6 text-center text-sm text-gray-600">
				{$t.register_haveAccount}
				<button
					on:click={goToLogin}
					class="font-medium text-cyan-600 underline hover:text-cyan-700"
				>
					{$t.register_loginLink}
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
