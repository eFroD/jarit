<!-- Navigation.svelte -->
<script lang="ts">
  import { user, authToken } from '$lib/store';
  import { goto } from '$app/navigation';

  async function handleLogout() {
    authToken.set(null);
    user.set(null);
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    goto('/login');
  }
</script>

<nav class="bg-white shadow-sm border-b border-gray-200">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between items-center h-16">
      <div class="flex items-center">
        <a href="/dashboard" class="text-2xl font-bold text-cyan-600 hover:text-cyan-700">
          🍳 Recipe Agent
        </a>
      </div>

      <div class="flex items-center gap-4">
        {#if $user}
          <div class="flex items-center gap-3">
            <span class="text-sm text-gray-700">
              Welcome, <strong class="text-gray-900">{$user.username}</strong>
            </span>
            {#if $user.role === 'ADMIN'}
             <a href="/admin" class="inline-block px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 transition-colors duration-200 cursor-pointer font-medium text-sm no-underline">
               Admin Panel
              </a>      
            {/if}
            <button
              on:click={handleLogout}
              class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium text-sm"
            >
              Logout
            </button>
          </div>
        {:else if $authToken}
          <div class="flex items-center gap-3">
            <span class="text-sm text-gray-500">Loading...</span>
          </div>
        {/if}
      </div>
    </div>
  </div>
</nav>

<style>
  nav {
    position: sticky;
    top: 0;
    z-index: 50;
  }
</style>