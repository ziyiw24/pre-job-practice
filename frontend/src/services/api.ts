import Taro from '@tarojs/taro'

// 由 frontend/config/dev.ts、frontend/config/prod.ts 中的 defineConstants 按环境注入
declare const API_BASE_URL: string

const BASE_URL = API_BASE_URL

const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'

/* ---- 登录就绪机制：确保页面在登录完成后再请求需要鉴权的接口 ---- */
let _loginResolve: () => void
const _loginReady = new Promise<void>((resolve) => { _loginResolve = resolve })

/** 等待登录流程完成（无论成功或失败） */
export function waitForLogin(): Promise<void> { return _loginReady }

/** 标记登录流程已结束 */
export function resolveLogin() { _loginResolve() }

interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

/** 获取本地存储的 token */
export function getToken(): string {
  return Taro.getStorageSync(TOKEN_KEY) || ''
}

/** 保存 token */
export function setToken(token: string) {
  Taro.setStorageSync(TOKEN_KEY, token)
}

/** 清除 token */
export function clearToken() {
  Taro.removeStorageSync(TOKEN_KEY)
  Taro.removeStorageSync(USER_KEY)
}

/** 获取本地缓存的用户信息 */
export function getCachedUser(): UserBrief | null {
  const raw = Taro.getStorageSync(USER_KEY)
  return raw || null
}

/** 缓存用户信息 */
export function setCachedUser(user: UserBrief) {
  Taro.setStorageSync(USER_KEY, user)
}

export async function request<T = any>(
  url: string,
  options: {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
    data?: any
    timeout?: number
  } = {},
): Promise<T> {
  const { method = 'GET', data, timeout = 120000 } = options

  const header: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const token = getToken()
  if (token) {
    header['Authorization'] = `Bearer ${token}`
  }

  const res = await Taro.request({
    url: `${BASE_URL}${url}`,
    method,
    data,
    header,
    timeout,
  })

  const body = res.data as ApiResponse<T>

  // 401 未认证 — 清除本地凭证
  if (body.code === 4010) {
    clearToken()
    throw new Error('登录已过期，请重新进入小程序')
  }

  if (body.code !== 0) {
    throw new Error(body.message || '请求失败')
  }

  return body.data
}

/* ---- 核心业务 API ---- */

/** 上岗练 M0：匿名文本出题 */
export function createTrainingTask(params: TrainingGenerateParams) {
  return request<{ task_id: string; status: TrainingTaskStatus['status'] }>('/training/generate/async', {
    method: 'POST',
    data: params,
  })
}

export function getTrainingTask(taskId: string) {
  return request<TrainingTaskStatus>(`/training/tasks/${taskId}`)
}

export function getTrainingDemo() {
  return request<TrainingDemo>('/training/demo')
}

export function createTrainingReport(params: TrainingReportParams) {
  return request<TrainingReport>('/training/reports', {
    method: 'POST',
    data: params,
  })
}

export function uploadTrainingDocument(filePath: string, fileName: string): Promise<TrainingDocument> {
  const token = getToken()
  return new Promise((resolve, reject) => Taro.uploadFile({
    url: `${BASE_URL}/training/documents`, filePath, name: 'file',
    formData: { fileName, store_id: Taro.getStorageSync('training:store-id') || '' },
    header: token ? { Authorization: `Bearer ${token}` } : {},
    success: (res) => {
      try { const body = JSON.parse(res.data) as ApiResponse<TrainingDocument>; body.code === 0 ? resolve(body.data) : reject(new Error(body.message)) }
      catch { reject(new Error('文档上传响应无效')) }
    }, fail: reject,
  }))
}
export function getTrainingDocument(documentId: string) { return request<TrainingDocument>(`/training/documents/${documentId}`) }
export function generateDocumentDraft(documentId: string, title: string, questionCount: 3 | 5) { return request<{quiz_id: string; status: string}>(`/training/documents/${documentId}/generate`, { method: 'POST', data: { title, question_count: questionCount, difficulty: 'mixed' } }) }
export function getTrainingDraft(quizId: string) { return request<TrainingDraftReview>(`/training/drafts/${quizId}`) }
export function updateDraftQuestion(quizId: string, questionId: string, data: Record<string, any>) { return request<TrainingDraftReview>(`/training/drafts/${quizId}/questions/${questionId}`, { method: 'PUT', data }) }
export function deleteDraftQuestion(quizId:string,questionId:string){return request<TrainingDraftReview>(`/training/drafts/${quizId}/questions/${questionId}`,{method:'DELETE'})}
export function approveTrainingDraft(quizId: string) { return request<TrainingDraftReview>(`/training/drafts/${quizId}/approve`, { method: 'POST' }) }

