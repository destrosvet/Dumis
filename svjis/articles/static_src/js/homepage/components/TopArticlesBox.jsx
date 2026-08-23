export default function TopArticlesBox({ items }) {
  if (!items || items.length === 0) {
    return null
  }

  return (
    <div className="box2">
      <div className="box2_header">Nejčtenější články</div>
      <div className="box2_content">
        <ul id="top_articles">
          {items.map((item) => (
            <li key={item.article.id}>
              <span className="top_articles_times">{item.total}&times;</span>
              <a href={`/article/${item.article.slug}/`}>{item.article.header}</a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
