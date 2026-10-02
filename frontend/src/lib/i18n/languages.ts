// src/lib/i18n/languages.ts

/** Languages for the app and for extracted recipes; same codes as the backend. */
export type Locale = 'en' | 'de' | 'es' | 'fr' | 'it';

export const DEFAULT_LOCALE: Locale = 'en';

/** Display order of every language select, with names in their own language. */
export const LANGUAGES: { code: Locale; name: string }[] = [
	{ code: 'en', name: 'English' },
	{ code: 'de', name: 'Deutsch' },
	{ code: 'es', name: 'Español' },
	{ code: 'fr', name: 'Français' },
	{ code: 'it', name: 'Italiano' }
];

export function isLocale(value: unknown): value is Locale {
	return LANGUAGES.some((l) => l.code === value);
}

/** First supported language among browser language tags ("de-AT" → "de"), else English. */
export function matchLocale(tags: readonly string[]): Locale {
	for (const tag of tags) {
		const primary = tag.split('-')[0].toLowerCase();
		if (isLocale(primary)) return primary;
	}
	return DEFAULT_LOCALE;
}
