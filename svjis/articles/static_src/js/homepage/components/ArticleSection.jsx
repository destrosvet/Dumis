import { useEffect, useState } from 'react'
import { apiFetch } from '../../api.js'
import ArticleCard from './ArticleCard.jsx'
import Paginator from './Paginator.jsx'

function getInitialSearch() {
  return new URLSearchParams(window.location.search).get('search') || ''
}

function buildInitialUrl(menuId, search) {
  const params = new URLSearchParams()
  if (menuId) params.set('menu', menuId)
  if (search) params.set('search', search)
  const query = params.toString()
  return `/api/v1/articles/${query ? `?${query}` : ''}`
}

export default function ArticleSection({ menuId }) {
  const [search] = useState(getInitialSearch)
  const [url, setUrl] = useState(() => buildInitialUrl(menuId, search))
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    apiFetch(url)
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [url])

  const header = search ? `Výsledky hledání: ${search}` : 'Nejnovější články'

  return (
    <section className="main-content">
      <h1 className="article-page-title">{header}</h1>

      {error && <p className="alert alert-error">Nepodařilo se načíst články.</p>}
      {!error && !data && <p>Načítání…</p>}
      {data && data.results.map((article) => <ArticleCard key={article.id} article={article} search={search} />)}

      {data && (
        <Paginator
          hasPrevious={Boolean(data.previous)}
          hasNext={Boolean(data.next)}
          onPrevious={() => setUrl(data.previous)}
          onNext={() => setUrl(data.next)}
        />
      )}
    </section>
  )
}
