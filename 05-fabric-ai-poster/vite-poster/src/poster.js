// ============================================================
// poster.js —— 海报布局逻辑（浏览器 App.vue 与 Node 预览脚本共用）
// ============================================================
// 设计约定：
//   - 不直接 import fabric！浏览器与 Node 的构建入口不同
//     （浏览器 import 'fabric'，Node 用 'fabric/node'），
//     所以 buildPoster(fabric, canvas, ...) 由调用方传入对应实例。
//   - fabric v6+ 的 originX/originY 默认是 'center'！所有 left/top
//     必须配合 place() 显式转成「左上角定位」，否则整体错位。
//   - 文案数据 data 可由 Gradio 后端生成传入（AI 海报），缺省用
//     DEFAULT_DATA（王楚钦模板）；字号按文本长度自适应，避免溢出。
export const POSTER_W = 800
export const POSTER_H = 1120
export const IMG_URL = '/imgs/wcq.png'

// 默认海报词（王楚钦夺冠模板）。points 每项：label 小分类 / value 亮点 / sub 可选金色小字
export const DEFAULT_DATA = {
  title: '王楚钦',
  titleEn: 'WANG CHUQIN',
  tagline: '左手横拍 · 快攻结合弧圈',
  points: [
    { label: '男单世界排名', value: 'NO.1', sub: '世界第一' },
    { label: '2024 巴黎奥运会', value: '混双 · 男团 双金' },
    { label: '2023 德班世乒赛', value: '男双 · 混双 冠军' },
  ],
  footer: '2022 成都世乒赛团体赛 · 决赛夺冠之夜',
}

// 字体栈：中文用微软雅黑，英文标题用 Arial Black / Impact（海报感更强）
export const CN = "'Microsoft YaHei', 'SimHei', sans-serif"
const BLACK = "'Arial Black', 'Arial', sans-serif"
const IMPACT = "'Impact', 'Arial Black', sans-serif"

const RED = '#e02c3f'
const GOLD = '#e8c15a'
const WHITE = '#f5f6fa'

// 左栏版心：x 52 → 照片左缘 320，再留 24 间隙
const COL_X = 52
const COL_W = 320 - 52 - 24     // 244

// 统一「左上角定位」：fabric v6+ 默认 origin 是 center，必须显式改回
const place = (o, left, top) => o.set({ originX: 'left', originY: 'top', left, top })

// 装饰元素锁定：不允许拖拽/选中（背景和修饰不该被用户挪走）
const lock = o => Object.assign(o, { selectable: false, evented: false, hoverCursor: 'default' })

