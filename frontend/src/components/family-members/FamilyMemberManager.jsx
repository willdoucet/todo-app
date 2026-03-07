import { useState, useEffect } from 'react'
import axios from 'axios'
import PhotoUpload from '../shared/PhotoUpload'
import MemberAvatar from '../shared/MemberAvatar'
import ColorPicker from '../shared/ColorPicker'
import { getFirstUnusedColor } from '../../constants/familyColors'

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
  const [editingColor, setEditingColor] = useState('')
  const [newMemberColor, setNewMemberColor] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Auto-select first unused color when family members change
  useEffect(() => {
    const existingColors = familyMembers.map(m => m.color).filter(Boolean)
    setNewMemberColor(getFirstUnusedColor(existingColors))
  }, [familyMembers])

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
        color: newMemberColor,
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
    setEditingColor(member.color || null)
  }

  // Cancel editing
  const cancelEdit = () => {
    setEditingId(null)
    setEditingName('')
    setEditingPhotoUrl(null)
    setEditingColor('')
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
        color: editingColor,
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

  // Colors used by non-system members, excluding a given member ID
  const colorsUsedByOthers = (excludeId) =>
    editableMembers
      .filter(m => m.id !== excludeId)
      .map(m => m.color)
      .filter(Boolean)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-terracotta-500 dark:border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto">
      <h2 className="text-xl font-semibold text-text-primary dark:text-gray-100 mb-6">
        Family Members
      </h2>

      {/* Error message */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Add new member form */}
      <div className="mb-6 bg-warm-beige dark:bg-gray-800/50 rounded-xl border border-card-border dark:border-gray-700 p-4">
        <form onSubmit={handleCreate}>
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
                  flex-1 px-4 py-2.5 border border-card-border dark:border-gray-600
                  rounded-lg bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
                  focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
                  outline-none transition text-sm
                  placeholder:text-text-muted dark:placeholder:text-gray-500
                "
              />
              <button
                type="submit"
                disabled={isSubmitting || !newMemberName.trim()}
                className="
                  px-4 py-2.5 bg-terracotta-500 text-white font-medium rounded-lg
                  hover:bg-terracotta-600 transition-colors duration-200
                  disabled:opacity-50 disabled:cursor-not-allowed
                  text-sm
                "
              >
                Add
              </button>
            </div>
          </div>
          <div className="pl-[76px] mt-2">
            <ColorPicker selectedColor={newMemberColor} onSelect={setNewMemberColor} disabledColors={colorsUsedByOthers(null)} />
          </div>
        </form>
      </div>

      {/* System members (Everyone) - shown but not editable */}
      {systemMembers.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-label-green dark:text-gray-400 uppercase tracking-wide mb-2">
            System
          </p>
          {systemMembers.map(member => (
            <div
              key={member.id}
              className="flex items-center gap-3 p-3 bg-warm-beige dark:bg-gray-800/50 rounded-lg"
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-warm-sand dark:bg-gray-700">
                <svg className="w-4 h-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <span className="text-text-secondary dark:text-gray-400 text-sm">
                {member.name}
              </span>
              <span className="ml-auto text-xs text-text-muted dark:text-gray-500">
                (cannot be modified)
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Editable members list */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-label-green dark:text-gray-400 uppercase tracking-wide mb-2">
          Family Members
        </p>
        {editableMembers.length === 0 ? (
          <p className="text-text-muted dark:text-gray-400 text-sm py-4 text-center">
            No family members yet. Add one above!
          </p>
        ) : (
          editableMembers.map(member => (
            <div
              key={member.id}
              className="flex items-center gap-3 p-3 bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-lg"
              style={{ borderLeftWidth: '10px', borderLeftColor: editingId === member.id ? (editingColor || '#9ca3af') : (member.color || '#9ca3af') }}
            >
              {editingId === member.id ? (
                // Edit mode
                <div className="flex flex-col gap-2 w-full">
                  <div className="flex items-center gap-3">
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
                        flex-1 px-3 py-1.5 border border-card-border dark:border-gray-600
                        rounded bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
                        focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
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
                      className="px-3 py-1.5 text-sm text-sage-600 dark:text-green-400 hover:bg-sage-50 dark:hover:bg-green-900/20 rounded transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="px-3 py-1.5 text-sm text-text-secondary dark:text-gray-400 hover:bg-warm-beige dark:hover:bg-gray-700 rounded transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                  <div className="pl-[76px]">
                    <ColorPicker selectedColor={editingColor} onSelect={setEditingColor} disabledColors={colorsUsedByOthers(member.id)} />
                  </div>
                </div>
              ) : (
                // View mode
                <>
                  <MemberAvatar name={member.name} photoUrl={member.photo_url} color={member.color} />
                  <span className="flex-1 text-text-primary dark:text-gray-100 text-sm">
                    {member.name}
                  </span>
                  <button
                    onClick={() => startEdit(member)}
                    className="px-3 py-1.5 text-sm text-terracotta-600 dark:text-blue-400 hover:bg-terracotta-50 dark:hover:bg-blue-900/20 rounded transition-colors"
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