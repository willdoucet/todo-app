import { useState, useRef } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Recipe image upload sub-component for RecipeFormModal.
 * States: no image (upload area) → uploading (spinner) → preview (change/remove).
 * Error: inline banner for too-large or invalid type.
 */
export default function RecipeImageUpload({ imageUrl, onImageChange }) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef(null)

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setUploading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await axios.post(`${API_BASE}/upload/recipe-image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      onImageChange(res.data.url)
    } catch (err) {
      const status = err.response?.status
      if (status === 413) {
        setError('File too large (max 5MB)')
      } else if (status === 400) {
        setError('Invalid file type — use JPG/PNG/GIF/WebP')
      } else {
        setError('Upload failed — check your connection')
      }
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleRemove = () => {
    setError(null)
    onImageChange(null)
  }

  return (
    <div>
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        className="hidden"
        onChange={handleFileSelect}
      />

      {imageUrl ? (
        <div>
          <div className="relative aspect-video rounded-lg overflow-hidden border border-card-border dark:border-gray-600">
            <img
              src={imageUrl.startsWith('http') ? imageUrl : `${API_BASE}${imageUrl}`}
              alt="Recipe preview"
              className="w-full h-full object-cover"
            />
          </div>
          <div className="flex gap-2 mt-2">
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="px-3 py-1.5 text-xs font-medium bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 rounded-lg hover:bg-warm-beige dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
            >
              Change
            </button>
            <button
              type="button"
              onClick={handleRemove}
              className="px-3 py-1.5 text-xs font-medium text-text-muted dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="
            w-full flex flex-col items-center justify-center gap-2 py-6
            border-2 border-dashed border-card-border dark:border-gray-600
            rounded-lg text-text-muted dark:text-gray-500
            hover:border-terracotta-500 dark:hover:border-blue-500
            hover:text-terracotta-500 dark:hover:text-blue-400
            transition-colors disabled:opacity-50
          "
        >
          {uploading ? (
            <>
              <div className="w-5 h-5 border-2 border-terracotta-500 dark:border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs">Uploading...</span>
            </>
          ) : (
            <>
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
              </svg>
              <span className="text-xs font-medium">Upload image</span>
            </>
          )}
        </button>
      )}

      {error && (
        <div className="mt-2 px-3 py-2 text-xs rounded-lg bg-terracotta-50 dark:bg-red-900/20 border border-terracotta-200 dark:border-red-800 text-terracotta-700 dark:text-red-400">
          {error}
        </div>
      )}
    </div>
  )
}
