export function highlightHtml(html, search) {
  if (!search) {
    return html
  }
  const escaped = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const rgx = new RegExp(`(${escaped})(?![^<>]*>)`, 'gi')
  return html.replace(rgx, (match) => `<b style="color:black;background-color:#ffff66">${match}</b>`)
}
