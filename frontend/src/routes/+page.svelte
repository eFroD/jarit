<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authToken } from '$lib/store';
	import { get } from 'svelte/store';

	onMount(() => {
		const token = get(authToken);
		if (token) {
			goto('/dashboard');
		} else {
			goto('/login');
		}
	});
</script>

<div class="flex min-h-screen items-center justify-center">
	<p class="text-gray-500">Loading...</p>
</div>
