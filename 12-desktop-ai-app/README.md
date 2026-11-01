# 12 · 桌面应用开发基础（tkinter）

> 一个文件把 tkinter 的常用组件、三种布局、文件对话框和打包方式全部演示一遍。

## 技术栈

`tkinter / ttk`（Python 标准库，无需安装）· `PyInstaller`（打包）

## 内容

`01.认识tkinter.py`（400 余行）按九个小节组织：

1. 窗口基础：标题 / 尺寸 / 居中 / 关闭确认
2. 菜单栏 + 状态栏 + 全局快捷键
3. 基础组件：`Label` `Button` `Entry` `Text` `Scale` `Spinbox` `Progressbar`
4. 选择组件：`Checkbutton` `Radiobutton` `Combobox` `Listbox`
5. 表格组件：`Treeview`
6. 三种布局：`pack` / `grid` / `place` 的适用场景对比
7. 文件对话框 `askopenfilename` / `askdirectory` / `asksaveasfilename`
8. 弹窗与事件：`messagebox` `simpledialog` `colorchooser` `Toplevel` `bind` 右键菜单 `Canvas`
9. 打包成 exe：`PyInstaller` 配置（见 `01.认识tkinter.spec`）

## 运行

```powershell
python 01.认识tkinter.py

# 打包成单文件 exe
pyinstaller 01.认识tkinter.spec
```

## 实现要点

- **组件两套**：`tk.*` 经典组件与 `ttk.*` 主题化组件的差异，代码里统一推荐 `ttk`。
- **变量绑定**：`StringVar` / `IntVar` 与组件的双向联动，避免手动 `get`/`set`。
- **居中计算**：先 `update()` 渲染一帧再读屏幕尺寸，否则拿不到真实宽高。
- **打包踩坑**：`spec` 文件里记录了资源路径与 `--onefile` 的注意事项。
