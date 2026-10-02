<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { authToken } from '$lib/store';
	import { get } from 'svelte/store';
	import { t } from '$lib/i18n';

	onMount(() => {
		const token = get(authToken);
		if (token) {
			goto(resolve('/dashboard'));
		} else {
			goto(resolve('/login'));
		}
	});
</script>

<div class="flex min-h-screen items-center justify-center">
	<p class="text-gray-500">{$t.common_loading}</p>
</div>
