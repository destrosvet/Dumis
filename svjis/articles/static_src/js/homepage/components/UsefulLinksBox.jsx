const ATTACH_ICON_PATH =
  'm21.44 11.05-9.19 9.19a6 6 0 0 1-8.48-8.48l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48'

export default function UsefulLinksBox({ items }) {
  if (!items || items.length === 0) {
    return null
  }

  return (
    <div className="box1">
      <div className="box1_header">Užitečné odkazy</div>
      <div className="box1_content">
        <ul className="usefullinks">
          {items.map((link) => (
            <li key={link.id}>
              <span className="icon-static" title={link.header}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d={ATTACH_ICON_PATH} />
                </svg>
              </span>
              <a href={link.link}>{link.header}</a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
