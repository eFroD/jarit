<!-- src/routes/(app)/+layout.svelte -->
<script lang="ts">
	import { authToken } from '$lib/store';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';

	// Require authentication for app routes
	$: if (!$authToken && typeof window !== 'undefined') {
		goto(resolve('/login'));
	}
</script>

<div class="min-h-screen bg-gray-50">
	<slot />
</div>