export async function buildPoster(fabric, canvas, { imageUrl = IMG_URL, data = {} } = {}) {
  // 图片加载：浏览器走 fromURL；Node 预览环境回退 util.loadImage
  async function loadImage(url) {
    try {
      return await fabric.FabricImage.fromURL(url, { crossOrigin: 'anonymous' })
    } catch {
      const el = await fabric.util.loadImage(url)
      return new fabric.FabricImage(el)
    }
  }

  // 合并文案：传入 data 里有的字段覆盖默认值
  const d = { ...DEFAULT_DATA, ...data }
  d.points = (d.points || []).slice(0, 3)

  // ---------- 自适应字号：防止 AI 生成的文案溢出版心 ----------
  const titleFs = Math.min(90, Math.floor(272 / Math.max(d.title.length, 1)))
  // 英文副标题：charSpacing 200 时每字符约 0.82em 宽
  const enFs = d.titleEn ? Math.min(21, Math.floor(COL_W / (d.titleEn.length * 0.82))) : 0
  const tagFs = Math.min(14, Math.floor((COL_W - 40) / Math.max(d.tagline.length, 1)))
  const chipW = Math.min(COL_W, Math.max(120, d.tagline.length * tagFs + 40))
  // 成就大字：纯拉丁短文本（如 NO.1）给特大号，其余按长度收敛
  const valueFs = v =>
    v.length <= 4 && !/[^\x00-\x7F]/.test(v) ? 44 : Math.min(28, Math.floor((COL_W - 8) / v.length))

  canvas.backgroundColor = '#0a0c1e'

  // ---------- 1. 背景：深蓝紫对角渐变（呼应场馆灯光）+ 径向暗角 ----------
  const bg = place(new fabric.Rect({ width: POSTER_W, height: POSTER_H }), 0, 0)
  bg.set('fill', new fabric.Gradient({
    type: 'linear',
    gradientUnits: 'percentage',
    coords: { x1: 0, y1: 0, x2: 1, y2: 1 },
    colorStops: [
      { offset: 0, color: '#0a0c1e' },
      { offset: 0.52, color: '#191036' },
      { offset: 1, color: '#451540' },
    ],
  }))
  const vignette = place(new fabric.Rect({ width: POSTER_W, height: POSTER_H }), 0, 0)
  vignette.set('fill', new fabric.Gradient({
    type: 'radial',
    gradientUnits: 'percentage',
    coords: { x1: 0.5, y1: 0.42, r1: 0, x2: 0.5, y2: 0.42, r2: 0.85 },
    colorStops: [
      { offset: 0, color: 'rgba(0,0,0,0)' },
      { offset: 1, color: 'rgba(4,5,14,0.55)' },
    ],
  }))
  canvas.add(lock(bg), lock(vignette))

  // ---------- 2. 顶部装饰：中国红斜切 + 描边圆环 ----------
  canvas.add(
    lock(place(new fabric.Polygon(
      [{ x: 0, y: 0 }, { x: 144, y: 0 }, { x: 144, y: 86 }],
      { fill: RED, opacity: 0.92 },
    ), 656, 0)),
    lock(place(new fabric.Circle({
      radius: 190, fill: '', stroke: 'rgba(255,75,90,0.35)', strokeWidth: 2,
    }), 436, -86)),
    lock(place(new fabric.Circle({
      radius: 34, fill: '', stroke: 'rgba(232,193,90,0.4)', strokeWidth: 1.5,
      strokeDashArray: [4, 5],
    }), 246, 60)),
  )

  // ---------- 3. 底部 CHAMPION 描边大字（玻璃感水印） ----------
  canvas.add(lock(place(new fabric.Text('CHAMPION', {
    fontFamily: IMPACT, fontSize: 88, charSpacing: 250,
    fill: 'rgba(0,0,0,0)', stroke: 'rgba(255,255,255,0.10)', strokeWidth: 1.5,
  }), 48, 902)))

  // ---------- 4. 照片：红衬框 + 投影 + 滤镜 ----------
  const photo = await loadImage(imageUrl)
  photo.set({ scaleX: 780 / photo.height, scaleY: 780 / photo.height })
  const pw = photo.width * photo.scaleX            // 缩放后的实测宽
  photo.shadow = new fabric.Shadow({ color: 'rgba(0,0,0,0.55)', blur: 40, offsetY: 16 })
  // 滤镜：轻微提对比 + 提饱和，让主体更出片
  photo.filters.push(
    new fabric.filters.Contrast({ contrast: 0.06 }),
    new fabric.filters.Saturation({ saturation: 0.15 }),
  )
  photo.applyFilters()
  place(photo, 320, 120)

  // 红色衬框在照片下层，错位 18px 露出右下角，形成「双层相框」效果
  const frame = place(new fabric.Rect({ width: pw, height: 780, fill: RED }), 338, 138)
  canvas.add(frame, photo)

  // ---------- 5. 左栏：标题区（左边缘统一 x=52） ----------
  canvas.add(
    lock(place(new fabric.Rect({ width: 46, height: 6, fill: RED }), 52, 86)),
    lock(place(new fabric.Text('CHINA TABLE TENNIS TEAM', {
      fontFamily: BLACK, fontSize: 13, charSpacing: 220, fill: GOLD,
    }), 52, 106)),
    place(new fabric.Text(d.title, {
      fontFamily: CN, fontSize: titleFs, fontWeight: 900, fill: WHITE,
    }), 48, 134),
  )
  if (d.titleEn) {
    canvas.add(place(new fabric.Text(d.titleEn, {
      fontFamily: BLACK, fontSize: enFs, charSpacing: 200, fill: '#ff5560',
    }), 52, 252))
  }

  // 标签语「胶囊」：圆角矩形 + Textbox 文字水平垂直居中
  if (d.tagline) {
    canvas.add(
      lock(place(new fabric.Rect({
        width: chipW, height: 34, rx: 17, ry: 17,
        fill: 'rgba(255,255,255,0.07)', stroke: 'rgba(255,255,255,0.22)', strokeWidth: 1,
      }), 52, 296)),
      lock(place(new fabric.Textbox(d.tagline, {
        width: chipW, textAlign: 'center',
        fontFamily: CN, fontSize: tagFs, fill: '#c9cede',
        lineHeight: 34 / tagFs,       // 行高撑满胶囊高度 → 垂直居中
      }), 52, 296)),
    )
  }

  // ---------- 6. 左栏：成就列表（3 个固定槽位：366 / 474 / 570） ----------
  const slots = [
    { labelTop: 366, valueTop: 384 },
    { labelTop: 474, valueTop: 494 },
    { labelTop: 570, valueTop: 590 },
  ]
  const dividerTops = [452, 548]
  const label = text => new fabric.Text(text, {
    fontFamily: CN, fontSize: 13, charSpacing: 150, fill: '#8f95ab',
  })

  d.points.forEach((p, i) => {
    const { labelTop, valueTop } = slots[i]
    const value = place(new fabric.Text(p.value, {
      fontFamily: CN, fontSize: valueFs(p.value), fontWeight: 900, fill: WHITE,
    }), 50, valueTop)
    canvas.add(place(label(p.label), 52, labelTop), value)
    // 可选金色小字：紧跟 value 实测宽度之后
    if (p.sub) {
      canvas.add(place(new fabric.Text(p.sub, {
        fontFamily: CN, fontSize: 15, charSpacing: 100, fill: GOLD,
      }), value.left + value.width + 16, valueTop + 16))
    }
    if (i < d.points.length - 1 && dividerTops[i] !== undefined) {
      canvas.add(lock(place(
        new fabric.Rect({ width: COL_W, height: 1, fill: 'rgba(255,255,255,0.14)' }), 52, dividerTops[i],
      )))
    }
  })

  // ---------- 7. 半调网点装饰（波普风角落点缀） ----------
  const dots = []
  for (let r = 0; r < 5; r++)
    for (let c = 0; c < 6; c++)
      dots.push(new fabric.Circle({ left: c * 20, top: r * 20, radius: 2.8, fill: 'rgba(255,255,255,0.16)' }))
  canvas.add(lock(place(new fabric.Group(dots), 52, 686)))

  // ---------- 8. 页脚信息条 ----------
  canvas.add(
    lock(place(new fabric.Rect({ width: POSTER_W - 104, height: 1, fill: 'rgba(255,255,255,0.14)' }), 52, 1010)),
    lock(place(new fabric.Rect({ width: 64, height: 3, fill: RED }), 52, 1009)),
    place(new fabric.Text(d.footer, {
      fontFamily: CN, fontSize: 15, fill: '#aeb3c7',
    }), 52, 1032),
    place(new fabric.Textbox('荣耀时刻 · GLORY', {
      width: POSTER_W - 380 - 52, textAlign: 'right',
      fontFamily: CN, fontSize: 13, charSpacing: 250, fill: GOLD,
    }), 380, 1034),
  )

  // ---------- 9. 内边框收尾（细金线，让画面更「装裱」） ----------
  canvas.add(lock(place(new fabric.Rect({
    width: POSTER_W - 52, height: POSTER_H - 52,
    fill: '', stroke: 'rgba(232,193,90,0.25)', strokeWidth: 1.5,
  }), 26, 26)))

  canvas.requestRenderAll()
}
