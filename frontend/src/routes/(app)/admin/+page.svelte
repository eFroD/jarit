<script lang="ts">
	import AdminPanel from '$lib/components/AdminPanel.svelte';
	import { user } from '$lib/store';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';

	onMount(() => {
		if (!$user || $user.role !== 'ADMIN') {
			goto(resolve('/dashboard'));
		}
	});

	$: if ($user && $user.role !== 'ADMIN') {
		goto(resolve('/dashboard'));
	}
</script>

{#if $user && $user.role === 'ADMIN'}
	<div class="min-h-screen bg-gray-50">
		<AdminPanel />
	</div>
{:else}
	<div class="flex min-h-screen items-center justify-center bg-gray-50">
		<p class="text-gray-500">Checking permissions...</p>
	</div>
{/if}

<svelte:head>
	<title>Admin Panel - JarIt</title>
</svelte:head>
