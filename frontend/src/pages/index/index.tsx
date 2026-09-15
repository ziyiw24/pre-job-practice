import { useEffect, useState } from 'react'
import { Input, Text, Textarea, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { createTrainingTask, getTrainingDemo } from '../../services/api'
import { createClientRequestId, loadTrainingDraft, saveTrainingDraft } from '../../services/trainingStorage'
import './index.scss'

const MIN_LENGTH = 500
const MAX_LENGTH = 8000
const ROLE_KEY = 'training:entry-role'

export default function IndexPage() {
  const [role, setRole] = useState<'manager' | 'employee' | ''>(() => Taro.getStorageSync(ROLE_KEY) || '')
  const cached = loadTrainingDraft()
  const [title, setTitle] = useState(cached?.title || '')
  const [content, setContent] = useState(cached?.content || '')
  const [questionCount, setQuestionCount] = useState<3 | 5>(cached?.questionCount || 5)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => saveTrainingDraft({ title, content, questionCount }), 300)
    return () => clearTimeout(timer)
  }, [title, content, questionCount])

  useEffect(() => {
    if (role === 'employee') Taro.reLaunch({ url: '/pages/assignment/index' })
  }, [role])

  const chooseRole = (value: 'manager' | 'employee') => {
    Taro.setStorageSync(ROLE_KEY, value)
    setRole(value)
  }

  const pasteDemo = async () => {
    try {
      const demo = await getTrainingDemo()
      setTitle(demo.title)
      setContent(demo.content)
      Taro.showToast({ title: '已填入脱敏示例', icon: 'success' })
    } catch (error: any) {
      Taro.showToast({ title: error.message || '示例加载失败', icon: 'none' })
    }
  }

  const start = async () => {
    const normalized = content.trim()
    if (normalized.length < MIN_LENGTH) {
      Taro.showToast({ title: `请至少粘贴 ${MIN_LENGTH} 字培训内容`, icon: 'none' })
      return
    }
    if (normalized.length > MAX_LENGTH) {
      Taro.showToast({ title: '内容过长，请分章节生成', icon: 'none' })
      return
    }
    setSubmitting(true)
    const clientRequestId = createClientRequestId()
    saveTrainingDraft({ title: title.trim(), content: normalized, questionCount, clientRequestId })
    try {
      const result = await createTrainingTask({
        client_request_id: clientRequestId, title: title.trim(), content: normalized,
        question_count: questionCount, difficulty: 'mixed',
      })
      Taro.navigateTo({ url: `/pages/generating/index?taskId=${result.task_id}` })
    } catch (error: any) {
      Taro.showToast({ title: error.message || '创建任务失败', icon: 'none', duration: 3000 })
    } finally { setSubmitting(false) }
  }

  if (!role) return <View className='role-page'>
    <View className='brand role-brand'><View className='brand-mark'><Text>练</Text></View><View><Text className='brand-name'>上岗练</Text><Text className='brand-sub'>门店培训，各走各的入口</Text></View></View>
    <View className='role-hero'><Text className='hero-kicker'>请选择你的身份</Text><Text className='hero-title'>你今天要做什么？</Text><Text className='hero-desc'>选择一次后会记住，下次打开直接进入对应流程。</Text></View>
    <View className='role-card manager-role' onClick={() => chooseRole('manager')}><Text className='role-icon'>店</Text><View className='role-copy'><Text className='role-title'>我是店长</Text><Text className='role-desc'>生成题库、上传手册、审核发布、查看成绩</Text></View><Text className='role-arrow'>→</Text></View>
    <View className='role-card employee-role' onClick={() => chooseRole('employee')}><Text className='role-icon'>答</Text><View className='role-copy'><Text className='role-title'>我是员工</Text><Text className='role-desc'>打开培训任务，直接开始答题</Text></View><Text className='role-arrow'>→</Text></View>
    <Text className='role-note'>员工不会看到标准答案，提交后由服务端判分</Text>
  </View>

  return <View className='input-page'>
    <View className='brand'><View className='brand-mark'><Text>练</Text></View><View><Text className='brand-name'>上岗练</Text><Text className='brand-sub'>把门店手册，变成会做的题</Text></View></View>
    <View className='hero'>
      <Text className='hero-kicker'>3 分钟验证培训效果</Text>
      <Text className='hero-title'>粘贴一段培训内容，{`\n`}立即生成岗位练习</Text>
      <Text className='hero-desc'>题目、解析和报告都以你的原文为依据，适合店长先验证题目质量。</Text>
    </View>
    <View className='form-card'>
      <View className='field-head'><Text className='field-label'>培训标题</Text><Text className='optional'>选填</Text></View>
      <Input className='title-input' maxlength={60} value={title} placeholder='例如：原料时效与异常处理' onInput={(event) => setTitle(event.detail.value)} />
      <View className='field-head content-head'><Text className='field-label'>培训内容</Text><Text className={content.length > MAX_LENGTH ? 'count danger' : 'count'}>{content.length} / {MAX_LENGTH}</Text></View>
      <View className='textarea-wrap'><Textarea className='content-input' maxlength={MAX_LENGTH + 1} value={content} placeholder='粘贴 SOP、操作标准、服务话术或食安要求……' onInput={(event) => setContent(event.detail.value)} /></View>
      <View className='helper-row'><Text>建议 {MIN_LENGTH}～{MAX_LENGTH} 字</Text><Text className='demo-link' onClick={pasteDemo}>不知道怎么写？粘贴示例</Text></View>
      <Text className='field-label count-title'>生成题量</Text>
      <View className='count-options'>{[3, 5].map((item) => <View key={item} className={`count-option ${questionCount === item ? 'active' : ''}`} onClick={() => setQuestionCount(item as 3 | 5)}><Text>{item} 题</Text><Text className='count-hint'>{item === 3 ? '快速验证' : '推荐'}</Text></View>)}</View>
      <View className={`primary-button ${submitting ? 'disabled' : ''}`} onClick={() => !submitting && start()}><Text>{submitting ? '正在提交…' : '生成岗位练习 →'}</Text></View>
      <View className='upload-button' onClick={() => Taro.navigateTo({ url: '/pages/upload/index' })}><Text>从 PDF / DOCX 生成</Text></View>
      <Text className='review-notice'>AI 生成内容需管理者确认，以门店最新正式制度为准</Text>
    </View>
    <View className='flow-row'><Text>① 读取规则</Text><Text>→</Text><Text>② 情景出题</Text><Text>→</Text><Text>③ 薄弱点报告</Text></View>
    <Text className='manager-link' onClick={() => Taro.navigateTo({ url: '/pages/manager/index' })}>店长管理中心</Text>
    <Text className='manager-link' onClick={() => { Taro.removeStorageSync(ROLE_KEY); setRole('') }}>切换为员工入口</Text>
    <Text className='manager-link' onClick={() => Taro.navigateTo({ url: '/pages/privacy/index' })}>隐私、删除与投诉</Text>
  </View>
}