/** 生成题库（异步任务模式） */
export function generateQuizAsync(
  userInput: string,
  questionCount = 5,
  docId?: string,
  generateImages = false,
) {
  return request<{ task_id: string }>('/quiz/generate/async', {
    method: 'POST',
    data: {
      user_input: userInput,
      question_count: questionCount,
      difficulty: 'mixed',
      doc_id: docId,
      generate_images: generateImages,
    },
  })
}

/** 从已审核专题生成题库 */
export function generateTopicQuizAsync(
  topicId: string,
  questionCount = 5,
  difficulty: 'easy' | 'medium' | 'hard' = 'easy',
) {
  return request<{ task_id: string }>('/quiz/generate/async', {
    method: 'POST',
    data: { topic_id: topicId, question_count: questionCount, difficulty, generate_images: false },
  })
}

/** 获取已审核精选专题 */
export function getTopics() {
  return request<TopicListResponse>('/topics')
}

/** 查询出题任务状态 */
export function getQuizTaskStatus(taskId: string) {
  return request<QuizTaskStatus>(`/quiz/task/${taskId}`)
}

/** 轮询等待出题任务完成 */
export function pollQuizTask(
  taskId: string,
  onProgress?: (status: string) => void,
  intervalMs = 1200,
  maxAttempts = 100,
): Promise<QuizData> {
  return new Promise((resolve, reject) => {
    let attempts = 0
    const timer = setInterval(async () => {
      attempts++
      try {
        const res = await getQuizTaskStatus(taskId)
        onProgress?.(res.status)

        if (res.status === 'completed' && res.result) {
          clearInterval(timer)
          resolve(res.result)
        } else if (res.status === 'failed') {
          clearInterval(timer)
          reject(new Error(res.error_message || '题目生成失败'))
        } else if (attempts >= maxAttempts) {
          clearInterval(timer)
          reject(new Error('生成超时，请稍后重试'))
        }
      } catch (err) {
        clearInterval(timer)
        reject(err)
      }
    }, intervalMs)
  })
}

/** 生成题库（同步，保留兼容） */
export function generateQuiz(userInput: string, questionCount = 5, generateImages = false) {
  return request<QuizData>('/quiz/generate', {
    method: 'POST',
    data: {
      user_input: userInput,
      question_count: questionCount,
      difficulty: 'mixed',
      generate_images: generateImages,
    },
    timeout: 600000,
  })
}

/** 生成复盘报告 */
export function generateReport(params: {
  quiz_id: string
  topic: string
  questions: Question[]
  answer_records: AnswerRecord[]
}) {
  return request<ReportData>('/report/generate', {
    method: 'POST',
    data: params,
    timeout: 600000,
  })
}

/* ---- 用户 API ---- */

/** 微信登录 */
export function loginByCode(code: string) {
  return request<LoginResponse>('/user/login', {
    method: 'POST',
    data: { code },
  })
}

export async function ensureWechatLogin() {
  if (getToken()) return getCachedUser()
  const login = await Taro.login()
  const result = await loginByCode(login.code)
  setToken(result.token)
  setCachedUser(result.user)
  return result.user
}

export function createStore(name: string) { return request<{ id: string; name: string }>('/stores', { method: 'POST', data: { name } }) }
export function addStoreMember(storeId: string, userId: number, role: 'manager' | 'employee') { return request(`/stores/${storeId}/members`, { method: 'POST', data: { user_id: userId, role } }) }
export function createStoreCourse(storeId: string, title: string, questions: TrainingQuestion[], confirmedQuestionIds: string[]) { return request<{ id: string; status: string }>(`/stores/${storeId}/courses`, { method: 'POST', data: { title, questions, confirmed_question_ids: confirmedQuestionIds } }) }
export function publishStoreCourse(courseId: string) { return request<{ id: string; status: string }>(`/courses/${courseId}/publish`, { method: 'POST' }) }
export function createAssignment(courseId: string, employeeUserId: number) { return request<{ id: string; status: string }>(`/courses/${courseId}/assignments`, { method: 'POST', data: { employee_user_id: employeeUserId } }) }
export type AssignmentQuestion = Omit<TrainingQuestion, 'answer' | 'explanation'>
export function getAssignmentQuestions(id: string) { return request<AssignmentQuestion[]>(`/employee/assignments/${id}/questions`) }
export function submitAssignmentAnswers(id: string, answers: TrainingAnswerRecord[]) { return request<AssignmentReport>(`/employee/assignments/${id}/answers`, { method: 'POST', data: { answers } }) }
export interface AssignmentReport { score: number; correct_count: number; total_count: number; answer_results: Record<string, boolean>; questions: TrainingQuestion[]; certification_notice: string }
export function createPrivacyRequest(requestType:'complaint'|'delete_account'|'delete_document',detail:string,resourceId?:string){return request<{request_id:string;status:string}>('/privacy/requests',{method:'POST',data:{request_type:requestType,detail,resource_id:resourceId}})}
export interface StoreResult { assignment_id:string; employee_user_id:number; course_id:string; status:string; score:number|null }
export function getStoreResults(storeId:string){return request<StoreResult[]>(`/stores/${storeId}/results`)}

