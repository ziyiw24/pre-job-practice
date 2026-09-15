import { useEffect, useState } from 'react'
import { Input, Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { AssignmentQuestion, AssignmentReport, ensureWechatLogin, getAssignmentQuestions, submitAssignmentAnswers } from '../../services/api'
import type { TrainingAnswerRecord } from '../../services/api'
import './index.scss'

const ROLE_KEY = 'training:entry-role'

export default function AssignmentPage() {
  const router = useRouter()
  const initialId = router.params.assignmentId || router.params.id || ''
  const [id, setId] = useState(initialId)
  const [questions, setQuestions] = useState<AssignmentQuestion[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [report, setReport] = useState<AssignmentReport | null>(null)
  const [loading, setLoading] = useState(false)
  const load = async (assignmentId = id) => {
    if (!assignmentId.trim()) return Taro.showToast({ title: '请输入培训任务 ID', icon: 'none' })
    try { setLoading(true); await ensureWechatLogin(); setQuestions(await getAssignmentQuestions(assignmentId.trim())) }
    catch (error: any) { Taro.showToast({ title: error.message || '任务打开失败', icon: 'none' }) }
    finally { setLoading(false) }
  }
  useEffect(() => { if (initialId) void load(initialId) }, [])
  const submit = async () => {
    if (questions.some(q => !answers[q.id])) return Taro.showToast({ title: '请完成所有题目', icon: 'none' })
    const rows: TrainingAnswerRecord[] = questions.map(q => ({ question_id: q.id, selected_answers: [answers[q.id]], duration_ms: 0 }))
    try { setReport(await submitAssignmentAnswers(id.trim(), rows)) } catch (error: any) { Taro.showToast({ title: error.message, icon: 'none' }) }
  }
  const switchRole = () => { Taro.removeStorageSync(ROLE_KEY); Taro.reLaunch({ url: '/pages/index/index' }) }
  return <View className='assignment-page'>
    <View className='assignment-head'><View><Text className='eyebrow'>员工入口</Text><Text className='page-title'>我的岗位练习</Text></View><Text className='switch-role' onClick={switchRole}>切换身份</Text></View>
    {!questions.length && <View className='join-card'><Text className='join-title'>打开店长分配的任务</Text><Text className='join-desc'>输入任务 ID，或直接打开店长分享的任务链接。</Text><Input value={id} onInput={e => setId(e.detail.value)} placeholder='输入培训任务 ID' /><View className={`button ${loading ? 'disabled' : ''}`} onClick={() => !loading && load()}><Text>{loading ? '正在打开…' : '开始答题'}</Text></View></View>}
    {questions.map((q, i) => <View className='card' key={q.id}><Text className='question-index'>第 {i + 1} 题</Text><Text className='question-stem'>{q.stem}</Text>{q.options.map(o => <View className={answers[q.id] === o.key ? 'option active' : 'option'} key={o.key} onClick={() => !report && setAnswers({ ...answers, [q.id]: o.key })}><Text>{o.key}. {o.text}</Text></View>)}</View>)}
    {!!questions.length && !report && <View className='button' onClick={submit}><Text>提交答案</Text></View>}
    {report && <View className='score'><Text className='score-number'>{report.score} 分</Text><Text>{report.certification_notice}</Text></View>}
  </View>
}
