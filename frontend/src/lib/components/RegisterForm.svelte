<!-- RegisterForm.svelte -->
<script lang="ts">
  import { api } from '$lib/api';
  import { error, isLoading } from '$lib/store';
  import { goto } from '$app/navigation';

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
      localError = 'Passwords do not match';
      isLoading.set(false);
      return;
    }

    if (password.length < 8) {
      localError = 'Password must be at least 8 characters';
      isLoading.set(false);
      return;
    }

    if (username.length < 3 || username.length > 50) {
      localError = 'Username must be between 3 and 50 characters';
      isLoading.set(false);
      return;
    }

    try {
      await api.register(email, username, password);
      localSuccess = 'Account created! Redirecting to login...';
      error.set(null);

      setTimeout(() => {
        goto('/login');
      }, 1500);
    } catch (err) {
      localError = err instanceof Error ? err.message : 'Registration failed';
      error.set(localError);
    } finally {
      isLoading.set(false);
    }
  }

  function goToLogin() {
    goto('/login');
  }
</script>

<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
  <div class="w-full max-w-md">
    <div class="bg-white rounded-lg shadow-md p-8">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-cyan-600 mb-2">JarIt</h1>
        <p class="text-gray-600">Extract recipes from videos to Mealie</p>
      </div>

      <h2 class="text-2xl font-bold text-gray-900 mb-6">Create Account</h2>

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

      <form on:submit={handleRegister} class="space-y-4">
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <input
            id="email"
            type="email"
            bind:value={email}
            required
            disabled={$isLoading}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50"
          />
        </div>

        <div>
          <label for="username" class="block text-sm font-medium text-gray-700 mb-1">
            Username <span class="text-gray-500 text-xs">(3-50 chars)</span>
          </label>
          <input
            id="username"
            type="text"
            bind:value={username}
            minlength="3"
            maxlength="50"
            required
            disabled={$isLoading}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50"
          />
        </div>

        <div>
          <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
            Password <span class="text-gray-500 text-xs">(min 8 chars)</span>
          </label>
          <input
            id="password"
            type="password"
            bind:value={password}
            minlength="8"
            required
            disabled={$isLoading}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50"
          />
        </div>

        <div>
          <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-1">
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            type="password"
            bind:value={confirmPassword}
            minlength="8"
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
          {$isLoading ? 'Creating Account...' : 'Register'}
        </button>
      </form>

      <p class="text-center text-sm text-gray-600 mt-6">
        Already have an account?
        <button
          on:click={goToLogin}
          class="text-cyan-600 hover:text-cyan-700 font-medium underline"
        >
          Sign in here
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