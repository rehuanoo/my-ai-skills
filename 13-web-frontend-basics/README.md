# 13 · Web 前端基础（HTML / CSS / JavaScript 手写练习）

> 从第一个 `<h1>` 到 `async/await`，最后自己写出一个能用的 AI 聊天界面。

## 技术栈

`HTML5` · `CSS3（Flex / 定位 / 选择器）` · `JavaScript（ES6+）` · `DOM / Web API` · `Fetch` · `Promise / async-await` · `BOM` · `localStorage / sessionStorage`

## 目录

| 目录 | 内容 |
|------|------|
| `01.html` | 基础标签与文档结构 |
| `02.input与表单` | 表单控件与提交 |
| `04.层级样式使用` | 选择器优先级、层叠 |
| `05.css盒子与布局` | 盒模型、绝对/相对定位、弹性布局 |
| `07.固定定位` | 视口与 `fixed` 定位 |
| `08.讯飞ai聊天` | AI 聊天界面第一版（静态布局） |
| `11.javascripr基础` | 变量、运算、条件、循环、函数、类 |
| `13.数组` | 数组与对象的常用方法 |
| `14.webapi` / `15.操作元素` | 事件绑定、元素创建、改属性、改样式 |
| `16.调试技巧` | DevTools 断点、动画调试 |
| `17.BOM浏览器对象` | `window`、计时器 |
| `18.this指向` | `this` 绑定的四种场景、本地存储与会话存储 |
| `19.讯飞ai聊天交互` | **最终版**：可交互的 AI 聊天界面 |
| `21.ajax` / `22.promise_async_await` | 传统 Ajax 与 `Promise / async-await` 的写法演进 |

## 运行

纯静态页面，直接双击 `.html` 即可；需要请求接口的页面用本地服务器打开：

```powershell
python -m http.server 5500
# http://127.0.0.1:5500/19.讯飞ai聊天交互/index.html
```

## 实现要点

- **从静态到交互**：`08` 只有布局，`19` 变成能发消息、渲染回复、管理会话的完整界面，能看出一步步迭代的过程。
- **异步演进**：`21.ajax` 用回调，`22` 用 `Promise` 与 `async/await` 重写，对比很直观。
- **存储**：`localStorage` 与 `sessionStorage` 的生命周期差异，配合 `this` 指向的坑一起练。
