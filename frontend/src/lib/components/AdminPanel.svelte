<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { authToken } from '$lib/store';
	import { errorMessage, t } from '$lib/i18n';
	import type { User } from '$lib/types';

	let users: User[] = [];
	let loading = false;
	let error = '';
	let success = '';

	// Create form
	let showCreateModal = false;
	let newUser = {
		email: '',
		username: '',
		password: '',
		role: 'USER'
	};

	// Filter & Sort
	let search = '';
	let sortBy = 'username';

	$: filteredUsers = users
		.filter(
			(u) =>
				u.username.toLowerCase().includes(search.toLowerCase()) ||
				u.email.toLowerCase().includes(search.toLowerCase())
		)
		.sort((a, b) => {
			if (sortBy === 'username') return a.username.localeCompare(b.username);
			if (sortBy === 'email') return a.email.localeCompare(b.email);
			return 0;
		});

	async function loadUsers() {
		if (!$authToken) return;

		loading = true;
		error = '';

		try {
			users = await api.listUsers();
		} catch (e) {
			error = errorMessage(e, $t);
		} finally {
			loading = false;
		}
	}

	async function createUser() {
		if (!newUser.email || !newUser.username || !newUser.password) {
			error = $t.admin_allFieldsRequired;
			return;
		}

		try {
			const created = await api.createUser(newUser);
			users = [created, ...users];

			// Reset form
			newUser = { email: '', username: '', password: '', role: 'USER' };
			showCreateModal = false;
			success = $t.admin_created({ name: created.username });

			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			error = errorMessage(e, $t);
		}
	}

	async function deleteUser(id: number, username: string) {
		if (!confirm($t.admin_confirmDelete({ name: username }))) return;

		try {
			await api.deleteUser(id);
			users = users.filter((u) => u.id !== id);
			success = $t.admin_deleted({ name: username });
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			error = errorMessage(e, $t);
		}
	}

	onMount(loadUsers);
</script>