/** 获取用户资料（含统计） */
export function getUserProfile() {
  return request<UserProfile>('/user/profile')
}

/** 更新用户资料 */
export function updateUserProfile(data: { nickname?: string; avatar_url?: string }) {
  return request<null>('/user/profile', {
    method: 'PUT',
    data,
  })
}

/** 获取闯关历史（分页） */
export function getQuizHistory(page = 1, pageSize = 10) {
  return request<QuizHistoryList>(`/user/quizzes?page=${page}&page_size=${pageSize}`)
}

/** 获取闯关详情 */
export function getQuizDetail(quizId: string) {
  return request<QuizDetailResponse>(`/user/quizzes/${quizId}`)
}

/* ---- 知识库 API ---- */

/** 上传知识库文档（PDF/Word/Markdown/文本） */
export function uploadKnowledgeDocument(filePath: string, fileName: string): Promise<KnowledgeUploadResponse> {
  const token = getToken()
  const header: Record<string, string> = {}
  if (token) {
    header['Authorization'] = `Bearer ${token}`
  }

  return new Promise((resolve, reject) => {
    Taro.uploadFile({
      url: `${BASE_URL}/knowledge/documents`,
      filePath,
      name: 'file',
      fileName,
      header,
      timeout: 120000,
      success: (res) => {
        try {
          const body = JSON.parse(res.data) as ApiResponse<KnowledgeUploadResponse>
          if (body.code === 4010) {
            clearToken()
            reject(new Error('登录已过期，请重新进入小程序'))
            return
          }
          if (body.code !== 0) {
            reject(new Error(body.message || '上传失败'))
            return
          }
          resolve(body.data)
        } catch (e) {
          reject(new Error('上传响应解析失败'))
        }
      },
      fail: (err) => reject(new Error(err.errMsg || '上传失败')),
    })
  })
}

/** 获取知识库文档列表 */
export function getKnowledgeDocuments() {
  return request<KnowledgeListResponse>('/knowledge/documents')
}

/** 查询知识库文档处理状态 */
export function getKnowledgeDocumentStatus(docId: string) {
  return request<KnowledgeDocumentStatus>(`/knowledge/documents/${docId}`)
}

/** 删除知识库文档 */
export function deleteKnowledgeDocument(docId: string) {
  return request<null>(`/knowledge/documents/${docId}`, {
    method: 'DELETE',
  })
}

/* ---- 类型定义 ---- */

export interface TrainingGenerateParams {
  client_request_id: string
  title: string
  content: string
  question_count: 3 | 5
  difficulty: 'easy' | 'mixed' | 'hard'
}

export interface TrainingEvidence {
  quote: string
  start_offset?: number | null
  end_offset?: number | null
  page_number?: number | null
}

export interface TrainingQuestion {
  id: string
  type: 'single' | 'judge'
  scenario?: string | null
  stem: string
  options: QuestionOption[]
  answer: string[]
  explanation: string
  knowledge_point: string
  evidence: TrainingEvidence
  risk_tags: string[]
  requires_confirmation: boolean
}

export interface TrainingQuiz {
  quiz_id: string
  title: string
  summary: string
  questions: TrainingQuestion[]
  ai_generated: boolean
  generation_mode: 'ai' | 'demo'
  review_notice: string
}

export interface TrainingTaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'awaiting_review' | 'completed' | 'failed'
  progress_stage: 'reading' | 'extracting' | 'planning' | 'generating' | 'validating' | 'reviewing' | 'rewriting' | 'awaiting_review'
  agent: { revision_count: number; max_revisions: number; issue_count: number; model_calls: number; graph_version: string } | null
  result: TrainingQuiz | null
  error_code: string | null
  error_message: string | null
}

