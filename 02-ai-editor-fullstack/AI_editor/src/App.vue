<script setup>
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { marked } from 'marked'
import { Client } from '@gradio/client'   // Gradio JS 客户端：调用 01-llm-knowledge-workspace 工作台的 API

// 开启 GFM（表格/删除线/任务列表）+ 单换行转 <br>
marked.setOptions({ gfm: true, breaks: true })

const mdText = ref('')

// 实时转换：左侧输入一变，右侧 HTML 自动更新
const htmlOutput = computed(() => marked.parse(mdText.value))

// 底部状态栏统计
const stats = computed(() => {
  const text = mdText.value
  return {
    chars: text.length,
    lines: text ? text.split('\n').length : 0,
  }
})

// 载入本地 .md 文件：beforeUpload 返回 false 阻止 a-upload 默认上传行为
function loadFile(file) {
  const reader = new FileReader()
  reader.onload = (e) => {
    mdText.value = e.target.result
    message.success(`已载入文件：${file.name}`)
  }
  reader.onerror = () => message.error('文件读取失败')
  reader.readAsText(file, 'utf-8')
  return false
}

// 载入内置示例
function loadDemo() {
  mdText.value = DEMO
  message.success('已载入示例')
}

// 清空
function clearAll() {
  mdText.value = ''
}

// ---------- AI 功能：调用 01-llm-knowledge-workspace 工作台（Gradio）的商汤付费模型 ----------
// 连接信息：Gradio 开了登录验证，账号在 01-llm-knowledge-workspace/db/database.db 的 user 表
const GRADIO_URL = 'http://127.0.0.1:7860'
const GRADIO_AUTH = ['admin', '123456']

let gradioClient = null   // 连接一次，全局复用（避免每次点击都重新握手）

async function getClient() {
  if (!gradioClient) {
    gradioClient = await Client.connect(GRADIO_URL, { auth: GRADIO_AUTH })
  }
  return gradioClient
}

// 统一错误提示：服务没启动 / 登录失败 / 模型调用失败
function showError(e) {
  message.error(
    e.message.includes('Failed to fetch') || e.message.includes('connect')
      ? '无法连接 01-llm-knowledge-workspace 的 Gradio 服务，请先启动 01-llm-knowledge-workspace/server.py'
      : `调用失败：${e.message}`
  )
}

// ✍️ 续写：把续写片段追加到当前文档结尾
const continuing = ref(false)

async function continueText() {
  if (!mdText.value.trim()) {
    message.warning('内容为空，无法续写')
    return
  }
  continuing.value = true
  try {
    const client = await getClient()
    const result = await client.predict('/continue_markdown', { text: mdText.value })
    mdText.value += '\n\n' + result.data[0]   // 追加续写内容，右侧预览自动更新
    message.success('✍️ 续写完成，已追加到文档结尾')
  } catch (e) {
    showError(e)
  } finally {
    continuing.value = false
  }
}

// ✨ 润色：润色后的全文回填输入框
const polishing = ref(false)

async function polishText() {
  if (!mdText.value.trim()) {
    message.warning('内容为空，无需润色')
    return
  }
  polishing.value = true
  try {
    const client = await getClient()
    const result = await client.predict('/polish_markdown', { text: mdText.value })
    mdText.value = result.data[0]   // 回填润色全文，右侧预览自动更新
    message.success('✨ AI 润色完成')
  } catch (e) {
    showError(e)
  } finally {
    polishing.value = false
  }
}

// 📌 生成 5 个标题：结果用弹窗（Modal）展示
const titling = ref(false)
const titlesOpen = ref(false)
const titles = ref([])

async function genTitles() {
  if (!mdText.value.trim()) {
    message.warning('内容为空，无法生成标题')
    return
  }
  titling.value = true
  try {
    const client = await getClient()
    const result = await client.predict('/gen_titles', { text: mdText.value })
    titles.value = result.data[0]   // gr.JSON 输出 → 这里直接是数组
    titlesOpen.value = true         // 打开弹窗
    message.success('📌 已生成 5 个备选标题')
  } catch (e) {
    showError(e)
  } finally {
    titling.value = false
  }
}

// 复制弹窗里的某个标题
async function copyTitle(t) {
  await navigator.clipboard.writeText(t)
  message.success(`已复制：${t}`)
}

// 复制 HTML 源码到剪贴板
async function copyHtml() {
  if (!htmlOutput.value) {
    message.warning('内容为空，无需复制')
    return
  }
  await navigator.clipboard.writeText(htmlOutput.value)
  message.success('HTML 源码已复制到剪贴板')
}

