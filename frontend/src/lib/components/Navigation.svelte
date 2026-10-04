<!-- Navigation.svelte -->
<script lang="ts">
	import { user, authToken } from '$lib/store';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n';

	let mobileOpen = false;
	function toggleMobile() {
		mobileOpen = !mobileOpen;
	}
	async function handleLogout() {
		authToken.set(null);
		user.set(null);
		localStorage.removeItem('authToken');
		localStorage.removeItem('user');
		goto(resolve('/login'));
		mobileOpen = false;
	}
	onMount(() => {
		const handleClickOutside = (e: MouseEvent) => {
			if (mobileOpen && !(e.target as HTMLElement).closest('nav')) {
				mobileOpen = false;
			}
		};
		document.addEventListener('click', handleClickOutside);
		return () => document.removeEventListener('click', handleClickOutside);
	});
</script>

<nav class="border-b border-gray-200 bg-white shadow-sm">
	<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
		<div class="flex h-16 items-center justify-between">
			<a
				href={resolve('/dashboard')}
				class="flex items-center gap-2 text-xl font-bold text-cyan-600"
			>
				<img src="/logo_800.png" alt="JarIt" class="h-8 w-auto" />
				<span class="hidden sm:inline">JarIt</span>
			</a>

			<div class="hidden items-center gap-4 md:flex">
				{#if $user}
					<span class="text-sm text-gray-700"
						>{$t.nav_welcome} <strong>{$user.username}</strong></span
					>
					<a
						href={resolve('/history')}
						class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 no-underline hover:bg-gray-100"
						>{$t.nav_history}</a
					>
					{#if $user.role === 'ADMIN'}
						<a
							href={resolve('/admin')}
							class="rounded-lg bg-cyan-600 px-4 py-2 text-sm !text-white no-underline hover:bg-cyan-700"
							>{$t.nav_admin}</a
						>
					{/if}
					<button
						on:click={handleLogout}
						class="rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
						>{$t.nav_logout}</button
					>
				{/if}
			</div>

			<button on:click={toggleMobile} class="p-2 md:hidden" aria-label={$t.nav_menu}>
				<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 6h16M4 12h16M4 18h16"
					/>
				</svg>
			</button>
		</div>
	</div>

	{#if mobileOpen}
		<div
			class="absolute top-full z-40 w-full border-t border-gray-200 bg-white shadow-lg md:hidden"
		>
			{#if $user}
				<div class="space-y-2 px-4 py-4">
					<span class="block text-sm text-gray-700"
						>{$t.nav_welcome} <strong>{$user.username}</strong></span
					>
					<a
						href={resolve('/history')}
						on:click={toggleMobile}
						class="block rounded-lg px-4 py-2 text-sm font-medium text-gray-700 no-underline hover:bg-gray-100"
						>{$t.nav_history}</a
					>
					{#if $user.role === 'ADMIN'}
						<a
							href={resolve('/admin')}
							on:click={toggleMobile}
							class="block rounded-lg bg-cyan-600 px-4 py-2 text-sm !text-white no-underline hover:bg-cyan-700"
							>{$t.nav_admin}</a
						>
					{/if}
					<button
						on:click={handleLogout}
						class="w-full rounded-lg bg-red-600 px-4 py-2 text-left text-sm text-white hover:bg-red-700"
						>{$t.nav_logout}</button
					>
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
