// src/lib/api.ts

import { authToken, error } from './store';
import { get } from 'svelte/store';
import { ApiError } from './errors';
import { errorMessage, t, type Locale } from './i18n';
import type {
	User,
	APIKey,
	Recipe,
	ExtractionJob,
	ExtractionJobSummary,
	UploadResponse,
	LoginResponse,
	RegisterResponse
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

// ============ HTTP REQUEST HELPER ============

export { ApiError };

// 401 codes that mean the JarIt session itself is invalid (others, e.g. Mealie's, do not log out).
const SESSION_CODES = new Set(['INVALID_TOKEN', 'USER_NOT_FOUND']);

async function toApiError(response: Response): Promise<ApiError> {
	let detail = response.statusText || 'Request failed';
	let code: string | undefined;
	try {
		const body = await response.json();
		if (typeof body.detail === 'string') detail = body.detail;
		if (typeof body.code === 'string') code = body.code;
	} catch {
		// no JSON body
	}
	return new ApiError(detail, response.status, code);
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
	const token = get(authToken);

	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string> | undefined)
	};

	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	try {
		const response = await fetch(`${API_BASE}${endpoint}`, {
			...options,
			headers
		});

		if (!response.ok) {
			const err = await toApiError(response);
			if (err.status === 401 && (!err.code || SESSION_CODES.has(err.code))) {
				authToken.set(null);
			}
			throw err;
		}

		if (response.status === 204) {
			return undefined as T;
		}

		return await response.json();
	} catch (err) {
		error.set(errorMessage(err, get(t)));
		throw err;
	}
}

// ============ API CLIENT ============

export const api = {
	/**
	 * Register a new user
	 */
	async register(
		email: string,
		username: string,
		password: string,
		language: Locale
	): Promise<RegisterResponse> {
		return request<RegisterResponse>('/auth/register', {
			method: 'POST',
			body: JSON.stringify({ email, username, password, language })
		});
	},

	/**
	 * Login with username and password
	 * Returns JWT token
	 */
	async login(username: string, password: string): Promise<LoginResponse> {
		const formData = new FormData();
		formData.append('username', username);
		formData.append('password', password);

		try {
			const response = await fetch(`${API_BASE}/auth/login`, {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				throw await toApiError(response);
			}

			return await response.json();
		} catch (err) {
			error.set(errorMessage(err, get(t)));
			throw err;
		}
	},

	/**
	 * Get current user profile (requires auth)
	 */
	getCurrentUser(): Promise<User> {
		return request<User>('/users/me');
	},

	/**
	 * Change the current user's language
	 */
	updateMe(language: Locale): Promise<User> {
		return request<User>('/users/me', {
			method: 'PATCH',
			body: JSON.stringify({ language })
		});
	},

	/**
	 * All users (admin only)
	 */
	listUsers(): Promise<User[]> {
		return request<User[]>('/admin/users');
	},

	/**
	 * Create a user (admin only)
	 */
	createUser(newUser: {
		email: string;
		username: string;
		password: string;
		role: string;
	}): Promise<User> {
		return request<User>('/admin/users', {
			method: 'POST',
			body: JSON.stringify(newUser)
		});
	},

	/**
	 * Delete a user (admin only)
	 */
	deleteUser(id: number): Promise<void> {
		return request<void>(`/admin/users/${id}`, { method: 'DELETE' });
	},

	/**
	 * List all API keys for current user
	 */
	listApiKeys(): Promise<APIKey[]> {
		return request<APIKey[]>('/users/me/api-keys');
	},

	/**
	 * Create or update an API key
	 */
	async createApiKey(serviceName: string, apiKey: string, baseUrl?: string): Promise<void> {
		return request<void>('/users/me/api-keys', {
			method: 'POST',
			body: JSON.stringify({
				service_name: serviceName,
				api_key: apiKey,
				base_url: baseUrl || null
			})
		});
	},

	/**
	 * Delete an API key
	 */
	async deleteApiKey(serviceName: string): Promise<void> {
		return request<void>(`/users/me/api-keys/${serviceName}`, {
			method: 'DELETE'
		});
	},

	/**
	 * Submit a video URL for extraction; returns the queued job immediately
	 */
	createExtractionJob(url: string, targetLanguage?: Locale): Promise<ExtractionJob> {
		// Without a language the server uses the user's own language.
		return request<ExtractionJob>('/extraction-jobs', {
			method: 'POST',
			body: JSON.stringify(targetLanguage ? { url, target_language: targetLanguage } : { url })
		});
	},

	/**
	 * Current state (and result, once completed) of one extraction job
	 */
	getExtractionJob(id: string): Promise<ExtractionJob> {
		return request<ExtractionJob>(`/extraction-jobs/${id}`);
	},

	/**
	 * The current user's extraction history, newest first
	 */
	listExtractionJobs(): Promise<ExtractionJobSummary[]> {
		return request<ExtractionJobSummary[]>('/extraction-jobs');
	},

	/**
	 * Save the edited recipe of a completed job
	 */
	saveJobRecipe(id: string, recipe: Recipe): Promise<ExtractionJob> {
		return request<ExtractionJob>(`/extraction-jobs/${id}/recipe`, {
			method: 'PUT',
			body: JSON.stringify(recipe)
		});
	},

	/**
	 * Upload the stored recipe of a completed job to Mealie
	 * Requires: configured Mealie API key
	 */
	uploadJobToMealie(id: string): Promise<UploadResponse> {
		return request<UploadResponse>(`/extraction-jobs/${id}/upload-mealie`, {
			method: 'POST'
		});
	},

	/**
	 * Start a failed job again with the same URL and language
	 */
	retryExtractionJob(id: string): Promise<ExtractionJob> {
		return request<ExtractionJob>(`/extraction-jobs/${id}/retry`, {
			method: 'POST'
		});
	},

	/**
	 * Remove a finished job from the history
	 */
	deleteExtractionJob(id: string): Promise<void> {
		return request<void>(`/extraction-jobs/${id}`, {
			method: 'DELETE'
		});
	},

	/**
	 * Verify Mealie user credentials
	 * Used to test if Mealie API key is valid
	 */
	verifyMealieUser(): Promise<{ valid: boolean }> {
		return request<{ valid: boolean }>('/integrations/verify-mealie-user');
	}
};
