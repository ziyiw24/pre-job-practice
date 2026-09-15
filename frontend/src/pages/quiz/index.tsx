import { useEffect, useMemo, useState } from 'react'
import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import type { TrainingAnswerRecord } from '../../services/api'
import { loadQuestionFeedback, loadTrainingSession, saveQuestionFeedback, saveTrainingSession } from '../../services/trainingStorage'
import './index.scss'

export default function QuizPage() {
  const taskId = useRouter().params.taskId || ''
  const initial = useMemo(() => loadTrainingSession(taskId), [taskId])
  const quiz = initial?.quiz
  const [currentIndex, setCurrentIndex] = useState(initial?.currentIndex || 0)
  const [records, setRecords] = useState<TrainingAnswerRecord[]>(initial?.answers || [])
  const [selected, setSelected] = useState<string[]>([])
  const [submitted, setSubmitted] = useState(false)
  const [startedAt, setStartedAt] = useState(Date.now())
  const [quality, setQuality] = useState<'accurate' | 'ambiguous' | 'unsupported' | ''>('')

  const question = quiz?.questions[currentIndex]
  useEffect(() => {
    if (quiz?.title) Taro.setNavigationBarTitle({ title: quiz.title.slice(0, 12) })
  }, [quiz?.title])
  useEffect(() => {
    const existing = question ? records.find((item) => item.question_id === question.id) : null
    setSelected(existing?.selected_answers || [])
    setSubmitted(Boolean(existing))
    setStartedAt(Date.now())
    setQuality(question ? loadQuestionFeedback(taskId, question.id)?.value || '' : '')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex])

  if (!quiz || !question) {
    return <View className='quiz-page empty'><Text>本次练习已失效</Text><View className='primary-button' onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}><Text>重新生成</Text></View></View>
  }

  const answerKey = question.answer[0]
  const isCorrect = submitted && selected[0] === answerKey
  const progress = Math.round(((currentIndex + 1) / quiz.questions.length) * 100)

  const submit = () => {
    if (!selected.length) return
    const record: TrainingAnswerRecord = { question_id: question.id, selected_answers: selected, duration_ms: Date.now() - startedAt }
    const nextRecords = [...records.filter((item) => item.question_id !== question.id), record]
    setRecords(nextRecords)
    setSubmitted(true)
    saveTrainingSession(taskId, { quiz, answers: nextRecords, currentIndex })
  }

  const next = () => {
    if (currentIndex < quiz.questions.length - 1) {
      const nextIndex = currentIndex + 1
      setCurrentIndex(nextIndex)
      saveTrainingSession(taskId, { quiz, answers: records, currentIndex: nextIndex })
    } else {
      saveTrainingSession(taskId, { quiz, answers: records, currentIndex })
      Taro.redirectTo({ url: `/pages/report/index?taskId=${taskId}` })
    }
  }

  const optionClass = (key: string) => {
    if (!submitted) return selected.includes(key) ? 'option selected' : 'option'
    if (key === answerKey) return 'option correct'
    if (selected.includes(key)) return 'option wrong'
    return 'option muted'
  }

  return <View className='quiz-page'>
    <View className='quiz-top'><View><Text className='top-label'>岗位练习</Text><Text className='quiz-name'>{quiz.title}</Text></View><View className={`mode-badge ${quiz.ai_generated ? 'ai' : ''}`}><Text>{quiz.ai_generated ? 'AI 生成' : '演示生成'}</Text></View></View>
    <View className='progress-head'><Text>第 {currentIndex + 1} / {quiz.questions.length} 题</Text><Text>{progress}%</Text></View>
    <View className='progress-track'><View className='progress-fill' style={{ width: `${progress}%` }} /></View>

    <View className='question-card'>
      <View className='knowledge-row'><Text className='knowledge-tag'>{question.knowledge_point}</Text>{question.requires_confirmation && <Text className='risk-tag'>需店长确认</Text>}</View>
      {question.scenario && <Text className='scenario'>{question.scenario}</Text>}
      <Text className='stem'>{question.stem}</Text>
      <View className='options'>{question.options.map((option) => <View key={option.key} className={optionClass(option.key)} onClick={() => !submitted && setSelected([option.key])}><View className='option-key'><Text>{submitted && option.key === answerKey ? '✓' : submitted && selected.includes(option.key) ? '×' : option.key}</Text></View><Text className='option-text'>{option.text}</Text></View>)}</View>
      {!submitted && <View className={`submit-button ${selected.length ? '' : 'disabled'}`} onClick={submit}><Text>确认答案</Text></View>}
    </View>

    {submitted && <View className={`feedback ${isCorrect ? 'correct-feedback' : 'wrong-feedback'}`}>
      <Text className='feedback-title'>{isCorrect ? '答对了，你掌握了这条规则' : `这题需要复习，正确答案是 ${answerKey}`}</Text>
      <Text className='explanation'>{question.explanation}</Text>
      <View className='evidence'><Text className='evidence-label'>原文依据</Text><Text className='evidence-quote'>“{question.evidence.quote}”</Text></View>
      <Text className='quality-label'>这道题的质量如何？</Text>
      <View className='quality-actions'>{([['accurate', '准确'], ['ambiguous', '有歧义'], ['unsupported', '不符原文']] as const).map(([value, label]) => <View key={value} className={`quality-button ${quality === value ? 'selected' : ''}`} onClick={() => { setQuality(value); saveQuestionFeedback({ taskId, questionId: question.id, value, createdAt: Date.now() }) }}><Text>{label}</Text></View>)}</View>
      {question.requires_confirmation && <Text className='confirm-note'>此题涉及数字、时效、配方或安全要求，发布前请管理者复核。</Text>}
      <View className='next-button' onClick={next}><Text>{currentIndex < quiz.questions.length - 1 ? '下一题 →' : '查看学习报告 →'}</Text></View>
    </View>}
  </View>
}
