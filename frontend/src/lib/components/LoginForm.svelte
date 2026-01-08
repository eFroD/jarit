<!-- LoginForm.svelte -->
<script lang="ts">
  import { api } from '$lib/api';
  import { user, authToken, error, isLoading, apiKeys, mealieKey } from '$lib/store';
  import { goto } from '$app/navigation';

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
      goto('/dashboard');
    } catch (err) {
      localError = err instanceof Error ? err.message : 'Login failed';
      error.set(localError);
    } finally {
      isLoading.set(false);
    }
  }

  function goToRegister() {
    goto('/register');
  }
</script>

<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
  <div class="w-full max-w-md">
    <div class="bg-white rounded-lg shadow-md p-8">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-cyan-600 mb-2">JarIt</h1>
        <p class="text-gray-600">Extract recipes from videos to Mealie</p>
      </div>

      <h2 class="text-2xl font-bold text-gray-900 mb-6">Sign In</h2>

      {#if localError}
        <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p class="text-red-800 text-sm">
            <strong>✗ Error:</strong>
            {localError}
          </p>
        </div>
      {/if}

      <form on:submit={handleLogin} class="space-y-4">
        <div>
          <label for="username" class="block text-sm font-medium text-gray-700 mb-1">
            Username
          </label>
          <input
            id="username"
            type="text"
            bind:value={username}
            required
            disabled={$isLoading}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50"
          />
        </div>

        <div>
          <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <input
            id="password"
            type="password"
            bind:value={password}
            required
            disabled={$isLoading}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50"
          />
        </div>

        <button
          type="submit"
          disabled={$isLoading}
          class="w-full bg-cyan-600 text-white py-2 rounded-lg font-medium hover:bg-cyan-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {$isLoading ? 'Signing In...' : 'Sign In'}
        </button>
      </form>

      <p class="text-center text-sm text-gray-600 mt-6">
        Don't have an account?
        <button
          on:click={goToRegister}
          class="text-cyan-600 hover:text-cyan-700 font-medium underline"
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