// src/lib/i18n/messages/en.ts
// Source dictionary: every other language must have exactly these keys (checked by `npm run check`).

export const en = {
	// App
	app_title: 'JarIt - Extract recipes to Mealie',
	app_description: 'Extract recipes from videos to your Mealie instance using AI',
	app_tagline: 'Extract recipes from videos to Mealie',

	// Common
	common_loading: 'Loading…',
	common_cancel: 'Cancel',
	common_delete: 'Delete',
	common_edit: 'Edit',
	common_saving: 'Saving…',
	common_error: 'Error:',
	common_success: 'Success:',
	common_warning: 'Warning:',
	common_tryAgain: 'Try again',
	common_restarting: 'Restarting…',
	common_viewProgress: 'View progress',
	common_backToHistory: '← Back to history',

	// Navigation
	nav_welcome: 'Welcome,',
	nav_history: 'History',
	nav_admin: 'Admin Panel',
	nav_logout: 'Logout',
	nav_menu: 'Open menu',

	// Login
	login_title: 'Sign In',
	login_username: 'Username',
	login_password: 'Password',
	login_submit: 'Sign In',
	login_submitting: 'Signing in…',
	login_noAccount: "Don't have an account?",
	login_registerLink: 'Register here',
	login_missingFields: 'Please enter username and password.',

	// Register
	register_title: 'Create Account',
	register_email: 'Email',
	register_username: 'Username',
	register_usernameHint: '(3–50 characters)',
	register_password: 'Password',
	register_passwordHint: '(at least 8 characters)',
	register_confirmPassword: 'Confirm password',
	register_language: 'Language',
	register_languageHint: 'Used for the app and as the default language of your recipes.',
	register_submit: 'Register',
	register_submitting: 'Creating account…',
	register_success: 'Account created! Redirecting to sign in…',
	register_passwordMismatch: 'Passwords do not match.',
	register_passwordTooShort: 'Password must be at least 8 characters.',
	register_usernameLength: 'Username must be between 3 and 50 characters.',
	register_haveAccount: 'Already have an account?',
	register_loginLink: 'Sign in here',

	// Dashboard
	dashboard_title: 'Dashboard',
	dashboard_subtitle: 'Extract recipes from videos and upload them to your Mealie instance',

	// Recipe extraction form
	extract_title: 'Extract Recipe from Video',
	extract_subtitle: 'Paste a video URL from YouTube, TikTok or other social media platforms',
	extract_videoUrl: 'Video URL',
	extract_videoUrlPlaceholder: 'https://www.youtube.com/watch?v=… or https://www.tiktok.com/…',
	extract_videoUrlHint: 'Supports YouTube, TikTok, Instagram and other video platforms',
	extract_language: 'Recipe language',
	extract_languageHint: 'The recipe will be written in this language, even if the video is not.',
	extract_submit: '🎥 Extract Recipe',
	extract_submitting: 'Starting…',
	extract_missingUrl: 'Please enter a video URL.',
	extract_tipLabel: '💡 Tip:',
	extract_tip:
		'Make sure the video contains a clear recipe with ingredients and instructions. The AI turns it into a structured recipe.',

	// Language settings
	language_title: 'Language',
	language_subtitle: 'Language of the app and default language for new recipes',
	language_label: 'Your language',
	language_saved: 'Language saved.',

	// Mealie configuration
	mealie_title: 'Mealie Configuration',
	mealie_subtitle: 'Connect your Mealie instance to upload extracted recipes',
	mealie_configured: '✓ Mealie API key configured',
	mealie_baseUrl: 'Base URL:',
	mealie_lastUpdated: (p: { date: string }) => `Last updated: ${p.date}`,
	mealie_update: 'Update key',
	mealie_remove: 'Remove',
	mealie_baseUrlLabel: 'Mealie base URL',
	mealie_baseUrlHint:
		'The URL where your Mealie instance is running (e.g. https://mealie.yourdomain.com)',
	mealie_apiKeyLabel: 'Mealie API key',
	mealie_apiKeyPlaceholder: 'Paste your Mealie API key here',
	mealie_apiKeyHint: 'Create it in Mealie under Settings → API Tokens',
	mealie_save: 'Save configuration',
	mealie_fillAll: 'Please fill in all fields.',
	mealie_saved: 'Mealie configuration saved.',
	mealie_removed: 'Mealie configuration removed.',
	mealie_confirmDelete: 'Do you really want to delete the Mealie API key?',
	mealie_helpTitle: '📖 Need help?',
	mealie_help1: 'Open your Mealie instance (Settings → Profile)',
	mealie_help2: 'Create a new API token under "Long-lived tokens"',
	mealie_help3: 'Copy the token and paste it above',
	mealie_help4: 'Save, and you are ready to upload recipes!',

	// Job statuses and failure reasons
	jobs_status_QUEUED: 'Waiting',
	jobs_status_FETCHING_DESCRIPTION: 'Fetching video description',
	jobs_status_TRANSCRIBING: 'Transcribing audio',
	jobs_status_EXTRACTING: 'Extracting recipe',
	jobs_status_COMPLETED: 'Completed',
	jobs_status_FAILED: 'Failed',
	jobs_failure_VIDEO_UNREACHABLE: 'Video unreachable',
	jobs_failure_NO_RECIPE_FOUND: 'No recipe found in this video',
	jobs_failure_TRANSCRIPTION_FAILED: 'Transcription failed',
	jobs_failure_LLM_ERROR: 'Language model error',
	jobs_failure_TIMEOUT: 'Timed out',
	jobs_failure_RESTARTED: 'Interrupted by an application restart',
	jobs_failure_UNKNOWN: 'Unknown error, please try again',
	jobs_inProgress: 'In progress',

	// Progress page
	progress_notFoundTitle: 'Extraction not found',
	progress_goToHistory: 'Go to your history',
	progress_title: 'Extracting recipe',
	progress_runningFor: (p: { duration: string }) =>
		`Running for ${p.duration} · you can leave this page and come back later`,
	progress_duration: (p: { minutes: number; seconds: number }) =>
		p.minutes > 0 ? `${p.minutes} min ${p.seconds} s` : `${p.seconds} s`,
	progress_notNeeded: '(not needed)',
	progress_done: '✓ Done, opening the recipe…',
	progress_connectionProblem: 'Connection problem, retrying…',

	// History
	history_title: 'History',
	history_subtitle: 'All your recipe extractions, newest first',
	history_empty: 'No extractions yet.',
	history_firstRecipe: 'Extract your first recipe',
	history_open: 'Open',
	history_inMealie: (p: { date: string }) => `In Mealie · ${p.date}`,
	history_confirmDelete: (p: { name: string }) => `Delete "${p.name}" from your history?`,

	// Recipe editor
	editor_title: 'Review & Edit Recipe',
	editor_back: '← Back',
	editor_uploadSuccess: '✓ Recipe uploaded!',
	editor_redirecting: 'Redirecting to your history…',
	editor_metadata: 'Recipe details',
	editor_name: 'Recipe name',
	editor_description: 'Description',
	editor_category: 'Category',
	editor_categoryPlaceholder: 'e.g. Breakfast',
	editor_cuisine: 'Cuisine',
	editor_cuisinePlaceholder: 'e.g. Italian',
	editor_timing: 'Timing & Yield',
	editor_prepTime: 'Prep time',
	editor_isoHint: 'ISO 8601 format',
	editor_cookTime: 'Cook time',
	editor_yield: 'Yield',
	editor_yieldPlaceholder: '4 servings',
	editor_ingredients: 'Ingredients',
	editor_add: '+ Add',
	editor_noIngredients: 'No ingredients added',
	editor_instructions: 'Instructions',
	editor_addStep: '+ Add step',
	editor_stepPlaceholder: 'Describe this step…',
	editor_noInstructions: 'No instructions added',
	editor_remove: 'Remove',
	editor_preview: 'Preview',
	editor_previewName: 'Name',
	editor_untitled: 'Untitled',
	editor_ingredientCount: (p: { count: number }) =>
		p.count === 1 ? '1 ingredient' : `${p.count} ingredients`,
	editor_stepCount: (p: { count: number }) => (p.count === 1 ? '1 step' : `${p.count} steps`),
	editor_unsaved: 'Unsaved changes',
	editor_allSaved: 'All changes saved',
	editor_inMealieSince: (p: { date: string }) => `In Mealie since ${p.date}`,
	editor_save: 'Save changes',
	editor_upload: '✓ Upload to Mealie',
	editor_uploading: 'Uploading…',
	editor_confirmReupload: (p: { date: string }) =>
		`This recipe was already uploaded on ${p.date}. Upload again? This creates another copy in Mealie.`,
	editor_mealieMissing: 'Please configure your Mealie API key first.',

	// Admin
	admin_pageTitle: 'Admin Panel - JarIt',
	admin_checking: 'Checking permissions…',
	admin_title: '🛡️ Admin Dashboard',
	admin_subtitle: 'Manage users and permissions',
	admin_newUser: '➕ New user',
	admin_totalUsers: 'Total users',
	admin_admins: 'Admins',
	admin_search: 'Search users…',
	admin_refresh: 'Refresh',
	admin_loadingUsers: 'Loading users…',
	admin_noUsers: 'No users found',
	admin_role_USER: 'User',
	admin_role_ADMIN: 'Admin',
	admin_createTitle: 'Create new user',
	admin_username: 'Username',
	admin_email: 'Email',
	admin_password: 'Password',
	admin_create: 'Create user',
	admin_creating: 'Creating…',
	admin_allFieldsRequired: 'All fields are required.',
	admin_created: (p: { name: string }) => `User "${p.name}" created.`,
	admin_deleted: (p: { name: string }) => `User "${p.name}" deleted.`,
	admin_confirmDelete: (p: { name: string }) => `Delete "${p.name}"?`,

	// Errors: generic by situation
	error_generic: 'Something went wrong. Please try again.',
	error_network: 'The server cannot be reached. Check your connection and try again.',
	error_401: 'Your session has expired. Please sign in again.',
	error_403: 'You are not allowed to do this.',
	error_404: 'Not found.',
	error_409: 'This is not possible right now.',
	error_422: 'Some input is invalid. Please check your entries.',
	error_5xx: 'The server ran into a problem. Please try again later.',

	// Errors: by server error code (contracts/http-api.md)
	error_INVALID_TOKEN: 'Your session has expired. Please sign in again.',
	error_USER_NOT_FOUND: 'User not found.',
	error_INVALID_CREDENTIALS: 'Incorrect username or password.',
	error_REGISTRATION_DISABLED:
		'Registration is disabled. Ask an administrator to create an account for you.',
	error_EMAIL_TAKEN: 'This email address is already registered.',
	error_USERNAME_TAKEN: 'This username is already taken.',
	error_ADMIN_REQUIRED: 'Only administrators can do this.',
	error_CANNOT_DELETE_SELF: 'You cannot delete your own account.',
	error_API_KEY_NOT_FOUND: 'No API key is configured for this service.',
	error_JOB_NOT_FOUND: 'This extraction does not exist.',
	error_JOB_NOT_EDITABLE: 'Only completed extractions can be edited.',
	error_JOB_NOT_UPLOADABLE: 'Only completed extractions can be uploaded.',
	error_JOB_NOT_RETRYABLE: 'Only failed extractions can be retried.',
	error_JOB_NOT_DELETABLE: 'Wait until the extraction has finished before deleting it.',
	error_MEALIE_NOT_CONFIGURED: 'Please configure your Mealie API key first.',
	error_MEALIE_URL_NOT_CONFIGURED: 'Please add the base URL of your Mealie instance.',
	error_MEALIE_CREDENTIALS_UNREADABLE:
		'Your stored Mealie credentials can no longer be read. Please enter your Mealie API key again.',
	error_MEALIE_ERROR: 'Mealie rejected the request. Check your Mealie settings and try again.',
	error_MEALIE_INVALID_CREDENTIALS: 'Your Mealie credentials are not valid.'
};

/** Shape every dictionary must have: same keys, strings stay strings, functions keep their parameters. */
export type Messages = {
	[K in keyof typeof en]: (typeof en)[K] extends (...args: infer A) => string
		? (...args: A) => string
		: string;
};
