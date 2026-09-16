import { useEffect } from 'react'
import { Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { clearAuthContext, devLogin, ensureWechatLogin, getAuthSession, getToken, syncAuthContext } from '../../services/api'
import './index.scss'

const ROLE_KEY = 'training:entry-role'

export default function IndexPage() {
  useEffect(() => {
    if (!getToken() || !Taro.getStorageSync(ROLE_KEY)) return
    syncAuthContext().then(next => {
      if (!next.membership) { clearAuthContext(); return }
      Taro.switchTab({ url: '/pages/main/home/index' })
    }).catch(() => clearAuthContext())
  }, [])

  const chooseRole = async (value: 'manager' | 'employee') => {
    try {
      let membership
      if (Taro.getEnv() === Taro.ENV_TYPE.WEB) membership = (await devLogin(value)).membership
      else {
        await ensureWechatLogin()
        membership = (await getAuthSession()).memberships.find(item => value === 'manager' ? item.role !== 'employee' : item.role === 'employee')
      }
      if (!membership) return Taro.navigateTo({ url: `/pages/onboarding/index?role=${value}` })
      Taro.setStorageSync(ROLE_KEY, value)
      Taro.setStorageSync('training:membership', membership)
      Taro.setStorageSync('training:store-id', membership.store_id)
      Taro.switchTab({ url: '/pages/main/home/index' })
    } catch (error: any) {
      Taro.showToast({ title: error.message || '登录失败', icon: 'none' })
    }
  }

  return <View className='role-page'>
    <View className='brand role-brand'><View className='brand-mark'><Text>练</Text></View><View><Text className='brand-name'>上岗练</Text><Text className='brand-sub'>门店培训，各走各的入口</Text></View></View>
    <View className='role-hero'><Text className='hero-kicker'>请选择你的身份</Text><Text className='hero-title'>你今天要做什么？</Text><Text className='hero-desc'>选择一次后会记住，下次打开直接进入对应流程。</Text></View>
    <View className='role-card manager-role' onClick={() => chooseRole('manager')}><Text className='role-icon'>店</Text><View className='role-copy'><Text className='role-title'>我是店长</Text><Text className='role-desc'>生成题库、上传手册、审核发布、查看成绩</Text></View><Text className='role-arrow'>→</Text></View>
    <View className='role-card employee-role' onClick={() => chooseRole('employee')}><Text className='role-icon'>答</Text><View className='role-copy'><Text className='role-title'>我是员工</Text><Text className='role-desc'>打开培训任务，直接开始答题</Text></View><Text className='role-arrow'>→</Text></View>
    <Text className='role-note'>员工不会看到标准答案，提交后由服务端判分</Text>
  </View>
}