export interface TrainingAnswerRecord {
  question_id: string
  selected_answers: string[]
  duration_ms: number
}

export interface TrainingReportParams {
  quiz_id: string
  questions: TrainingQuestion[]
  answer_records: TrainingAnswerRecord[]
}

export interface TrainingReport {
  score: number
  correct_count: number
  total_count: number
  result: 'passed' | 'needs_review'
  mastered_points: string[]
  weak_points: string[]
  review_actions: string[]
  ai_summary: string
  ai_generated: boolean
  answer_results: Record<string, boolean>
  certification_notice: string
}

export interface TrainingDemo { title: string; content: string }
export interface DocumentBlock { block_id: string; page_number: number | null; paragraph_index: number; text: string; start_offset: number; end_offset: number }
export interface TrainingDocument { document_id: string; file_name: string; status: 'uploaded'|'parsing'|'ready'|'failed'; blocks?: DocumentBlock[]; content?: string; error_code?: string|null; error_message?: string|null }
export interface TrainingDraftReview { quiz_id: string; document_id: string; status: 'draft'|'awaiting_review'|'approved'|'published'; questions: TrainingQuestion[]; confirmed_question_ids: string[] }

export interface QuestionOption {
  key: string
  text: string
}

export interface Question {
  id: string
  type: 'single' | 'multiple' | 'judge'
  stem: string
  options: QuestionOption[]
  answer: string[]
  explanation: string
  knowledge_point: string
  difficulty: 'easy' | 'medium' | 'hard'
  image_url?: string | null
  domain: 'fitness' | 'tcm' | 'safety' | 'general'
  source_refs: string[]
  risk_level: 'low' | 'medium' | 'high'
}

export interface QuizData {
  quiz_id: string
  title: string
  summary: string
  questions: Question[]
  image_notice?: string | null
  topic_id?: string | null
  domain: 'fitness' | 'tcm' | 'safety' | 'general'
  source_refs: string[]
  health_notice: string
}

export interface TopicSource { title: string; publisher: string; url: string }
export interface Topic {
  id: string
  slug: string
  title: string
  summary: string
  category: 'fitness' | 'tcm' | 'safety'
  difficulty: 'easy' | 'medium' | 'hard'
  review_status: 'approved'
  updated_at: string
  risk_level: 'low' | 'medium' | 'high'
  icon: string
  sources: TopicSource[]
}
export interface TopicListResponse { items: Topic[]; total: number }

export interface QuizTaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result: QuizData | null
  error_message: string | null
}

export interface AnswerRecord {
  question_id: string
  selected_answers: string[]
  is_correct: boolean
  duration_ms: number
}

export interface ReportData {
  accuracy: number
  mastered_points: string[]
  weak_points: string[]
  three_line_summary: string[]
  advice: string[]
  share_quote: string
}

export interface UserBrief {
  id: number
  nickname: string
  avatar_url: string
  total_xp: number
}

export interface LoginResponse {
  token: string
  user: UserBrief
}

export interface UserProfile {
  id: number
  nickname: string
  avatar_url: string
  total_xp: number
  quiz_count: number
  correct_count: number
  average_accuracy: number
}

export interface QuizHistoryItem {
  quiz_id: string
  title: string
  accuracy: number
  question_count: number
  created_at: string
}

export interface QuizHistoryList {
  items: QuizHistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface QuizDetailResponse {
  quiz_id: string
  title: string
  summary: string
  user_input?: string
  questions: Question[]
  answer_records?: AnswerRecord[]
  report?: ReportData
  created_at: string
}

/* ---- 知识库类型定义 ---- */

export type KnowledgeDocumentStatusEnum = 'processing' | 'ready' | 'failed'

export interface KnowledgeUploadResponse {
  doc_id: string
  file_name: string
  status: KnowledgeDocumentStatusEnum
}

export interface KnowledgeDocumentItem {
  doc_id: string
  file_name: string
  file_type: string
  file_size: number
  status: KnowledgeDocumentStatusEnum
  chunk_count: number
  error_message: string | null
  created_at: string
}

export interface KnowledgeListResponse {
  items: KnowledgeDocumentItem[]
}

export interface KnowledgeDocumentStatus {
  doc_id: string
  file_name: string
  status: KnowledgeDocumentStatusEnum
  chunk_count: number
  error_message: string | null
}
