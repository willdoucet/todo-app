import { useEffect, useRef, useState } from 'react'

import { useRecipeImport } from '../../hooks/useRecipeImport'
import { getImportErrorInfo } from '../../constants/importErrors'

/**
 * URL-import view inside the recipe modal. Four states:
 *   input   → URL text field + disabled/enabled Import button
 *   loading → step indicator (pulsing dots) + skeleton preview card
 *   preview → image-hero card with title/description/metadata + primary CTA
 *   error   → calm recoverable state, copy + buttons calibrated by error code
 *
 * Accessibility (per plan Pass 6):
 *   - URL input auto-focuses on mount (when switching to this tab)
 *   - Loading step label carries aria-live=polite
 *   - Error container carries role="alert"
 *   - Primary recovery button receives focus on state transition into
 *     preview or error states
 */
export default function RecipeUrlImport({
  initialUrl = '',
  onUseRecipe,
  onEnterManually,
  onAfterSubmit,
}) {
  const { status, step, recipe, errorCode, importFromUrl, reset } = useRecipeImport()
  const [url, setUrl] = useState(initialUrl)
  const [imageFailed, setImageFailed] = useState(false)

  const urlInputRef = useRef(null)
  const primaryButtonRef = useRef(null)
  const errorPrimaryRef = useRef(null)

  // When the caller updates `initialUrl` (e.g. paste-detect flow), accept it.
  useEffect(() => {
    if (initialUrl && initialUrl !== url) setUrl(initialUrl)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialUrl])

  // Auto-focus URL input on first mount when we're in the input state.
  useEffect(() => {
    if (status === 'idle' && urlInputRef.current) {
      urlInputRef.current.focus()
    }
  }, [status])

  // Focus management on state transitions into preview / error.
  useEffect(() => {
    if (status === 'complete' && primaryButtonRef.current) {
      primaryButtonRef.current.focus()
    } else if ((status === 'failed' || status === 'timeout' || status === 'unavailable') && errorPrimaryRef.current) {
      errorPrimaryRef.current.focus()
    }
  }, [status])

  // Reset broken-image state when a new recipe comes in.
  useEffect(() => {
    setImageFailed(false)
  }, [recipe?.recipe_detail?.image_url])

  // Notify parent when we leave the idle state (useful so parent can collapse
  // or annotate the view above us).
  useEffect(() => {
    if (status !== 'idle' && onAfterSubmit) onAfterSubmit(status)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  const canImport = /^https?:\/\//i.test(url.trim())

  const handleSubmit = (e) => {
    e?.preventDefault?.()
    if (!canImport || status === 'pending' || status === 'progress') return
    importFromUrl(url.trim())
  }

  const handleTryAgain = () => {
    reset()
    // Leave `url` in place so the user can tweak and resubmit without retyping.
    setTimeout(() => urlInputRef.current?.focus(), 0)
  }

  // ── Render by state ────────────────────────────────────────────────────

  if (status === 'pending' || status === 'progress') {
    return <LoadingState step={step} />
  }

  if (status === 'complete' && recipe) {
    return (
      <PreviewCard
        recipe={recipe}
        imageFailed={imageFailed}
        onImageError={() => setImageFailed(true)}
        primaryButtonRef={primaryButtonRef}
        onUseRecipe={() => onUseRecipe?.(recipe)}
        onTryAgain={handleTryAgain}
      />
    )
  }

  if (status === 'failed' || status === 'timeout' || status === 'unavailable') {
    return (
      <ErrorState
        errorCode={errorCode}
        isTimeout={status === 'timeout'}
        primaryRef={errorPrimaryRef}
        onTryAgain={handleTryAgain}
        onEnterManually={() => {
          reset()
          onEnterManually?.()
        }}
      />
    )
  }

  return (
    <InputState
      url={url}
      canImport={canImport}
      inputRef={urlInputRef}
      onUrlChange={setUrl}
      onSubmit={handleSubmit}
    />
  )
}

// ──────────────────────────────────────────────────────────────────────────
// States
// ──────────────────────────────────────────────────────────────────────────

function InputState({ url, canImport, inputRef, onUrlChange, onSubmit }) {
  // IMPORTANT: this view renders inside RecipeFormBody's outer <form>, so we
  // must NOT wrap in <form> here — nested form tags cause the Import button's
  // submit to bubble up to the outer form and kick off the manual-recipe
  // POST /items with an empty name, which closes/errors the modal. Instead,
  // submit via explicit button onClick + Enter key handler on the input.
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      // Prevent the outer form from catching Enter as a submit.
      e.preventDefault()
      e.stopPropagation()
      if (canImport) onSubmit(e)
    }
  }
  const handleClick = (e) => {
    // Belt-and-suspenders: even though this is type="button", make sure no
    // synthetic submit escapes to the outer form.
    e.preventDefault()
    e.stopPropagation()
    onSubmit(e)
  }

  return (
    <div className="space-y-3" aria-label="Import recipe from URL">
      <label className="block">
        <span className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
          Paste a recipe URL
        </span>
        <input
          ref={inputRef}
          type="url"
          value={url}
          onChange={(e) => onUrlChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="https://www.allrecipes.com/recipe/..."
          className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
          autoComplete="off"
          spellCheck={false}
        />
        <span className="block text-xs text-text-muted dark:text-gray-500 mt-1">
          We&rsquo;ll extract ingredients, instructions, and times automatically.
        </span>
      </label>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleClick}
          disabled={!canImport}
          className="px-5 py-2.5 rounded-lg bg-terracotta-500 hover:bg-terracotta-600 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-600 dark:hover:bg-blue-700"
        >
          Import
        </button>
      </div>
    </div>
  )
}

