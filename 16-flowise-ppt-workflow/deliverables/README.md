# 商汤 AI PPT 助手 · 交付说明

## 1. 交付文件

| 文件 | 说明 |
|---|---|
| `AIPptHelper.pptm` | PowerPoint 宏助手。含开始页 4 个按钮、VBA 模块、JSON 解析器 |
| `AI_PPT_示例_人工智能赋能客户服务.pptx` | 实际跑通生成的 4 页示例，每页为 16:9 AI 幻灯片图片 |
| `四页示例预览.png` | 示例 PPT 的 2×2 预览图 |
| `开始页预览.png` | `AIPptHelper.pptm` 开始页截图 |
| `Flowise工作流_智能PPT生成.json` | Flowise 工作流备份（含完整节点代码） |
| `senseTime_PPT_node.js` | Flowise 自定义 JS 节点源码，便于修改后重新粘贴 |
| `modPptAI.bas` | PowerPoint VBA 源码，便于审查/二次开发 |

PowerPoint 路径：`C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE`。

## 2. Flowise 工作流

- 名称：**智能PPT生成（商汤 Kimi-K3 → U1.5 Lite）**
- Flow ID：`5f6f5ff3-22a0-4a52-9ce8-6a5f04ecb349`
- 地址：`http://127.0.0.1:3000`
- 类型：Chatflow，已部署
- 节点：一个 **Custom JS Function** 自定义节点，内部按顺序完成「Kimi 大纲 → U1.5 Lite 逐页生图 → 返回 JSON」

### 模型分工

| 环节 | 模型 | 说明 |
|---|---|---|
| 大纲 | `kimi-k3` | 首选；`temperature=1`（该模型只允许 1） |
| 大纲限流回退 | `glm-5.2` → `deepseek-v4-flash` | 文本模型回退，保证大纲步骤不中断 |
| 页面图片 | `sensenova-u1.5-lite` | `/v1/images/generations`，1536×864、无水印、16:9 |

