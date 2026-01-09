<!-- src/routes/+layout.svelte -->
<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { authToken, user, apiKeys, mealieKey } from '$lib/store';
  import { goto } from '$app/navigation';
  import Navigation from '$lib/components/Navigation.svelte';
  import { api } from '$lib/api';

  let initialized = false;
  onMount(async () => {
    if ($authToken && !$user) {
      try {
        const userData = await api.getCurrentUser();
        user.set(userData);

        const keys = await api.listApiKeys();
        apiKeys.set(keys);
        const mealieApiKey = keys.find(k => k.service_name === 'mealie');
        mealieKey.set(mealieApiKey || null);
      } catch (err) {
        console.error('Failed to initialize user data:', err);
        authToken.set(null);
        user.set(null);
      }
    }
    initialized = true;
  });

  $: if (initialized && !$authToken && typeof window !== 'undefined') {
    const path = window.location.pathname;

    if (!path.includes('/login') && !path.includes('/register') && path !== '/') {
      goto('/login');
    }
  }
</script>

<svelte:head>
  <title>JarIt - Extract recipes to Mealie</title>
  <meta name="description" content="Extract recipes from videos to your Mealie instance using AI" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
</svelte:head>

{#if $authToken}
  <Navigation />
{/if}

<slot />