function LoadingState({ step }) {
  const stepLabel = STEP_LABELS[step] || 'Working…'
  const stepIndex = STEP_ORDER.indexOf(step)

  return (
    <div className="space-y-4" aria-busy="true">
      {/* Step indicator */}
      <div className="flex flex-col items-center gap-2">
        <p
          className="text-base font-medium text-text-primary dark:text-gray-100"
          aria-live="polite"
          aria-atomic="true"
        >
          {stepLabel}
        </p>
        <div className="flex gap-1.5" aria-hidden="true">
          {STEP_ORDER.slice(0, 3).map((s, i) => (
            <span
              key={s}
              className={`
                w-2 h-2 rounded-full transition-colors
                ${i < stepIndex
                  ? 'bg-terracotta-500 dark:bg-blue-500'
                  : i === stepIndex
                    ? 'bg-terracotta-500 dark:bg-blue-500 animate-pulse'
                    : 'bg-warm-sand dark:bg-gray-600'}
              `}
            />
          ))}
        </div>
      </div>

      {/* Skeleton preview card */}
      <div
        className="bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-xl overflow-hidden"
        aria-hidden="true"
      >
        <div className="h-48 bg-warm-sand dark:bg-gray-700 animate-pulse" />
        <div className="p-4 space-y-2">
          <div className="h-5 w-3/4 bg-warm-sand dark:bg-gray-700 rounded animate-pulse" />
          <div className="h-4 w-full bg-warm-sand dark:bg-gray-700 rounded animate-pulse" />
          <div className="h-4 w-1/2 bg-warm-sand dark:bg-gray-700 rounded animate-pulse" />
        </div>
      </div>
    </div>
  )
}

