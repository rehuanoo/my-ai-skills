<script setup>
// ============================================================
// App.vue —— 用 Fabric.js 制作王楚钦夺冠海报
// ============================================================
// 核心思路：
//   1. 一张 800x1120 的 Fabric 画布，海报的每个元素（背景/照片/文字/
//      装饰）都是画布上的「对象」，可以用鼠标直接拖拽微调；
//   2. 布局逻辑在 src/poster.js（与 Node 预览脚本共用同一份代码），
//      用到 Fabric 的核心能力：线性/径向渐变（Gradient）、图片滤镜
//      （filters：对比度/饱和度）、阴影（Shadow）、描边文字（stroke）、
//      多边形（Polygon）、组合（Group）、位图导出（toDataURL）；
//   3. 「AI 生成海报」：通过 @gradio/client 调本地 Gradio 后端
//      （server/server.py，商汤 LLM 写海报词 + u1.5-lite 画配图），
//      拿到结果后按海报词自动重排 Fabric 海报；
//   4. 「下载海报」= canvas.toDataURL 导出 2 倍分辨率 PNG。
//   ⚠️ fabric v6+ 的 originX/originY 默认是 'center'，poster.js 里
//      统一用 place() 转成左上角定位，否则所有 left/top 都会错位。
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as fabric from 'fabric'
import { Client } from '@gradio/client'
import { buildPoster, POSTER_W, POSTER_H } from './poster.js'

const API_URL = 'http://127.0.0.1:7864'   // server/server.py 的 Gradio 地址

const canvasEl = ref(null)
const exporting = ref(false)
const cnReq = ref('')          // 用户的海报要求（中文）
const aiLoading = ref(false)
const aiMsg = ref('')
let canvas = null
let gradioApp = null           // 缓存已连接的 @gradio/client 实例
let lastImageUrl = null        // 最近一次 AI 生成的配图（data URL）
let lastData = null            // 最近一次 AI 生成的海报词

// ============================================================
// AI 生成：中文要求 → 海报词 + 配图 → 自动排版
// ============================================================
async function aiGenerate() {
  if (aiLoading.value) return
  const req = cnReq.value.trim()
  if (!req) {
    aiMsg.value = '请先输入海报要求'
    return
  }
  aiLoading.value = true
  try {
    aiMsg.value = '连接 Gradio 后端…'
    gradioApp ??= await Client.connect(API_URL)

    aiMsg.value = 'AI 撰写海报词 + 生成配图（约 20~40 秒）…'
    const res = await gradioApp.predict('/generate_poster', [req])
    const [imgOut, copyStr] = res.data
    lastData = JSON.parse(copyStr)

    // 图片转 data URL：避免跨域图片污染画布，导致之后无法导出 PNG
    aiMsg.value = '加载配图…'
    const imgUrl = typeof imgOut === 'string' ? imgOut : imgOut?.url
    const blob = await (await fetch(imgUrl)).blob()
    lastImageUrl = await new Promise((resolve, reject) => {
      const r = new FileReader()
      r.onload = () => resolve(r.result)
      r.onerror = reject
      r.readAsDataURL(blob)
    })

    await rebuild()
    aiMsg.value = '✅ 海报已生成，可直接拖拽微调或下载'
  } catch (e) {
    aiMsg.value = '❌ 生成失败：' + (e?.message || e)
  } finally {
    aiLoading.value = false
  }
}

// ============================================================
// 交互：导出 PNG / 重置版式
// ============================================================
function download() {
  if (!canvas || exporting.value) return
  exporting.value = true
  // multiplier: 2 → 导出 1600x2240 高清图
  const url = canvas.toDataURL({ format: 'png', multiplier: 2 })
  const a = document.createElement('a')
  a.href = url
  a.download = `${lastData?.title || '海报'}.png`
  a.click()
  exporting.value = false
}

async function rebuild() {
  canvas.remove(...canvas.getObjects())
  await buildPoster(fabric, canvas, { imageUrl: lastImageUrl ?? undefined, data: lastData ?? undefined })
}

async function reset() {
  if (!canvas) return
  lastImageUrl = null
  lastData = null
  aiMsg.value = ''
  await rebuild()   // 回到默认王楚钦模板
}

onMounted(async () => {
  canvas = new fabric.Canvas(canvasEl.value, {
    width: POSTER_W,
    height: POSTER_H,
    preserveObjectStacking: true,   // 拖拽时不改变图层顺序
    selectionColor: 'rgba(255,255,255,0.08)',
    selectionBorderColor: '#e02c3f',
  })
  await buildPoster(fabric, canvas)
})

onBeforeUnmount(() => canvas?.dispose())
</script>

<template>
  <main class="studio">
    <header class="studio-head">
      <h1>🏓 王楚钦 · Fabric 海报工坊</h1>
      <p>
        画布里的照片和文字都可以<em>直接拖拽</em>微调排版 —— Fabric 把海报拆成了一个个可交互的对象
      </p>
    </header>

    <!-- AI 生成面板：调 Gradio 后端，自动重排海报 -->
    <section class="ai-panel">
      <input
        v-model="cnReq"
        class="ai-input"
        :disabled="aiLoading"
        placeholder="输入海报要求，例如：给孙颖莎做一张巴黎奥运混双夺冠海报，突出世界第一"
        @keyup.enter="aiGenerate"
      />
      <button class="btn primary" :disabled="aiLoading" @click="aiGenerate">
        {{ aiLoading ? '⏳ 生成中…' : '✨ AI 生成海报' }}
      </button>
      <p v-if="aiMsg" class="ai-msg" :class="{ err: aiMsg.startsWith('❌') }">{{ aiMsg }}</p>
    </section>

    <!-- fabric 会把 canvas 包进 .canvas-container，所以外层只负责居中和发光 -->
    <div class="stage">
      <canvas ref="canvasEl"></canvas>
    </div>

    <div class="toolbar">
      <button class="btn primary" :disabled="exporting" @click="download">⬇️ 下载海报 PNG</button>
      <button class="btn" @click="reset">↺ 重置版式</button>
    </div>

    <footer class="studio-foot">
      Fabric.js 7 · Vue 3 · 照片：2022 成都世乒赛团体赛现场
    </footer>
  </main>
</template>

<style scoped>
.studio {
  min-height: 100vh;
  padding: 28px 16px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}
.studio-head { text-align: center; }
.studio-head h1 {
  margin: 0 0 6px;
  font-size: 26px;
  color: #f3f4f6;
  letter-spacing: 1px;
}
.studio-head p {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
}
.studio-head em {
  font-style: normal;
  color: #ff6b78;
}

.ai-panel {
  width: min(760px, 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.ai-input {
  width: 100%;
  padding: 11px 18px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.05);
  color: #e5e7eb;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.ai-input:focus { border-color: #ff5560; }
.ai-input::placeholder { color: #6b7280; }
.ai-msg {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
}
.ai-msg.err { color: #ff6b78; }

.stage {
  border-radius: 14px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.04);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08), 0 24px 60px rgba(0, 0, 0, 0.55);
  line-height: 0;
}

.toolbar { display: flex; gap: 12px; }
.btn {
  padding: 10px 22px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.06);
  color: #e5e7eb;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn:hover { background: rgba(255, 255, 255, 0.12); }
.btn.primary {
  border-color: transparent;
  background: linear-gradient(90deg, #e02c3f, #ff5560);
  color: #fff;
  font-weight: 600;
}
.btn.primary:hover { filter: brightness(1.1); }
.btn:disabled { opacity: 0.6; cursor: wait; }

.studio-foot {
  font-size: 12px;
  color: #6b7280;
}
</style>
