// src/lib/i18n/format.ts

import type { Locale } from './languages';

export function formatDate(value: string | Date, locale: Locale): string {
	return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(new Date(value));
}

export function formatDateTime(value: string | Date, locale: Locale): string {
	return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(
		new Date(value)
	);
}

/** "2 minutes ago", "yesterday", … in the given language. */
export function formatRelative(value: string | Date, locale: Locale, now = Date.now()): string {
	const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
	const seconds = Math.round((new Date(value).getTime() - now) / 1000);
	if (Math.abs(seconds) < 60) return rtf.format(0, 'second');
	const minutes = Math.round(seconds / 60);
	if (Math.abs(minutes) < 60) return rtf.format(minutes, 'minute');
	const hours = Math.round(minutes / 60);
	if (Math.abs(hours) < 24) return rtf.format(hours, 'hour');
	return rtf.format(Math.round(hours / 24), 'day');
}
