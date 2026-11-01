# 06 · LangGraph 多智能体协作

> 从「一个会调工具的智能体」到「主持人 + 多位明星嘉宾的圆桌综艺」，用状态图把多智能体编排讲清楚。

## 技术栈

`LangGraph (StateGraph)` · `transformers`（本地 Qwen1.5-1.8B）· 商汤 SenseNova API · `SearXNG`（本地搜索）· `wttr.in`（免费天气）

## 四个 Notebook

| 文件 | 内容 |
|------|------|
| `01.LangGraph初识.ipynb` | State / Node / Edge 基本概念，第一个可运行图 |
| `02.LangGraph实现智能体.ipynb` | 单智能体：few-shot 路由（天气 / 搜索 / 直接回答）+ 工具节点 + 条件边 |
| `03.LangGraph自动生成段子.ipynb` | 双节点闭环：写段子 → 分析评分 → 不合格回炉 |
| `04.LangGraph创建多个智能体扮演明星做综艺.ipynb` | 多智能体：主持人开场 → 嘉宾依次发言 → 主持人复盘追问 → 总结，输出完整讨论记录 |

## 目录结构

```
06-langgraph-multi-agent/
├── 01.LangGraph初识.ipynb
├── 02.LangGraph实现智能体.ipynb
├── 03.LangGraph自动生成段子.ipynb
├── 04.LangGraph创建多个智能体扮演明星做综艺.ipynb
├── 段子.txt              # 03 的输出
├── 段子分析.txt           # 03 的输出
└── 综艺讨论记录.txt       # 04 的输出（可直接看效果）
```

## 环境要求

- 本地模型：`Qwen1.5-1.8B`（02 用），路径写在 Notebook 里，改成自己的即可
- 本地搜索：SearXNG 跑在 `localhost:6688`（国内网络下需显式指定 `engines=bilibili,sogou`）
- API：`$env:SENSENOVA_API_KEY`

## 实现要点

- **不用现成的 Agent 封装**：节点、条件边、状态结构全部手写，把「图是怎么跑起来的」讲透。
- **小模型兜底**：1.8B 的 base 模型经常不遵守输出格式，所以路由节点在 LLM 判断之外还加了一层关键词规则兜底。
- **限流处理**：商汤 API 有 TPM 限制，约 5 次连续调用就会 429，代码里做了延迟 + 等 60 秒重试 + `reasoning_content` 兜底。
- **结果落盘**：每轮的讨论记录实时写入 txt，跑完可以直接读，便于调试多轮状态。
