import { useState } from 'react'
import { Input, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { generateDocumentDraft, uploadTrainingDocument } from '../../services/api'
import './index.scss'

export default function UploadPage() {
  const [title,setTitle]=useState(''); const [count,setCount]=useState<3|5>(5); const [busy,setBusy]=useState(false); const [file,setFile]=useState<{path:string;name:string}|null>(null)
  const choose=async()=>{ try { const result=await Taro.chooseMessageFile({count:1,type:'file',extension:['pdf','docx']}); const f=result.tempFiles[0]; if(f.size>10*1024*1024) return Taro.showToast({title:'文件不能超过 10 MB',icon:'none'}); setFile({path:f.path,name:f.name}) } catch {} }
  const start=async()=>{ if(!file||busy)return; setBusy(true); try { const doc=await uploadTrainingDocument(file.path,file.name); const draft=await generateDocumentDraft(doc.document_id,title,count); Taro.redirectTo({url:`/pages/review/index?quizId=${draft.quiz_id}`}) } catch(e:any){Taro.showToast({title:e.message||'处理失败',icon:'none',duration:3000})} finally{setBusy(false)} }
  return <View className='upload-page'><Text className='title'>从门店手册生成练习</Text><Text className='hint'>支持 PDF、DOCX，最大 10 MB / 50 页；扫描件暂不支持 OCR。</Text><Input className='input' value={title} placeholder='培训标题（选填）' onInput={e=>setTitle(e.detail.value)} /><View className='picker' onClick={choose}><Text>{file?.name||'选择微信会话中的文件'}</Text></View><View className='counts'>{([3,5] as const).map(x=><View className={count===x?'active':''} onClick={()=>setCount(x)} key={x}><Text>{x} 题</Text></View>)}</View><View className={`submit ${!file||busy?'disabled':''}`} onClick={start}><Text>{busy?'正在解析…':'上传并生成'}</Text></View></View>
}
