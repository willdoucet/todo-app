/**
 * Frontend counterpart to backend/app/constants/import_errors.py.
 *
 * Every error_code returned by the import-status endpoint maps here. A
 * backend parity test (tests/unit/test_import_errors.py) ensures this map
 * never silently drifts — new backend codes without a frontend entry are
 * caught in CI.
 *
 * Shape:
 *   { message: string, retryable: boolean }
 *
 * Retryable codes surface "Try Again" as the primary recovery button;
 * non-retryable codes make "Enter Manually" the primary button instead.
 */
export const IMPORT_ERROR_MESSAGES = {
  unknown_or_expired_task: {
    message: 'Import not found. Please try again.',
    retryable: true,
  },
  invalid_url: {
    message: 'Please enter a valid URL.',
    retryable: true,
  },
  ssrf_blocked: {
    message: 'This URL cannot be imported.',
    retryable: false,
  },
  broker_unavailable: {
    message: 'Service temporarily unavailable. Try again in a moment.',
    retryable: true,
  },
  fetch_failed: {
    message: "Couldn't reach that website. Try again?",
    retryable: true,
  },
  fetch_timeout: {
    message: 'Website took too long to respond. Try again?',
    retryable: true,
  },
  fetch_blocked: {
    message: 'Website blocked our request. Enter the recipe manually.',
    retryable: false,
  },
  fetch_not_found: {
    message: 'Page not found. Check the URL or enter the recipe manually.',
    retryable: false,
  },
  fetch_too_large: {
    message: 'Page too large to process. Enter the recipe manually.',
    retryable: false,
  },
  not_html: {
    message: 'Not a recipe page. Enter the recipe manually.',
    retryable: false,
  },
  llm_unavailable: {
    message: 'AI service unavailable. Try again in a moment.',
    retryable: true,
  },
  llm_auth: {
    message: 'AI service is misconfigured. Enter the recipe manually.',
    retryable: false,
  },
  llm_rate_limited: {
    message: 'Try again in a moment.',
    retryable: true,
  },
  llm_refused: {
    message: "Couldn't extract a recipe from this page.",
    retryable: false,
  },
  not_recipe: {
    message: "Couldn't extract a recipe from this page.",
    retryable: false,
  },
  task_timeout: {
    message: 'Import timed out. Try again?',
    retryable: true,
  },
  internal_error: {
    message: 'Something went wrong. Try again?',
    retryable: true,
  },
}

const GENERIC_FALLBACK = {
  message: 'Something went wrong. Try again?',
  retryable: true,
}

export function getImportErrorInfo(errorCode) {
  if (!errorCode) return GENERIC_FALLBACK
  return IMPORT_ERROR_MESSAGES[errorCode] || GENERIC_FALLBACK
}
