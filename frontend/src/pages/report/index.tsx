import { useEffect, useMemo, useRef, useState } from 'react'
import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { createTrainingReport } from '../../services/api'
import type { TrainingReport } from '../../services/api'
import { loadTrainingSession, saveTrainingSession } from '../../services/trainingStorage'
import './index.scss'

function heading(score: number) {
  if (score >= 80) return '基础规则已掌握'
  if (score >= 60) return '再补齐几个关键点'
  return '建议复训后再测一次'
}

export default function ReportPage() {
  const taskId = useRouter().params.taskId || ''
  const session = useMemo(() => loadTrainingSession(taskId), [taskId])
  const [report, setReport] = useState<TrainingReport | null>(session?.report || null)
  const [loading, setLoading] = useState(!session?.report)
  const [error, setError] = useState('')
  const requested = useRef(false)

  const fetchReport = async () => {
    if (!session) { setError('本次练习已失效'); setLoading(false); return }
    setError(''); setLoading(true)
    try {
      const result = await createTrainingReport({ quiz_id: session.quiz.quiz_id, questions: session.quiz.questions, answer_records: session.answers })
      setReport(result)
      saveTrainingSession(taskId, { ...session, report: result })
    } catch (err: any) { setError(err.message || '报告生成失败') }
    finally { setLoading(false) }
  }

  useEffect(() => {
    if (!requested.current && !report) { requested.current = true; fetchReport() }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!session) return <View className='report-page empty'><Text>本次练习已失效</Text><View className='primary-action' onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}><Text>返回首页</Text></View></View>
  const quiz = session.quiz
  const redo = () => {
    saveTrainingSession(taskId, { quiz, answers: [], currentIndex: 0 })
    Taro.redirectTo({ url: `/pages/quiz/index?taskId=${taskId}` })
  }

  return <View className='report-page'>
    <View className='report-kicker'><Text>学习分析报告</Text><Text className='report-mode'>{report?.ai_generated ? 'AI 分析' : '规则分析'}</Text></View>
    <Text className='report-title'>{quiz.title}</Text>
    {loading && <View className='loading-card'><View className='loading-dot' /><Text>正在核对答案并生成复习建议…</Text></View>}
    {error && <View className='error-card'><Text>{error}</Text><View className='retry' onClick={fetchReport}><Text>重新生成报告</Text></View></View>}
    {report && <>
      <View className={`score-card ${report.result}`}><View><Text className='score-label'>{heading(report.score)}</Text><Text className='score-detail'>答对 {report.correct_count} / {report.total_count} 题</Text></View><View className='score-circle'><Text className='score-number'>{report.score}</Text><Text className='score-unit'>分</Text></View></View>
      <Text className='summary'>{report.ai_summary}</Text>
      <View className='report-card'><Text className='card-title'>需要优先复习</Text>{report.weak_points.length ? report.weak_points.map((point, index) => <View className='point weak' key={point}><Text className='point-index'>{index + 1}</Text><Text>{point}</Text></View>) : <Text className='empty-copy'>本次没有错题，可以结合实际操作再巩固一遍。</Text>}</View>
      <View className='report-card'><Text className='card-title'>下一步怎么练</Text>{report.review_actions.map((action, index) => <View className='action-row' key={`${action}-${index}`}><View className='action-check'><Text>✓</Text></View><Text>{action}</Text></View>)}</View>
      <View className='report-card'><Text className='card-title'>逐题回顾</Text>{quiz.questions.map((question, index) => <View className='review-item' key={question.id}><View className='review-head'><Text>{index + 1}. {question.knowledge_point}</Text><Text className={report.answer_results[question.id] ? 'right' : 'wrong'}>{report.answer_results[question.id] ? '已掌握' : '需复习'}</Text></View><Text className='review-stem'>{question.stem}</Text><Text className='review-quote'>原文：{question.evidence.quote}</Text></View>)}</View>
      <Text className='certification'>{report.certification_notice}</Text>
      <View className='bottom-actions'><View className='primary-action' onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}><Text>用新内容再练一次</Text></View><View className='secondary-action' onClick={redo}><Text>重做本组题</Text></View></View>
    </>}
  </View>
}
