# 16 · Flowise + PowerPoint VBA：AI 自动生成 PPT

> 用低代码平台编排 LLM 工作流，产出的结构化 JSON 直接喂给 PowerPoint 加载项，一键排出一套 PPT。

## 技术栈

`Flowise`（低代码 LLM 编排）· 自定义 JS Function 节点 · `SenseNova`（文案 + 文生图）· `PowerPoint VBA`（`modPptAI.bas`）· `python-pptx` 思路

## 工作流

```
用户在 PowerPoint 里输入「主题 + 页数」
   ↓ VBA 调用 Flowise 的 /api/v1/prediction/<flowId>
   ↓ Flowise：自定义 JS 节点 → 商汤 LLM 输出严格 JSON（标题/要点/配图提示词）
   ↓ 文生图模型按页生成配图
   ↓ VBA 按 JSON 自动排版：母版、标题、要点、图片、配色
   ↓ 得到一套可继续编辑的 PPT
```

## 目录结构

```
16-flowise-ppt-workflow/
├── deliverables/
│   ├── Flowise工作流_智能PPT生成.json   # 可直接导入 Flowise 的工作流
│   ├── senseTime_PPT_node.js            # 自定义 Function 节点源码
│   ├── modPptAI.bas                     # PowerPoint VBA 加载项源码
│   ├── AIPptHelper.pptm                 # 打包好的加载项（可直接打开）
│   ├── 四页示例预览.png / 开始页预览.png  # 效果截图
│   └── README.md                        # 原始交付说明
├── workflow/
│   ├── flow_export.json                 # 工作流导出备份
│   └── sensetime_ppt_node.js
├── scripts/
│   ├── build_flow.py                    # 用 API 批量创建工作流
│   └── create_ppt_flow.py               # 直接写 Flowise 的 SQLite 建流
├── 知识库_课程介绍.txt
├── AI文档助手-使用说明.docx
└── 启动Flowise.cmd
```

## 运行

```powershell
# 1) 启动 Flowise（本地 3000 端口），导入 deliverables 里的工作流 JSON
# 2) 在 PowerPoint 里加载 AIPptHelper.pptm（信任中心需允许宏）
# 3) 填主题与页数，点生成
```

重建工作流（可选）：

```powershell
$env:FLOWISE_API_KEY = "你的 Flowise API Key"
$env:SENSENOVA_API_KEY = "你的 Key"
$env:FLOWISE_DB = "你的Flowise目录\.flowise\database\database.sqlite"
python scripts/build_flow.py
```

## 实现要点

- **强制 JSON**：LLM 节点用系统提示词锁死输出格式，VBA 侧再用正则兜底，避免解析崩溃。
- **两种建流方式**：`build_flow.py` 走 HTTP API（通用），`create_ppt_flow.py` 直接操作 Flowise 的 SQLite（绕开 API 限制），两种都留了。
- **VBA 排版**：`modPptAI.bas` 里处理了母版继承、文本框自适应、图片裁切与占位，避免生成出来「字溢出、图变形」。
- **Office 自动化**：这是少见的把 LLM 接到 Office 插件里的实践，交付物里有可直接双击体验的 `.pptm`。
