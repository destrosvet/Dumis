import { createRoot } from 'react-dom/client'
import Homepage from './Homepage.jsx'

const root = document.getElementById('homepage-root')
if (root) {
  const menuId = root.dataset.initialMenu || null
  createRoot(root).render(<Homepage initialMenuId={menuId} />)
}
