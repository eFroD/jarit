// src/lib/api.ts

import { authToken, error } from './store';
import { get } from 'svelte/store';
import type {
  User,
  APIKey,
  Recipe,
  ExtractRecipeResponse,
  LoginResponse,
  RegisterResponse,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

// ============ HTTP REQUEST HELPER ============

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = get(authToken);

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle unauthorized
    if (response.status === 401) {
      authToken.set(null);
      error.set('Session expired. Please login again.');
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      let errorMsg = 'Request failed';

      try {
        const errorData = await response.json();
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMsg = errorData.detail[0]?.msg || errorData.detail[0] || errorMsg;
          } else {
            errorMsg = errorData.detail;
          }
        } else if (errorData.message) {
          errorMsg = errorData.message;
        }
      } catch {
        errorMsg = response.statusText || errorMsg;
      }

      throw new Error(errorMsg);
    }

    return await response.json();
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown error occurred';
    error.set(msg);
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
    password: string
  ): Promise<RegisterResponse> {
    return request<RegisterResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, username, password }),
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
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Invalid username or password');
      }

      return await response.json();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed';
      error.set(msg);
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
   * List all API keys for current user
   */
  listApiKeys(): Promise<APIKey[]> {
    return request<APIKey[]>('/users/me/api-keys');
  },

  /**
   * Create or update an API key
   */
  async createApiKey(
    serviceName: string,
    apiKey: string,
    baseUrl?: string
  ): Promise<void> {
    return request<void>('/users/me/api-keys', {
      method: 'POST',
      body: JSON.stringify({
        service_name: serviceName,
        api_key: apiKey,
        base_url: baseUrl || null,
      }),
    });
  },

  /**
   * Delete an API key
   */
  async deleteApiKey(serviceName: string): Promise<void> {
    return request<void>(`/users/me/api-keys/${serviceName}`, {
      method: 'DELETE',
    });
  },

  /**
   * Extract recipe from video URL using AI agent
   * Requires: authenticated user, video URL, target language
   */
  extractRecipe(
    url: string,
    targetLanguage: string = 'english'
  ): Promise<ExtractRecipeResponse> {
    return request<ExtractRecipeResponse>('/recipes/extract-recipe', {
      method: 'POST',
      body: JSON.stringify({
        url,
        target_language: targetLanguage,
      }),
    });
  },

  /**
   * Upload extracted recipe to Mealie instance
   * Requires: authenticated user, configured Mealie API key
   */
  uploadToMealie(recipe: Recipe): Promise<void> {
    return request<void>('/integrations/upload-mealie', {
      method: 'POST',
      body: JSON.stringify(recipe),
    });
  },

  /**
   * Verify Mealie user credentials
   * Used to test if Mealie API key is valid
   */
  verifyMealieUser(): Promise<any> {
    return request<any>('/integrations/verify-mealie-user');
  },
};