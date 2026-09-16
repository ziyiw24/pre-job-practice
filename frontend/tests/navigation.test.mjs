import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = path => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8')
const createRoute = '/pages/course/create/index'

test('应用注册独立的题库创建页', () => {
  assert.match(read('src/app.config.ts'), /pages\/course\/create\/index/)
})

test('店长工作台的粘贴生成进入题库创建页', () => {
  assert.ok(read('src/pages/main/home/index.tsx').includes(createRoute))
})

test('题库列表的新建题库进入题库创建页', () => {
  assert.ok(read('src/pages/main/content/index.tsx').includes(createRoute))
})

test('题库创建页包含标题、内容、题量和生成逻辑', () => {
  const page = read('src/pages/course/create/index.tsx')
  for (const contract of ['培训标题', '培训内容', '生成题量', 'createTrainingTask']) {
    assert.ok(page.includes(contract), `missing contract: ${contract}`)
  }
})
