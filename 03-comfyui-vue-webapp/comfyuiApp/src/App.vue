<script setup>
import { ref, reactive } from 'vue'

const API_BASE = 'http://127.0.0.1:9888'

const form = reactive({
  prompt: '一只可爱的猫, 彩色插画, 高质量',
  negativePrompt: '低质量, 模糊',
  steps: 6,
  cfg: 1.5,
  seed: 42,
  cnStrength: 0.85,
  sketch: null,
})

const loading = ref(false)
const resultImage = ref('')
const errorMsg = ref('')
const showAdvanced = ref(false)
const sketchPreview = ref('')
const fileInput = ref(null)

function onSketchUpload(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    form.sketch = ev.target.result
    sketchPreview.value = ev.target.result
  }
  reader.readAsDataURL(file)
}

function clearSketch() {
  form.sketch = null
  sketchPreview.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function randomSeed() {
  form.seed = Math.floor(Math.random() * 999999999)
}

async function generate() {
  if (!form.prompt.trim()) {
    errorMsg.value = '请输入提示词'
    return
  }
  loading.value = true
  errorMsg.value = ''
  resultImage.value = ''

  try {
    const body = {
      prompt: form.prompt,
      negative_prompt: form.negativePrompt,
      steps: form.steps,
      cfg: form.cfg,
      seed: form.seed,
      cn_strength: form.cnStrength,
      sketch: form.sketch || '',
    }
    const res = await fetch(`${API_BASE}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    if (data.error) {
      errorMsg.value = data.details || data.error
    } else if (data.success) {
      resultImage.value = data.image
    }
  } catch (e) {
    errorMsg.value = '请求失败: ' + e.message + '（请确认API服务已启动）'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="app-container">
    <header class="header">
      <h1>AI 实时绘画</h1>
      <p class="subtitle">输入中文提示词，画一张线稿，AI 帮你上色</p>
    </header>

    <div class="main-content">
      <div class="form-panel">
        <div class="form-group">
          <label class="form-label">提示词（中文）</label>
          <textarea v-model="form.prompt" class="form-textarea" placeholder="例如：一只可爱的猫, 彩色插画, 高质量" rows="3"></textarea>
        </div>

        <div class="form-group">
          <label class="form-label">反向提示词（不想出现的内容）</label>
          <textarea v-model="form.negativePrompt" class="form-textarea neg" placeholder="例如：低质量, 模糊" rows="2"></textarea>
        </div>

        <div class="form-group">
          <label class="form-label">线稿图片（可选，不传用默认）</label>
          <div v-if="sketchPreview" class="sketch-preview">
            <img :src="sketchPreview" alt="线稿预览" />
            <button class="btn-small" @click="clearSketch">移除</button>
          </div>
          <label v-else class="upload-btn" @click="fileInput?.click()">
            上传线稿
            <input ref="fileInput" type="file" accept="image/*" @change="onSketchUpload" hidden />
          </label>
        </div>

        <div class="form-group">
          <label class="form-label">生成步数 <span class="value-tag">{{ form.steps }}</span></label>
          <input type="range" v-model.number="form.steps" min="1" max="20" step="1" class="slider" />
          <div class="slider-hint">步数越少越快（推荐 4-8 步）</div>
        </div>

        <div class="form-group">
          <label class="form-label">提示词引导强度 (CFG) <span class="value-tag">{{ form.cfg.toFixed(1) }}</span></label>
          <input type="range" v-model.number="form.cfg" min="0.5" max="15" step="0.1" class="slider" />
          <div class="slider-hint">越高越贴合提示词（LCM推荐 1.0-2.0）</div>
        </div>

        <div class="advanced-toggle" @click="showAdvanced = !showAdvanced">
          {{ showAdvanced ? '收起' : '展开' }}高级参数
        </div>

        <div v-if="showAdvanced" class="advanced-panel">
          <div class="form-group">
            <label class="form-label">线稿控制强度 <span class="value-tag">{{ form.cnStrength.toFixed(2) }}</span></label>
            <input type="range" v-model.number="form.cnStrength" min="0" max="2" step="0.05" class="slider" />
            <div class="slider-hint">越高越忠实线稿结构</div>
          </div>
          <div class="form-group">
            <label class="form-label">随机种子</label>
            <div class="seed-row">
              <input type="number" v-model.number="form.seed" class="form-input" />
              <button class="btn-small" @click="randomSeed">随机</button>
            </div>
          </div>
        </div>

        <button class="generate-btn" @click="generate" :disabled="loading">
          <span v-if="loading" class="loading-text">
            <span class="spinner"></span> AI 正在绘画...
          </span>
          <span v-else>开始生成</span>
        </button>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
      </div>

      <div class="result-panel">
        <div class="result-header"><h2>生成结果</h2></div>
        <div class="result-area">
          <div v-if="loading" class="loading-area">
            <div class="loading-gif">🎨</div>
            <p>正在生成中，请稍候...</p>
            <p class="loading-hint">通常需要 5-15 秒</p>
          </div>
          <div v-else-if="resultImage" class="result-image">
            <img :src="resultImage" alt="生成结果" />
            <a :href="resultImage" download="ai_art.png" class="download-btn">下载</a>
          </div>
          <div v-else class="empty-area">
            <div class="empty-icon">🖼️</div>
            <p>输入提示词后点击生成</p>
            <p class="empty-hint">支持中文，会自动翻译为英文</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-container { max-width: 1200px; margin: 0 auto; padding: 20px; font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; }
.header { text-align: center; margin-bottom: 24px; }
.header h1 { font-size: 28px; color: #333; margin: 0 0 8px; }
.subtitle { color: #888; font-size: 14px; margin: 0; }
.main-content { display: flex; gap: 24px; }
.form-panel { flex: 1; min-width: 380px; }
.result-panel { flex: 1; min-width: 380px; }
.form-group { margin-bottom: 18px; }
.form-label { display: block; font-size: 14px; font-weight: 600; color: #555; margin-bottom: 6px; }
.form-textarea { width: 100%; padding: 10px 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; font-family: inherit; resize: vertical; box-sizing: border-box; }
.form-textarea:focus { border-color: #6c5ce7; outline: none; }
.form-textarea.neg { border-color: #ffd6d6; }
.slider { width: 100%; -webkit-appearance: none; height: 6px; border-radius: 3px; background: #e0e0e0; outline: none; }
.slider::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px; border-radius: 50%; background: #6c5ce7; cursor: pointer; border: 2px solid #fff; box-shadow: 0 2px 6px rgba(108,92,231,0.4); }
.value-tag { display: inline-block; background: #6c5ce7; color: #fff; font-size: 12px; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
.slider-hint { font-size: 12px; color: #aaa; margin-top: 4px; }
.upload-btn { display: inline-block; padding: 10px 20px; border: 2px dashed #b0b0b0; border-radius: 8px; cursor: pointer; font-size: 14px; color: #888; }
.upload-btn:hover { border-color: #6c5ce7; color: #6c5ce7; }
.sketch-preview { position: relative; border: 2px solid #e0e0e0; border-radius: 8px; overflow: hidden; max-width: 200px; }
.sketch-preview img { width: 100%; display: block; }
.btn-small { padding: 4px 12px; border: none; border-radius: 6px; background: #ff6b6b; color: #fff; font-size: 12px; cursor: pointer; }
.seed-row { display: flex; gap: 8px; align-items: center; }
.form-input { flex: 1; padding: 8px 10px; border: 2px solid #e0e0e0; border-radius: 6px; font-size: 14px; }
.advanced-toggle { text-align: center; color: #6c5ce7; font-size: 13px; cursor: pointer; padding: 8px; margin-bottom: 12px; user-select: none; }
.advanced-panel { padding: 12px; background: #f8f7ff; border-radius: 8px; margin-bottom: 12px; }
.generate-btn { width: 100%; padding: 14px; border: none; border-radius: 10px; background: linear-gradient(135deg, #6c5ce7, #a29bfe); color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.1s, opacity 0.2s; }
.generate-btn:hover:not(:disabled) { transform: scale(1.01); }
.generate-btn:disabled { opacity: 0.7; cursor: not-allowed; }
.loading-text { display: flex; align-items: center; justify-content: center; gap: 8px; }
.spinner { width: 18px; height: 18px; border: 3px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg { margin-top: 12px; padding: 10px 14px; background: #fff0f0; border: 1px solid #ffcccc; border-radius: 8px; color: #c0392b; font-size: 14px; }
.result-panel { background: #fafafa; border-radius: 12px; overflow: hidden; }
.result-header { padding: 16px 20px; border-bottom: 1px solid #eee; }
.result-header h2 { margin: 0; font-size: 18px; color: #555; }
.result-area { min-height: 400px; display: flex; align-items: center; justify-content: center; padding: 20px; }
.loading-area, .empty-area { text-align: center; }
.loading-gif { font-size: 48px; margin-bottom: 12px; }
.loading-area p { color: #888; margin: 4px 0; }
.loading-hint { font-size: 12px; color: #ccc !important; }
.result-image { text-align: center; }
.result-image img { max-width: 100%; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
.download-btn { display: inline-block; margin-top: 12px; padding: 8px 20px; background: #00b894; color: #fff; text-decoration: none; border-radius: 6px; font-size: 14px; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-area p { color: #888; margin: 4px 0; }
.empty-hint { font-size: 12px; color: #ccc !important; }
@media (max-width: 800px) { .main-content { flex-direction: column; } }
</style>