function PreviewCard({ recipe, imageFailed, onImageError, primaryButtonRef, onUseRecipe, onTryAgain }) {
  const rd = recipe.recipe_detail || {}
  const ingredientCount = rd.ingredients?.length || 0
  const totalTime = (rd.prep_time_minutes || 0) + (rd.cook_time_minutes || 0)
  const tags = (recipe.tags || []).slice(0, 5)
  const showImage = rd.image_url && !imageFailed

  return (
    <div className="bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-xl overflow-hidden shadow-sm">
      {/* Hero image or emoji fallback */}
      {showImage ? (
        <img
          src={rd.image_url}
          alt=""
          onError={onImageError}
          className="w-full aspect-video object-cover bg-warm-sand dark:bg-gray-700"
        />
      ) : (
        <div
          className="w-full aspect-video bg-warm-sand dark:bg-gray-700 flex items-center justify-center"
          aria-hidden="true"
        >
          <span className="text-5xl">🍽️</span>
        </div>
      )}

      <div className="p-4 space-y-2">
        <h3
          className="text-xl font-semibold text-text-primary dark:text-gray-100 line-clamp-2"
          title={recipe.name}
        >
          {recipe.name}
        </h3>

        {rd.description && (
          <p className="text-sm text-text-secondary dark:text-gray-400 truncate">
            {rd.description}
          </p>
        )}

        <div className="text-xs text-text-muted dark:text-gray-500 flex gap-2 flex-wrap">
          {totalTime > 0 && <span>⏱ {totalTime} min</span>}
          {rd.servings && <span>· 👥 {rd.servings} serving{rd.servings === 1 ? '' : 's'}</span>}
          {ingredientCount > 0 && <span>· 🥕 {ingredientCount} ingredient{ingredientCount === 1 ? '' : 's'}</span>}
        </div>

        {tags.length > 0 && (
          <div className="flex gap-1.5 flex-wrap pt-1">
            {tags.map((t) => (
              <span
                key={t}
                className="rounded-full bg-peach-100 text-terracotta-700 dark:bg-orange-900/30 dark:text-orange-400 px-2 py-0.5 text-xs font-medium"
              >
                {t}
              </span>
            ))}
          </div>
        )}

        {/* Action row: stacked on <sm (primary on top for thumb reach), horizontal on sm+ */}
        <div className="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end pt-3">
          <button
            type="button"
            onClick={onTryAgain}
            className="px-4 py-2.5 rounded-lg bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-600 font-medium transition-colors"
          >
            Try Again
          </button>
          <button
            ref={primaryButtonRef}
            type="button"
            onClick={onUseRecipe}
            className="px-4 py-2.5 rounded-lg bg-terracotta-500 hover:bg-terracotta-600 text-white font-medium transition-colors dark:bg-blue-600 dark:hover:bg-blue-700"
          >
            Use This Recipe
          </button>
        </div>
      </div>
    </div>
  )
}

function ErrorState({ errorCode, isTimeout, primaryRef, onTryAgain, onEnterManually }) {
  const info = isTimeout
    ? { message: 'Import timed out. Try again?', retryable: true }
    : getImportErrorInfo(errorCode)

  return (
    <div className="space-y-4 text-center" role="alert">
      <div
        className="w-10 h-10 rounded-full bg-terracotta-100 dark:bg-red-900/30 text-terracotta-600 dark:text-red-400 flex items-center justify-center mx-auto"
        aria-hidden="true"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>

      <p className="text-base text-text-primary dark:text-gray-100 px-4">
        {info.message}
      </p>

      <div className="flex gap-2 justify-center pt-2">
        {info.retryable ? (
          <>
            <button
              ref={primaryRef}
              type="button"
              onClick={onTryAgain}
              className="px-4 py-2.5 rounded-lg bg-terracotta-500 hover:bg-terracotta-600 text-white font-medium transition-colors dark:bg-blue-600 dark:hover:bg-blue-700"
            >
              Try Again
            </button>
            <button
              type="button"
              onClick={onEnterManually}
              className="px-4 py-2.5 rounded-lg bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-600 font-medium transition-colors"
            >
              Enter Manually
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              onClick={onTryAgain}
              className="px-4 py-2.5 rounded-lg bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-600 font-medium transition-colors"
            >
              Try Again
            </button>
            <button
              ref={primaryRef}
              type="button"
              onClick={onEnterManually}
              className="px-4 py-2.5 rounded-lg bg-terracotta-500 hover:bg-terracotta-600 text-white font-medium transition-colors dark:bg-blue-600 dark:hover:bg-blue-700"
            >
              Enter Manually
            </button>
          </>
        )}
      </div>
    </div>
  )
}

const STEP_LABELS = {
  queued: 'Queued…',
  fetching_page: 'Fetching page…',
  cleaning_html: 'Cleaning up page…',
  extracting_recipe: 'Extracting recipe…',
  parsing_ingredients: 'Parsing ingredients…',
}

const STEP_ORDER = ['fetching_page', 'extracting_recipe', 'parsing_ingredients']