// 把转换结果下载为 .html 文件
function downloadHtml() {
  if (!htmlOutput.value) {
    message.warning('内容为空，无法下载')
    return
  }
  // 套一层完整 HTML 骨架 + 基础样式，下载后双击打开即可看
  const full = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Markdown 导出</title>
<style>
  body { max-width: 800px; margin: 40px auto; padding: 0 20px;
         font-family: system-ui, sans-serif; line-height: 1.7; color: #333; }
  pre { background: #f6f8fa; padding: 12px; border-radius: 6px; overflow: auto; }
  code { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; } th, td { border: 1px solid #ccc; padding: 6px 12px; }
  blockquote { border-left: 4px solid #1677ff; margin: 0; padding: 4px 16px; color: #666; background: #f9f9f9; }
</style>
</head>
<body>
${htmlOutput.value}
</body>
</html>`
  const blob = new Blob([full], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'markdown-export.html'
  a.click()
  URL.revokeObjectURL(url)
  message.success('已开始下载 markdown-export.html')
}

// 内置示例
const DEMO = `# Markdown 转 HTML 工具

在左侧编辑，右侧**实时预览**。

## 支持的语法

- **加粗**、*斜体*、~~删除线~~、\`行内代码\`
- [链接](https://vite.dev/) 与图片
- 表格、代码块、引用、任务列表

| 语法 | 效果 |
| ---- | ---- |
| \`# 标题\` | 一级标题 |
| \`- 列表\` | 无序列表 |
| \`> 引用\` | 引用块 |

### 代码块

\`\`\`python
def hello():
    print("Hello, Markdown!")
\`\`\`

### 任务列表

- [x] 载入文件
- [x] 实时转换
- [ ] 导出 HTML

> 提示：点击右上角「载入文件」可以打开本地 .md 文件，转换结果可复制或下载。
`
</script>

<template>
  <div class="page">
    <!-- 顶部：标题 + 工具栏 -->
    <header class="topbar">
      <h1 class="title">📝 Markdown 转 HTML 工具</h1>
      <a-space>
        <a-upload :before-upload="loadFile" accept=".md,.markdown,.txt" :show-upload-list="false">
          <a-button type="primary">📂 载入文件</a-button>
        </a-upload>
        <a-button @click="loadDemo">示例</a-button>
        <a-button :loading="continuing" @click="continueText">✍️ AI 续写</a-button>
        <a-button type="primary" :loading="polishing" @click="polishText">
          {{ polishing ? '润色中…' : '✨ AI 润色' }}
        </a-button>
        <a-button :loading="titling" @click="genTitles">📌 生成 5 个标题</a-button>
        <a-button @click="copyHtml">复制 HTML</a-button>
        <a-button @click="downloadHtml">下载 .html</a-button>
        <a-button danger @click="clearAll">清空</a-button>
      </a-space>
    </header>

    <!-- 主体：左输入 / 右预览 -->
    <main class="editor">
      <section class="pane">
        <div class="pane-title">Markdown 输入</div>
        <a-textarea
          v-model:value="mdText"
          placeholder="在此输入或粘贴 Markdown 文本……&#10;也可以点击右上角「载入文件」打开本地 .md 文件"
          class="input-area"
        />
        <div class="status">共 {{ stats.chars }} 字符 · {{ stats.lines }} 行</div>
      </section>

      <section class="pane">
        <div class="pane-title">HTML 预览</div>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="preview markdown-body" v-html="htmlOutput"></div>
      </section>
    </main>

    <!-- 标题弹窗：展示 AI 生成的 5 个备选标题 -->
    <a-modal v-model:open="titlesOpen" title="📌 AI 生成的 5 个备选标题" :footer="null" width="560px">
      <a-list :data-source="titles" bordered>
        <template #renderItem="{ item, index }">
          <a-list-item>
            <span class="title-item">{{ index + 1 }}. {{ item }}</span>
            <template #actions>
              <a-button type="link" size="small" @click="copyTitle(item)">复制</a-button>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </a-modal>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
}

.title {
  margin: 0;
  font-size: 18px;
}

.editor {
  display: flex;
  flex: 1;
  gap: 12px;
  padding: 12px;
  min-height: 0;
}

.pane {
  display: flex;
  flex-direction: column;
  flex: 1;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  overflow: hidden;
  min-width: 0;
}

.pane-title {
  padding: 8px 16px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.input-area {
  flex: 1;
  resize: none;
  border: none;
  box-shadow: none !important;
  padding: 16px;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.7;
}

/* 覆盖 ant textarea 默认边框：无边框填满面板 */
.input-area.ant-input {
  height: 100%;
}

.status {
  padding: 6px 16px;
  font-size: 12px;
  color: #999;
  border-top: 1px solid #f0f0f0;
}

.preview {
  flex: 1;
  overflow: auto;
  padding: 20px 24px;
}

/* 预览区 Markdown 基础样式（v-html 不会带 scoped 属性，用 :deep 穿透） */
.markdown-body :deep(h1),
.markdown-body :deep(h2) {
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}
.markdown-body :deep(pre) {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
}
.markdown-body :deep(code) {
  background: #f0f0f0;
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 13px;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}
.markdown-body :deep(blockquote) {
  border-left: 4px solid #1677ff;
  margin: 8px 0;
  padding: 4px 16px;
  color: #666;
  background: #f9f9f9;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #ccc;
  padding: 6px 12px;
}
.markdown-body :deep(img) {
  max-width: 100%;
}

/* 弹窗里的标题文字 */
.title-item {
  font-size: 15px;
}
</style>
