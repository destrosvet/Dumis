export default function NewsBox({ items }) {
  if (!items || items.length === 0) {
    return null
  }

  return (
    <div className="box1">
      <div className="box1_header">Novinky</div>
      <div className="box1_content">
        {items.map((news) => {
          const date = new Date(news.created_date)
          return (
            <dl className="news_box" key={news.id}>
              <dt>
                {date.toLocaleDateString('cs-CZ', { month: 'short' }).toUpperCase()}
                <br />
                <span>{date.toLocaleDateString('cs-CZ', { day: '2-digit' })}</span>
              </dt>
              <dd>
                <span>
                  @ {date.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })}
                </span>
                <br />
                <span dangerouslySetInnerHTML={{ __html: news.body }} />
              </dd>
            </dl>
          )
        })}
      </div>
    </div>
  )
}
