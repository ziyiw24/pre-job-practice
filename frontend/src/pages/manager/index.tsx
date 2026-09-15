import { useState } from 'react'
import { Input, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { addStoreMember, createAssignment, createStore, ensureWechatLogin, getStoreResults, StoreResult } from '../../services/api'
import './index.scss'

export default function ManagerPage() {
  const [name,setName]=useState(''); const [member,setMember]=useState(''); const [course,setCourse]=useState('')
  const [store,setStore]=useState<string>(Taro.getStorageSync('training:store-id')||'')
  const [results,setResults]=useState<StoreResult[]>([])
  const setup=async()=>{try{const user=await ensureWechatLogin();if(!user)throw new Error('登录失败');const value=await createStore(name);setStore(value.id);Taro.setStorageSync('training:store-id',value.id);Taro.showModal({title:'门店已创建',content:`用户 ID：${user.id}\n门店 ID：${value.id}`,showCancel:false})}catch(e:any){Taro.showToast({title:e.message,icon:'none'})}}
  const add=async()=>{try{await addStoreMember(store,Number(member),'employee');Taro.showToast({title:'员工已加入',icon:'success'})}catch(e:any){Taro.showToast({title:e.message,icon:'none'})}}
  const assign=async()=>{try{const value=await createAssignment(course,Number(member));Taro.showModal({title:'任务已创建',content:`任务 ID：${value.id}`,showCancel:false})}catch(e:any){Taro.showToast({title:e.message,icon:'none'})}}
  const loadResults=async()=>{try{await ensureWechatLogin();setResults(await getStoreResults(store))}catch(e:any){Taro.showToast({title:e.message,icon:'none'})}}
  const switchRole=()=>{Taro.removeStorageSync('training:entry-role');Taro.reLaunch({url:'/pages/index/index'})}
  return <View className='manager-page'><View className='manager-head'><Text className='title'>店长工作台</Text><Text className='switch-role' onClick={switchRole}>切换身份</Text></View><View className='button ghost' onClick={()=>Taro.reLaunch({url:'/pages/index/index'})}><Text>生成新题库</Text></View><Input value={name} onInput={e=>setName(e.detail.value)} placeholder='门店名称'/><View className='button' onClick={setup}><Text>登录并创建门店</Text></View><Text className='meta'>当前门店：{store||'未创建'}</Text><Input value={member} onInput={e=>setMember(e.detail.value)} type='number' placeholder='员工用户 ID'/><View className='button secondary' onClick={add}><Text>添加员工</Text></View><Input value={course} onInput={e=>setCourse(e.detail.value)} placeholder='已发布课程 ID'/><View className='button secondary' onClick={assign}><Text>分配课程</Text></View><View className='button ghost' onClick={loadResults}><Text>查看本店成绩</Text></View>{results.map(x=><View className='result' key={x.assignment_id}><Text>员工 {x.employee_user_id} · {x.score===null?'未完成':`${x.score} 分`}</Text></View>)}</View>
}
