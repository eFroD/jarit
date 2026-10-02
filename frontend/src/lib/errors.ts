// src/lib/errors.ts

/**
 * Error thrown for non-2xx responses; keeps the HTTP status and the server's error code
 */
export class ApiError extends Error {
	constructor(
		message: string,
		public status: number,
		public code?: string
	) {
		super(message);
	}
}
