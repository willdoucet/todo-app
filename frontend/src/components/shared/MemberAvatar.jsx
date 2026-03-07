const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const sizeClasses = {
  xs: 'w-5 h-5 text-[10px]',
  sm: 'w-6 h-6 text-xs',
  md: 'w-8 h-8 text-sm',
  lg: 'w-10 h-10 text-base',
  xl: 'w-16 h-16 text-xl',
}

export default function MemberAvatar({ name, photoUrl, color, size = 'md', className = '', title }) {
  const initial = (name || '?').charAt(0).toUpperCase()
  const sizeClass = sizeClasses[size] || sizeClasses.md
  const dimensions = sizeClass.split(' ').slice(0, 2).join(' ')

  if (photoUrl) {
    const imageSrc = photoUrl.startsWith('http') ? photoUrl : `${API_BASE}${photoUrl}`
    return (
      <img
        src={imageSrc}
        alt={name}
        title={title}
        className={`${dimensions} rounded-full object-cover ${className}`}
      />
    )
  }

  return (
    <div
      className={`flex items-center justify-center rounded-full ${sizeClass} ${className}`}
      style={{ backgroundColor: color || '#9ca3af' }}
      title={title}
    >
      <span className="font-semibold text-white drop-shadow-sm">{initial}</span>
    </div>
  )
}
