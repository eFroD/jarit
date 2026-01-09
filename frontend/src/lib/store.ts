// src/lib/store.ts

import { writable, derived } from 'svelte/store';
import type { User, APIKey, Recipe } from './types';

// ============ PRIMARY STORES ============

/**
 * JWT authentication token
 * Persisted to localStorage
 */
export const authToken = writable<string | null>(
  typeof window !== 'undefined' ? localStorage.getItem('authToken') : null
);

/**
 * Current authenticated user profile
 */
export const user = writable<User | null>(null);

/**
 * User's stored API keys (for services like Mealie)
 */
export const apiKeys = writable<APIKey[]>([]);

/**
 * Mealie-specific API key (subset of apiKeys)
 */
export const mealieKey = writable<APIKey | null>(null);

/**
 * Recipe being extracted from video
 */
export const extractedRecipe = writable<Recipe | null>(null);

/**
 * Alternative suggested version of extracted recipe
 */
export const suggestedRecipe = writable<Recipe | null>(null);

/**
 * Global loading state
 */
export const isLoading = writable(false);

/**
 * Global error message
 */
export const error = writable<string | null>(null);

// ============ DERIVED STORES ============

/**
 * Computed: whether user is authenticated
 */
export const isAuthenticated = derived(authToken, ($authToken) => !!$authToken);

/**
 * Computed: whether Mealie is configured
 */
export const isMealieConfigured = derived(mealieKey, ($mealieKey) => !!$mealieKey);

// ============ PERSISTENCE ============

/**
 * Persist authToken to localStorage
 */
authToken.subscribe((token) => {
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('authToken', token);
    } else {
      localStorage.removeItem('authToken');
    }
  }
});

/**
 * Clear user data on logout
 */
export function logout() {
  authToken.set(null);
  user.set(null);
  apiKeys.set([]);
  mealieKey.set(null);
  extractedRecipe.set(null);
  error.set(null);
}