<!-- src/routes/(auth)/+layout.svelte -->
<script lang="ts">
  import { authToken } from '$lib/store';
  import { goto } from '$app/navigation';

  // Redirect to dashboard if already authenticated
  $: if ($authToken && typeof window !== 'undefined') {
    goto('/dashboard');
  }
</script>

<div class="min-h-screen bg-gray-50">
  <slot />
</div>