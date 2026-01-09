<!-- Navigation.svelte -->
<script lang="ts">
  import { user, authToken } from '$lib/store';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  let mobileOpen = false;
  function toggleMobile() { mobileOpen = !mobileOpen; }
  async function handleLogout() {
    authToken.set(null);
    user.set(null);
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    goto('/login');
    mobileOpen = false;
  }
  onMount(() => {
    const handleClickOutside = (e) => {
      if (mobileOpen && !e.target.closest('nav')) {
        mobileOpen = false;
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  });
</script>

<nav class="bg-white shadow-sm border-b border-gray-200">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between items-center h-16">
      <a href="/dashboard" class="text-xl font-bold text-cyan-600 flex items-center gap-2">
        <img src="/logo_800.png" alt="JarIt" class="h-8 w-auto"> 
        <span class="hidden sm:inline">JarIt</span>
      </a>

      <div class="hidden md:flex items-center gap-4">
        {#if $user}
          <span class="text-sm text-gray-700">Welcome, <strong>{$user.username}</strong></span>
          {#if $user.role === 'ADMIN'}
            <a href="/admin" class="px-4 py-2 bg-cyan-600 !text-white rounded-lg hover:bg-cyan-700 text-sm no-underline">Admin Panel</a>
          {/if}
          <button on:click={handleLogout} class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm">Logout</button>
        {/if}
      </div>

      <button on:click={toggleMobile} class="md:hidden p-2">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
        </svg>
      </button>
    </div>
  </div>

  {#if mobileOpen}
    <div class="md:hidden bg-white border-t border-gray-200 shadow-lg absolute w-full top-full z-40">
      {#if $user}
        <div class="px-4 py-4 space-y-2">
          <span class="text-sm text-gray-700 block">Welcome, <strong>{$user.username}</strong></span>
          {#if $user.role === 'ADMIN'}
            <a href="/admin" on:click={toggleMobile} class="block px-4 py-2 bg-cyan-600 !text-white rounded-lg hover:bg-cyan-700 text-sm no-underline">Admin Panel</a>
          {/if}
          <button on:click={handleLogout} class="w-full text-left px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm">Logout</button>
        </div>
      {/if}
    </div>
  {/if}
</nav>


<style>
  nav {
    position: sticky;
    top: 0;
    z-index: 50;
  }
</style>