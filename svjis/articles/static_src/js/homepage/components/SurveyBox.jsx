import { useState } from 'react'
import { apiFetch } from '../../api.js'

function SurveyOptionBar({ option, isSelectable, selectedOption, onSelect }) {
  return (
    <p className="survey-option">
      <span className="survey-option__row">
        {isSelectable ? (
          <>
            <input
              type="radio"
              id={`vote-${option.id}`}
              name="survey-option"
              checked={selectedOption === option.id}
              onChange={() => onSelect(option.id)}
            />
            <label htmlFor={`vote-${option.id}`}>{option.description}</label>
          </>
        ) : (
          <span>{option.description}</span>
        )}
        <em>{option.pct.toFixed(1)}%</em>
      </span>
      <span className="survey-bar">
        <span
          className={`survey-bar__fill${option.is_winning ? ' survey-bar__fill--winning' : ''}`}
          style={{ width: `${Math.round(option.pct)}%` }}
        />
      </span>
    </p>
  )
}

function Survey({ survey, onVoted }) {
  const [selectedOption, setSelectedOption] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const canVote = survey.is_open_for_voting && survey.user_can_vote

  function handleSubmit(e) {
    e.preventDefault()
    if (!selectedOption) return
    setSubmitting(true)
    setError(null)
    apiFetch(`surveys/${survey.id}/vote/`, {
      method: 'POST',
      body: JSON.stringify({ option: selectedOption }),
    })
      .then((updated) => onVoted(updated))
      .catch(() => setError('Hlasování se nezdařilo.'))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="box2">
      <div className="box2_header">Anketa</div>
      <div className="box2_content">
        <div className="survey_box">
          <strong dangerouslySetInnerHTML={{ __html: survey.description }} />
          {canVote ? (
            <form onSubmit={handleSubmit}>
              {survey.options.map((option) => (
                <SurveyOptionBar
                  key={option.id}
                  option={option}
                  isSelectable
                  selectedOption={selectedOption}
                  onSelect={setSelectedOption}
                />
              ))}
              <p>
                <input type="submit" value="Hlasovat" disabled={!selectedOption || submitting} />
              </p>
              {error && <p className="alert alert-error">{error}</p>}
            </form>
          ) : (
            survey.options.map((option) => <SurveyOptionBar key={option.id} option={option} isSelectable={false} />)
          )}
          <p>Počet hlasů: {survey.total_votes}</p>
        </div>
      </div>
    </div>
  )
}

export default function SurveyBox({ surveys, onSurveyUpdated }) {
  if (!surveys || surveys.length === 0) {
    return null
  }

  return surveys.map((survey) => <Survey key={survey.id} survey={survey} onVoted={onSurveyUpdated} />)
}
