// src/lib/i18n/index.ts

import { derived, writable } from 'svelte/store';
import { browser } from '$app/environment';
import { ApiError } from '$lib/errors';
import { user } from '$lib/store';
import { isLocale, matchLocale, DEFAULT_LOCALE, type Locale } from './languages';
import { en, type Messages } from './messages/en';
import { de } from './messages/de';
import { es } from './messages/es';
import { fr } from './messages/fr';
import { it } from './messages/it';

export type { Locale, Messages };
export { LANGUAGES } from './languages';

const dictionaries: Record<Locale, Messages> = { en, de, es, fr, it };

/** Language of the browser, used before login and after logout. */
export function browserLocale(): Locale {
	if (!browser) return DEFAULT_LOCALE;
	return matchLocale(navigator.languages?.length ? navigator.languages : [navigator.language]);
}

/** Current UI language. Follows the logged-in user's stored language. */
export const locale = writable<Locale>(browserLocale());

/** Messages of the current language: `$t.key` or `$t.key({ … })`. */
export const t = derived(locale, ($locale) => dictionaries[$locale]);

// The stored language wins over the browser language once a user is loaded.
user.subscribe(($user) => {
	if ($user && isLocale($user.language)) locale.set($user.language);
	else if (!$user) locale.set(browserLocale());
});

if (browser) {
	locale.subscribe(($locale) => {
		document.documentElement.lang = $locale;
	});
}

function lookup(m: Messages, key: string): string | undefined {
	const value = (m as Record<string, unknown>)[key];
	return typeof value === 'string' ? value : undefined;
}

/** A message for the user in the current language; server texts are never shown as-is. */
export function errorMessage(err: unknown, m: Messages): string {
	if (err instanceof ApiError) {
		const byCode = err.code ? lookup(m, `error_${err.code}`) : undefined;
		if (byCode) return byCode;
		if (err.status >= 500) return m.error_5xx;
		return lookup(m, `error_${err.status}`) ?? m.error_generic;
	}
	// fetch() rejects with a TypeError when the server cannot be reached.
	if (err instanceof TypeError) return m.error_network;
	return m.error_generic;
}
