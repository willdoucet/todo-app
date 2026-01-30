import { useState, useEffect } from 'react'
import axios from 'axios'
import PhotoUpload from './PhotoUpload'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function FamilyMemberManager() {
  const [familyMembers, setFamilyMembers] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newMemberName, setNewMemberName] = useState('')
  const [newMemberPhotoUrl, setNewMemberPhotoUrl] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editingName, setEditingName] = useState('')
  const [editingPhotoUrl, setEditingPhotoUrl] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Fetch family members
  useEffect(() => {
    loadFamilyMembers()
  }, [])

  const loadFamilyMembers = async () => {
    try {
      setIsLoading(true)
      const response = await axios.get(`${API_BASE}/family-members`)
      setFamilyMembers(response.data)
      setError(null)
    } catch (err) {
      console.error('Error loading family members:', err)
      setError('Failed to load family members')
    } finally {
      setIsLoading(false)
    }
  }

  // Create new family member
  const handleCreate = async (e) => {
    e.preventDefault()
    if (!newMemberName.trim()) return

    setIsSubmitting(true)
    setError(null)
    try {
      const response = await axios.post(`${API_BASE}/family-members`, {
        name: newMemberName.trim(),
        photo_url: newMemberPhotoUrl,
      })
      setFamilyMembers([...familyMembers, response.data])
      setNewMemberName('')
      setNewMemberPhotoUrl(null)
    } catch (err) {
      console.error('Error creating family member:', err)
      setError(err.response?.data?.detail || 'Failed to create family member')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Start editing
  const startEdit = (member) => {
    setEditingId(member.id)
    setEditingName(member.name)
    setEditingPhotoUrl(member.photo_url)
  }

  // Cancel editing
  const cancelEdit = () => {
    setEditingId(null)
    setEditingName('')
    setEditingPhotoUrl(null)
  }

  // Save edit
  const handleUpdate = async (id) => {
    if (!editingName.trim()) return

    setIsSubmitting(true)
    setError(null)
    try {
      const response = await axios.patch(`${API_BASE}/family-members/${id}`, {
        name: editingName.trim(),
        photo_url: editingPhotoUrl,
      })
      setFamilyMembers(familyMembers.map(m => 
        m.id === id ? response.data : m
      ))
      setEditingId(null)
      setEditingName('')
      setEditingPhotoUrl(null)
    } catch (err) {
      console.error('Error updating family member:', err)
      setError(err.response?.data?.detail || 'Failed to update family member')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Delete family member
  const handleDelete = async (id, name) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return

    setError(null)
    try {
      await axios.delete(`${API_BASE}/family-members/${id}`)
      setFamilyMembers(familyMembers.filter(m => m.id !== id))
    } catch (err) {
      console.error('Error deleting family member:', err)
      setError(err.response?.data?.detail || 'Failed to delete family member')
    }
  }

  // Filter out system members for display (Everyone can't be edited/deleted)
  const editableMembers = familyMembers.filter(m => !m.is_system)
  const systemMembers = familyMembers.filter(m => m.is_system)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
        Family Members
      </h2>

      {/* Error message */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Add new member form */}
      <form onSubmit={handleCreate} className="mb-6">
        <div className="flex gap-3 items-start">
          <PhotoUpload
            currentUrl={newMemberPhotoUrl}
            onUpload={(url) => setNewMemberPhotoUrl(url)}
            uploadEndpoint="/upload/family-photo"
            placeholder="Photo"
            size="sm"
          />
          <div className="flex-1 flex gap-2">
            <input
              type="text"
              value={newMemberName}
              onChange={(e) => setNewMemberName(e.target.value)}
              placeholder="Add family member..."
              className="
                flex-1 px-4 py-2.5 border border-gray-300 dark:border-gray-600 
                rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                outline-none transition text-sm
                placeholder:text-gray-400 dark:placeholder:text-gray-500
              "
            />
            <button
              type="submit"
              disabled={isSubmitting || !newMemberName.trim()}
              className="
                px-4 py-2.5 bg-blue-600 text-white font-medium rounded-lg
                hover:bg-blue-700 transition-colors duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
                text-sm
              "
            >
              Add
            </button>
          </div>
        </div>
      </form>

      {/* System members (Everyone) - shown but not editable */}
      {systemMembers.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            System
          </p>
          {systemMembers.map(member => (
            <div
              key={member.id}
              className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700">
                <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <span className="text-gray-600 dark:text-gray-400 text-sm">
                {member.name}
              </span>
              <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">
                (cannot be modified)
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Editable members list */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
          Family Members
        </p>
        {editableMembers.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 text-sm py-4 text-center">
            No family members yet. Add one above!
          </p>
        ) : (
          editableMembers.map(member => (
            <div
              key={member.id}
              className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
            >
              {editingId === member.id ? (
                // Edit mode
                <>
                  <PhotoUpload
                    currentUrl={editingPhotoUrl}
                    onUpload={(url) => setEditingPhotoUrl(url)}
                    uploadEndpoint="/upload/family-photo"
                    placeholder="Photo"
                    size="sm"
                  />
                  <input
                    type="text"
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    className="
                      flex-1 px-3 py-1.5 border border-gray-300 dark:border-gray-600 
                      rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                      focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                      outline-none text-sm
                    "
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleUpdate(member.id)
                      if (e.key === 'Escape') cancelEdit()
                    }}
                  />
                  <button
                    onClick={() => handleUpdate(member.id)}
                    disabled={isSubmitting}
                    className="px-3 py-1.5 text-sm text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
                  >
                    Save
                  </button>
                  <button
                    onClick={cancelEdit}
                    className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                // View mode
                <>
                  <MemberAvatar name={member.name} photoUrl={member.photo_url} />
                  <span className="flex-1 text-gray-900 dark:text-gray-100 text-sm">
                    {member.name}
                  </span>
                  <button
                    onClick={() => startEdit(member)}
                    className="px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(member.id, member.name)}
                    className="px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                  >
                    Delete
                  </button>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// Avatar component that shows photo if available, otherwise shows initial
function MemberAvatar({ name, photoUrl }) {
  const initial = name.charAt(0).toUpperCase()
  const colors = [
    { bg: 'bg-blue-100 dark:bg-blue-900/40', text: 'text-blue-600 dark:text-blue-400' },
    { bg: 'bg-pink-100 dark:bg-pink-900/40', text: 'text-pink-600 dark:text-pink-400' },
    { bg: 'bg-green-100 dark:bg-green-900/40', text: 'text-green-600 dark:text-green-400' },
    { bg: 'bg-purple-100 dark:bg-purple-900/40', text: 'text-purple-600 dark:text-purple-400' },
    { bg: 'bg-orange-100 dark:bg-orange-900/40', text: 'text-orange-600 dark:text-orange-400' },
  ]
  const colorIndex = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % colors.length
  const color = colors[colorIndex]

  // If there's a photo URL, show the image
  if (photoUrl) {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const imageSrc = photoUrl.startsWith('http') ? photoUrl : `${API_BASE}${photoUrl}`
    return (
      <img
        src={imageSrc}
        alt={name}
        className="w-8 h-8 rounded-full object-cover"
      />
    )
  }

  // Otherwise show the initial
  return (
    <div className={`flex items-center justify-center w-8 h-8 rounded-full ${color.bg}`}>
      <span className={`text-sm font-semibold ${color.text}`}>{initial}</span>
    </div>
  )
}