import { highlightHtml } from '../highlight.js'

export default function ArticleCard({ article, search }) {
  const detailUrl = search ? `/article/${article.slug}/?search=${encodeURIComponent(search)}` : `/article/${article.slug}/`

  return (
    <div className="article-box">
      {article.cover_image && (
        <a className="article-thumb" href={detailUrl}>
          <img src={article.cover_image} alt="" />
        </a>
      )}
      <div className="article-desc">
        <h1 className="article-title-list">
          <a href={detailUrl} dangerouslySetInnerHTML={{ __html: highlightHtml(article.header, search) }} />
        </h1>
        <p className="info">
          <a href={`/main/${article.menu.id}/`}>{article.menu.description}</a>:{' '}
          <strong>
            {new Date(article.published_date).toLocaleDateString('cs-CZ', {
              day: '2-digit',
              month: '2-digit',
              year: 'numeric',
            })}
          </strong>
          , Autor:{' '}
          <strong>
            {article.author.first_name}&nbsp;{article.author.last_name}
          </strong>
          {article.comments_count > 0 && (
            <>
              &nbsp;
              <a className="comments" href={`${detailUrl}#comments`}>
                <svg aria-hidden="true" viewBox="0 0 16 16" height="12" width="12" fill="currentColor" style={{ verticalAlign: 'middle' }}>
                  <path d="M1 2.75C1 1.784 1.784 1 2.75 1h10.5c.966 0 1.75.784 1.75 1.75v7.5A1.75 1.75 0 0 1 13.25 12H9.06l-2.573 2.573A1.458 1.458 0 0 1 4 13.543V12H2.75A1.75 1.75 0 0 1 1 10.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h2a.75.75 0 0 1 .75.75v2.19l2.72-2.72a.749.749 0 0 1 .53-.22h4.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z" />
                </svg>
                <strong>{article.comments_count}</strong>
              </a>
            </>
          )}
        </p>
        <p dangerouslySetInnerHTML={{ __html: highlightHtml(article.perex, search) }} />
      </div>
    </div>
  )
}
