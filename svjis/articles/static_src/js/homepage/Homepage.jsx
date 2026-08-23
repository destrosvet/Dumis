import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'
import ArticleSection from './components/ArticleSection.jsx'
import NewsBox from './components/NewsBox.jsx'
import SurveyBox from './components/SurveyBox.jsx'
import UsefulLinksBox from './components/UsefulLinksBox.jsx'
import TopArticlesBox from './components/TopArticlesBox.jsx'

export default function Homepage({ initialMenuId }) {
  const [news, setNews] = useState([])
  const [surveys, setSurveys] = useState([])
  const [usefulLinks, setUsefulLinks] = useState([])
  const [topArticles, setTopArticles] = useState([])

  useEffect(() => {
    apiFetch('news/').then(setNews).catch(() => {})
    apiFetch('surveys/').then(setSurveys).catch(() => {})
    apiFetch('useful-links/').then(setUsefulLinks).catch(() => {})
    apiFetch('articles/top/').then(setTopArticles).catch(() => {})
  }, [])

  function handleSurveyUpdated(updatedSurvey) {
    setSurveys((current) => current.map((s) => (s.id === updatedSurvey.id ? updatedSurvey : s)))
  }

  return (
    <>
      <ArticleSection menuId={initialMenuId} />
      <section className="boxes">
        <NewsBox items={news} />
        <SurveyBox surveys={surveys} onSurveyUpdated={handleSurveyUpdated} />
        <UsefulLinksBox items={usefulLinks} />
        <TopArticlesBox items={topArticles} />
      </section>
    </>
  )
}
