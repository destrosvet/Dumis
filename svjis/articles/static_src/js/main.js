import Alpine from 'alpinejs'
import htmx from 'htmx.org'

// ==========================================================================
// Alpine.js — lightweight reactivity for interactive components
// ==========================================================================
window.Alpine = Alpine
Alpine.start()

// ==========================================================================
// HTMX — AJAX without writing JavaScript
// ==========================================================================
window.htmx = htmx

// ==========================================================================
// Mobile sidebar toggle (Alpine.js handles most, but this is a fallback)
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  const sidebarToggle = document.querySelector('[data-sidebar-toggle]')
  const sidebar = document.querySelector('[data-sidebar]')
  const sidebarOverlay = document.querySelector('[data-sidebar-overlay]')

  if (sidebarToggle && sidebar) {
    const toggleSidebar = () => {
      sidebar.classList.toggle('translate-x-0')
      sidebar.classList.toggle('-translate-x-full')
      if (sidebarOverlay) {
        sidebarOverlay.classList.toggle('hidden')
      }
    }

    sidebarToggle.addEventListener('click', toggleSidebar)
    if (sidebarOverlay) {
      sidebarOverlay.addEventListener('click', toggleSidebar)
    }
  }
})

// ==========================================================================
// Auto-dismiss alerts after 5 seconds
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('[data-auto-dismiss]')
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s ease-out'
      alert.style.opacity = '0'
      setTimeout(() => alert.remove(), 500)
    }, 5000)
  })
})
