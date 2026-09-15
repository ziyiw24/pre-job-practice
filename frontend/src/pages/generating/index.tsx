import { useEffect, useRef, useState } from 'react'
import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { getTrainingTask } from '../../services/api'
import type { TrainingTaskStatus } from '../../services/api'
import { saveTrainingSession } from '../../services/trainingStorage'
import './index.scss'

const stageCopy = {
  reading: ['正在读取培训内容', '理解你提供的门店规则'],
  extracting: ['正在整理关键考点', '优先识别步骤、红线和异常处理'],
  planning: ['正在规划题目', '优先覆盖必须项、安全与禁止项'],
  generating: ['正在生成岗位练习', '把纸面规则改写成真实工作判断'],
  validating: ['正在校验题目依据', '确保每道题都能回到你的原文'],
  reviewing: ['正在审查题目质量', '检查答案唯一性和场景有效性'],
  rewriting: ['正在修订问题题目', '只重写未通过质检的题目'],
  awaiting_review: ['需要管理者审核', '高风险或多次修订的题目需要人工确认'],
}

export default function GeneratingPage() {
  const taskId = useRouter().params.taskId || ''
  const [task, setTask] = useState<TrainingTaskStatus | null>(null)
  const [error, setError] = useState('')
  const attempts = useRef(0)

  const check = async () => {
    if (!taskId) { setError('未找到生成任务'); return true }
    try {
      const result = await getTrainingTask(taskId)
      setTask(result)
      if (result.status === 'completed' && result.result) {
        saveTrainingSession(taskId, { quiz: result.result, answers: [], currentIndex: 0 })
        Taro.redirectTo({ url: `/pages/quiz/index?taskId=${taskId}` })
        return true
      }
      if (result.status === 'failed') {
        setError(result.error_message || '题目生成失败')
        return true
      }
      if (result.status === 'awaiting_review') {
        setError('题目需要管理者审核，请稍后在审核页处理。')
        return true
      }
    } catch (err: any) {
      setError(err.message || '查询任务失败')
      return true
    }
    return false
  }

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      if (cancelled) return
      attempts.current += 1
      const done = await check()
      if (!done && attempts.current < 100) timer = setTimeout(poll, 1200)
      if (!done && attempts.current >= 100) setError('生成时间较长，你可以继续查询或返回重试。')
    }
    poll()
    return () => { cancelled = true; if (timer) clearTimeout(timer) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId])

  const stage = task?.progress_stage || 'reading'
  const copy = stageCopy[stage] || ['正在处理', '请稍候，任务状态正在更新']
  const stageIndex = Object.keys(stageCopy).indexOf(stage)

  return <View className='generating-page'>
    <View className='loader'><View className='loader-inner'><Text>练</Text></View></View>
    <Text className='generating-title'>{error || copy[0]}</Text>
    <Text className='generating-desc'>{error ? '你粘贴的内容已保存，返回后不需要重新输入。' : copy[1]}</Text>
    {!error && <View className='stage-list'>{Object.entries(stageCopy).map(([key, value], index) => <View key={key} className={`stage ${index <= stageIndex ? 'active' : ''}`}><View className='stage-dot'><Text>{index < stageIndex ? '✓' : index + 1}</Text></View><Text>{value[0]}</Text></View>)}</View>}
    {error && <View className='error-actions'><View className='primary-action' onClick={() => { setError(''); attempts.current = 0; check() }}><Text>再查询一次</Text></View><View className='secondary-action' onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}><Text>返回修改内容</Text></View></View>}
    <Text className='bottom-note'>请保持页面打开，通常需要 10～40 秒</Text>
  </View>
}