> **关于“限流时用 U1.5 Lite”**：实测并查阅商汤官方说明后确认，`sensenova-u1.5-lite` 是**文生图模型**，只提供 `/images/generations`，不能作为 Chat Model 生成文字大纲。  
> 因此工作流中 U1.5 Lite 负责**所有页面图片**；Kimi 限流时，大纲自动回退到同为商汤 Token Plan 的文本模型 GLM-5.2 / DeepSeek-V4-Flash。这样既保留了 U1.5 的生图能力，也不会让大纲步骤直接失败。  
> 参考：[SenseNova U1.5 Lite 官方接入说明](https://www.sensetime.com/cn/news/sensenova-u1-5-lite-token-plan-20260911-1741)

### 工作流协议

请求：

```http
POST http://127.0.0.1:3000/api/v1/prediction/5f6f5ff3-22a0-4a52-9ce8-6a5f04ecb349
Content-Type: application/json

{"question":"{\"topic\":\"人工智能赋能客户服务\",\"slideCount\":6,\"outlineOnly\":true}"}
```

三种内部请求：

1. `{"ping":true}` 或 `"__PING__"`：秒级连通性测试，不调用模型。
2. `{"topic":"...","slideCount":6,"outlineOnly":true}`：只生成大纲。
3. `{"topic":"...","slideCount":6,"outline":{...}}`：使用已有大纲，直接逐页生图。

返回的 `slides[]` 中每项包含 `title`、`content`、`layout`、`imageUrl`、`imagePrompt`。  
图片 URL 是商汤临时地址，有效期约 24 小时，PowerPoint 会立即下载并嵌入 PPT。

## 3. PowerPoint 使用方法

1. 双击打开 `AIPptHelper.pptm`，如出现宏安全提示，选择“启用宏”。
2. 开始页有 4 个按钮：
   - **1 生成大纲**：输入主题和页数（3–10），调用 Kimi-K3 生成大纲；弹窗显示每页标题与要点。
   - **2 生成图片 PPT**：按当前大纲调用 U1.5 Lite 逐页生图，下载图片并组装为 16:9 PPT。
   - **3 测试连接**：调用工作流的 ping 接口，秒级检查 Flowise、Flow ID 是否正常。
   - **4 使用说明**：显示模型与使用提示。
3. 第一次点击任一功能按钮时，会自动创建 **“AI PPT 助手”浮动工具栏**（4 个带图标按钮，默认在窗口左上区域）。
   也可以按 `Alt+F8` 运行 `AI_创建工具栏` 手动创建。
4. 生成的 PPT 默认保存在**当前演示文稿所在目录**，文件名形如：
   `人工智能赋能客户服务_AI生成_1027_2210.pptx`。
5. 生成过程中请保持 Flowise 运行，不要关闭。4 页约 1 分钟；6 页约 1.5–2 分钟（取决于商汤接口排队）。

### 按钮/图标

- 4 个按钮图标均从 Icons8 下载（`todo-list`、`artificial-intelligence`、`connected`、`info`）。
- 安装位置：`%APPDATA%\AIWordFlowise\icons\pptOutline.png` 等。
- 开始页按钮的鼠标点击动作为 `ppActionRunMacro`，宏引用已写成 `'AIPptHelper.pptm'!AI_...`，避免同名宏解析错误。

## 4. 实测记录

| 测试 | 结果 |
|---|---|
| Flowise 大纲（Kimi-K3，4 页） | 成功，12.9 秒，`outlineModel=kimi-k3` |
| Flowise 4 页生图 | 成功，53.2 秒，4/4 张 1536×864 PNG |
| Flowise 6 页完整生成 | 成功，89.1 秒，6/6 张；GLM-5.2 大纲回退生效 |
| VBA 端到端自测（含大纲+生图+组装） | 成功，75.2 秒，`ok=4,fail=0`，输出 5.31 MB PPTX |
| 工具栏 | 4 个按钮，`OnAction` 正确指向 4 个宏 |
| 开始页 | 4 个圆角按钮，`Action=8 (ppActionRunMacro)`，宏引用正确 |
| ping | 成功，秒级返回 `ping:true` |

说明：
- VBA 自测时 Kimi 正好遇到瞬时 RPM 限流，工作流自动回退到 `deepseek-v4-flash` 并成功出图；单独测试 Kimi 大纲也成功。回退链路是真实生效的。
- 6 页测试时 Kimi 限流，回退到 `glm-5.2` 生成大纲，6 张图片全部成功。
- 已修正图片提示词中“第 N 页”被模型误画到页面上的问题；当前版本不会再向图片模型传递页码。

## 5. 重新构建

```powershell
# 1) 重新生成 AIPptHelper.pptm（含 VBA 模块）
& 'S:\PythonAILearningCourse\16-flowise-ppt-workflow\PowerPoint-VBA\scripts\build_pptm.ps1'

# 2) 创建开始页（build_pptm.ps1 里的 PowerShell COM Run 调用有重载问题，
#    因此单独用 Python COM 执行）
& 'C:\Users\rehuanoo\AppData\Local\Programs\Python\Python310\python.exe' `
  'S:\PythonAILearningCourse\16-flowise-ppt-workflow\PowerPoint-VBA\scripts\create_start_page.py'
```

构建脚本会把 `src/icons_web/*.png` 安装到 `%APPDATA%\AIWordFlowise\icons\`。  
VBA 源码：`PowerPoint-VBA\src\modPptAI.bas`；JSON 解析器：`JsonConverter.bas`。

## 6. 注意事项

- Flowise 必须已启动：`http://127.0.0.1:3000`。
- API Key 写在 Flowise 自定义节点代码中，仅适合本机/教学环境；不要公开分享该工作流 JSON。
- 商汤 Token Plan 有 RPM/TPM 限制；如果三个文本模型同时 429，等 1–2 分钟后重试即可。
- 图片模型对中文排版已很稳定，但复杂长句仍建议生成后人工检查一遍。
- 若某页图片下载失败，VBA 会自动生成同内容的深色文字页，不会出现缺页；`AI_配图统计()` 会显示 `ok/fail` 数量。