<div class="admin-panel">
	<!-- Header -->
	<div class="panel-header">
		<div>
			<h1>{$t.admin_title}</h1>
			<p class="subtitle">{$t.admin_subtitle}</p>
		</div>
		<button class="btn-primary" on:click={() => (showCreateModal = true)}>
			{$t.admin_newUser}
		</button>
	</div>

	<!-- Stats -->
	<div class="stats-grid">
		<div class="stat-card">
			<div class="stat-number">{users.length}</div>
			<div>{$t.admin_totalUsers}</div>
		</div>
		<div class="stat-card">
			<div class="stat-number admin-count">
				{users.filter((u) => u.role === 'ADMIN').length}
			</div>
			<div>{$t.admin_admins}</div>
		</div>
	</div>

	<!-- Messages -->
	{#if error}
		<div class="alert error">{error}</div>
	{/if}
	{#if success}
		<div class="alert success">{success}</div>
	{/if}

	<!-- Search -->
	<div class="search-bar">
		<input type="text" placeholder={$t.admin_search} bind:value={search} class="search-input" />
		<button
			class="btn-secondary"
			on:click={loadUsers}
			disabled={loading}
			aria-label={$t.admin_refresh}
			title={$t.admin_refresh}
		>
			{loading ? '⟳' : '🔄'}
		</button>
	</div>

	<!-- Users Table -->
	{#if loading}
		<div class="loading">{$t.admin_loadingUsers}</div>
	{:else if filteredUsers.length === 0}
		<div class="empty">{$t.admin_noUsers}</div>
	{:else}
		<div class="users-table">
			{#each filteredUsers as user (user.id)}
				<div class="user-row">
					<div class="user-info">
						<div class="username">{user.username}</div>
						<div class="email">{user.email}</div>
					</div>
					<div class="user-role">
						<span class="role-badge {user.role.toLowerCase()}">
							{user.role === 'ADMIN' ? $t.admin_role_ADMIN : $t.admin_role_USER}
						</span>
					</div>
					<div class="user-actions">
						<button class="btn-danger" on:click={() => deleteUser(user.id, user.username)}>
							{$t.common_delete}
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Create User Modal -->
{#if showCreateModal}
	<div class="modal-overlay" on:click={() => (showCreateModal = false)}>
		<div class="modal" on:click|stopPropagation>
			<h2>{$t.admin_createTitle}</h2>
			<form on:submit|preventDefault={createUser}>
				<input bind:value={newUser.username} placeholder={$t.admin_username} required />
				<input bind:value={newUser.email} type="email" placeholder={$t.admin_email} required />
				<input
					bind:value={newUser.password}
					type="password"
					placeholder={$t.admin_password}
					required
				/>
				<select bind:value={newUser.role}>
					<option value="USER">{$t.admin_role_USER}</option>
					<option value="ADMIN">{$t.admin_role_ADMIN}</option>
				</select>
				<div class="modal-actions">
					<button type="button" class="btn-secondary" on:click={() => (showCreateModal = false)}>
						{$t.common_cancel}
					</button>
					<button type="submit" class="btn-primary" disabled={loading}>
						{loading ? $t.admin_creating : $t.admin_create}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.admin-panel {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
	}

	.panel-header h1 {
		font-size: 2.5rem;
		margin: 0;
		color: #111827;
	}

	.subtitle {
		color: #6b7280;
		margin: 0.25rem 0 0 0;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 1rem;
		margin-bottom: 2rem;
	}

	.stat-card {
		background: white;
		padding: 1.5rem;
		border-radius: 12px;
		text-align: center;
		box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
	}

	.stat-number {
		font-size: 2rem;
		font-weight: bold;
		margin-bottom: 0.25rem;
		color: #111827;
	}

	.admin-count {
		color: #0891b2;
	}

	.alert {
		padding: 1rem;
		border-radius: 8px;
		margin-bottom: 1rem;
	}

	.alert.error {
		background: #fee2e2;
		color: #dc2626;
		border-left: 4px solid #dc2626;
	}

	.alert.success {
		background: #d1fae5;
		color: #059669;
		border-left: 4px solid #059669;
	}

	.search-bar {
		display: flex;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
	}

	.search-input {
		flex: 1;
		padding: 0.75rem 1rem;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		font-size: 1rem;
		color: #111827;
	}

	.search-input:focus {
		outline: none;
		border-color: #0891b2;
		box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.1);
	}

	.search-input::placeholder {
		color: #9ca3af;
	}

	.btn-primary {
		background: #0891b2;
		color: white;
		padding: 0.75rem 1.5rem;
		border: none;
		border-radius: 8px;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.2s;
	}

	.btn-primary:hover {
		background: #0e7490;
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-secondary {
		background: white;
		color: #374151;
		padding: 0.75rem 1rem;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-secondary:hover:not(:disabled) {
		background: #f9fafb;
		border-color: #9ca3af;
	}

	.btn-secondary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-danger {
		background: #dc2626;
		color: white;
		padding: 0.5rem 1rem;
		border: none;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.2s;
	}

	.btn-danger:hover {
		background: #b91c1c;
	}

	.loading,
	.empty {
		text-align: center;
		padding: 3rem;
		color: #6b7280;
		background: white;
		border-radius: 12px;
	}

	.users-table {
		background: white;
		border-radius: 12px;
		overflow: hidden;
		box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
	}

	.user-row {
		display: grid;
		grid-template-columns: 2fr 1fr auto;
		gap: 1rem;
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid #e5e7eb;
		align-items: center;
	}

	.user-row:last-child {
		border-bottom: none;
	}

	.user-row:hover {
		background: #f9fafb;
	}

	.user-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.username {
		font-weight: 600;
		color: #111827;
		font-size: 1rem;
	}

	.email {
		color: #6b7280;
		font-size: 0.875rem;
	}

	.user-role {
		display: flex;
		justify-content: center;
	}

	.role-badge {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		border-radius: 9999px;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
	}

	.role-badge.admin {
		background: #dbeafe;
		color: #1e40af;
	}

	.role-badge.user {
		background: #e5e7eb;
		color: #374151;
	}

	.user-actions {
		display: flex;
		justify-content: flex-end;
	}

	.modal-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.modal {
		background: white;
		padding: 2rem;
		border-radius: 12px;
		max-width: 500px;
		width: 90%;
		box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
	}

	.modal h2 {
		margin: 0 0 1.5rem 0;
		color: #111827;
		font-size: 1.5rem;
	}

	.modal form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.modal input,
	.modal select {
		width: 100%;
		padding: 0.75rem;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		font-size: 1rem;
		color: #111827;
	}

	.modal input:focus,
	.modal select:focus {
		outline: none;
		border-color: #0891b2;
		box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.1);
	}

	.modal input::placeholder {
		color: #9ca3af;
	}

	.modal-actions {
		display: flex;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}

	.modal-actions button {
		flex: 1;
	}
</style>
