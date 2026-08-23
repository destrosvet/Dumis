export default function Paginator({ hasPrevious, hasNext, onPrevious, onNext }) {
  if (!hasPrevious && !hasNext) {
    return null
  }

  function handleClick(e, callback) {
    e.preventDefault()
    callback()
  }

  return (
    <nav className="paginator">
      {hasPrevious && (
        <a href="#" onClick={(e) => handleClick(e, onPrevious)}>
          Předchozí
        </a>
      )}
      {hasPrevious && hasNext && ' '}
      {hasNext && (
        <a href="#" onClick={(e) => handleClick(e, onNext)}>
          Další
        </a>
      )}
    </nav>
  )
}
