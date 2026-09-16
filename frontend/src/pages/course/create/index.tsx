import { useEffect, useState } from 'react'
import { Input, Text, Textarea, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { createTrainingTask, getTrainingDemo, syncAuthContext } from '../../../services/api'
import { createClientRequestId, loadTrainingDraft, saveTrainingDraft } from '../../../services/trainingStorage'
import './index.scss'

const MIN_LENGTH = 500
const MAX_LENGTH = 8000

export default function CreateCoursePage() {
  const cached = loadTrainingDraft()
  const [title, setTitle] = useState(cached?.title || '')
  const [content, setContent] = useState(cached?.content || '')
  const [questionCount, setQuestionCount] = useState<3 | 5>(cached?.questionCount || 5)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    syncAuthContext().then(({ role, membership }) => {
      if (!membership || role !== 'manager') {
        Taro.showToast({ title: '仅店长可新建题库', icon: 'none' })
        Taro.switchTab({ url: '/pages/main/home/index' })
      }
    }).catch(() => Taro.reLaunch({ url: '/pages/index/index' }))
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => saveTrainingDraft({ title, content, questionCount }), 300)
    return () => clearTimeout(timer)
  }, [title, content, questionCount])

  const pasteDemo = async () => {
    try {
      const demo = await getTrainingDemo()
      setTitle(demo.title)
      setContent(demo.content)
      Taro.showToast({ title: '已填入脱敏示例', icon: 'success' })
    } catch (error: any) { Taro.showToast({ title: error.message || '示例加载失败', icon: 'none' }) }
  }

  const start = async () => {
    const normalized = content.trim()
    if (normalized.length < MIN_LENGTH) return Taro.showToast({ title: `请至少粘贴 ${MIN_LENGTH} 字培训内容`, icon: 'none' })
    if (normalized.length > MAX_LENGTH) return Taro.showToast({ title: '内容过长，请分章节生成', icon: 'none' })
    setSubmitting(true)
    const clientRequestId = createClientRequestId()
    saveTrainingDraft({ title: title.trim(), content: normalized, questionCount, clientRequestId })
    try {
      const result = await createTrainingTask({ client_request_id: clientRequestId, title: title.trim(), content: normalized, question_count: questionCount, difficulty: 'mixed' })
      Taro.navigateTo({ url: `/pages/generating/index?taskId=${result.task_id}` })
    } catch (error: any) {
      Taro.showToast({ title: error.message || '创建任务失败', icon: 'none', duration: 3000 })
    } finally { setSubmitting(false) }
  }

  return <View className='input-page'>
    <View className='create-page-head'><Text className='create-back' onClick={() => Taro.navigateBack()}>← 返回题库</Text></View>
    <View className='hero'><Text className='hero-kicker'>店长工作台</Text><Text className='hero-title'>新建题库</Text><Text className='hero-desc'>粘贴门店制度或 SOP，生成后先审核原文依据，再发布给员工。</Text></View>
    <View className='form-card'>
      <View className='field-head'><Text className='field-label'>培训标题</Text><Text className='optional'>选填</Text></View>
      <Input className='title-input' maxlength={60} value={title} placeholder='例如：原料时效与异常处理' onInput={event => setTitle(event.detail.value)} />
      <View className='field-head content-head'><Text className='field-label'>培训内容</Text><Text className={content.length > MAX_LENGTH ? 'count danger' : 'count'}>{content.length} / {MAX_LENGTH}</Text></View>
      <View className='textarea-wrap'><Textarea className='content-input' maxlength={MAX_LENGTH + 1} value={content} placeholder='粘贴 SOP、操作标准、服务话术或食安要求……' onInput={event => setContent(event.detail.value)} /></View>
      <View className='helper-row'><Text>建议 {MIN_LENGTH}～{MAX_LENGTH} 字</Text><Text className='demo-link' onClick={pasteDemo}>不知道怎么写？粘贴示例</Text></View>
      <Text className='field-label count-title'>生成题量</Text>
      <View className='count-options'>{[3, 5].map(item => <View key={item} className={`count-option ${questionCount === item ? 'active' : ''}`} onClick={() => setQuestionCount(item as 3 | 5)}><Text>{item} 题</Text><Text className='count-hint'>{item === 3 ? '快速验证' : '推荐'}</Text></View>)}</View>
      <View className={`primary-button ${submitting ? 'disabled' : ''}`} onClick={() => !submitting && start()}><Text>{submitting ? '正在提交…' : '生成岗位练习 →'}</Text></View>
      <View className='upload-button' onClick={() => Taro.navigateTo({ url: '/pages/upload/index' })}><Text>从 PDF / DOCX 生成</Text></View>
      <Text className='review-notice'>AI 生成内容需管理者确认，以门店最新正式制度为准</Text>
    </View>
  </View>
}
