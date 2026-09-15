import Taro from '@tarojs/taro'
import type { TrainingAnswerRecord, TrainingQuiz, TrainingReport } from './api'

const DRAFT_KEY = 'training:draft'
const FEEDBACK_KEY = 'training:question-feedback'

export interface QuestionFeedback {
  taskId: string
  questionId: string
  value: 'accurate' | 'ambiguous' | 'unsupported'
  note?: string
  createdAt: number
}

export interface TrainingDraft {
  title: string
  content: string
  questionCount: 3 | 5
  clientRequestId?: string
}

export interface TrainingSession {
  quiz: TrainingQuiz
  answers: TrainingAnswerRecord[]
  currentIndex: number
  report?: TrainingReport
}

export const trainingSessionKey = (taskId: string) => `training:session:${taskId}`

export function saveTrainingDraft(draft: TrainingDraft) { Taro.setStorageSync(DRAFT_KEY, draft) }
export function loadTrainingDraft(): TrainingDraft | null { return Taro.getStorageSync(DRAFT_KEY) || null }
export function saveTrainingSession(taskId: string, session: TrainingSession) { Taro.setStorageSync(trainingSessionKey(taskId), session) }
export function loadTrainingSession(taskId: string): TrainingSession | null { return Taro.getStorageSync(trainingSessionKey(taskId)) || null }
export function saveQuestionFeedback(feedback: QuestionFeedback) {
  const all: QuestionFeedback[] = Taro.getStorageSync(FEEDBACK_KEY) || []
  Taro.setStorageSync(FEEDBACK_KEY, [...all.filter(x => !(x.taskId === feedback.taskId && x.questionId === feedback.questionId)), feedback])
}
export function loadQuestionFeedback(taskId: string, questionId: string) {
  const all: QuestionFeedback[] = Taro.getStorageSync(FEEDBACK_KEY) || []
  return all.find(x => x.taskId === taskId && x.questionId === questionId) || null
}

export function createClientRequestId() {
  return `req_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
}
