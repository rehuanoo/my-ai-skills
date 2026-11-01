# -*- coding: utf-8 -*-
"""
01. 认识 tkinter —— 常用功能演示大全
====================================
运行方式：python 01.认识tkinter.py

一个程序演示 tkinter 的核心功能：
  1. 窗口基础：标题 / 尺寸 / 居中 / 关闭确认
  2. 菜单栏 + 状态栏 + 全局快捷键
  3. 基础组件：Label / Button / Entry / Text / Scale / Spinbox / Progressbar
  4. 选择组件：Checkbutton / Radiobutton / Combobox / Listbox
  5. 表格组件：Treeview
  6. 三种布局：pack / grid / place
  7. 文件对话框（桌面端的"文件上传"）：askopenfilename / askopenfilenames / askdirectory / asksaveasfilename
  8. 弹窗与事件：messagebox / simpledialog / colorchooser / Toplevel / bind / 右键菜单 / Canvas
  9. 打包成 exe：PyInstaller（见文件末尾附录注释）

tkinter 是 Python 标准库，无需 pip install。
组件分两套：tk.*（经典）和 ttk.*（主题化、更美观，推荐优先用 ttk）。
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser


# ============================================================
# 1. 主窗口
# ============================================================
root = tk.Tk()
root.title('01. 认识 tkinter —— 常用功能演示')

def center_window(win, w, h):
    """让窗口在屏幕中央显示"""
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f'{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}')

root.update()                      # 先渲染一帧，确保能拿到屏幕尺寸
center_window(root, 960, 640)
root.minsize(820, 560)             # 最小尺寸限制
# root.iconbitmap('app.ico')       # 自定义窗口图标（需要 .ico 文件）

# 数据绑定变量：组件与变量双向联动（改了变量界面自动刷新，反之亦然）
status_var = tk.StringVar(value='就绪')


# ============================================================
# 2. 文件对话框（菜单和"文件"选项卡共用）
# ============================================================
def open_file_dialog(preview_widget=None):
    """打开单个文件；桌面应用的"文件上传"本质上就是选文件 + 读内容"""
    path = filedialog.askopenfilename(
        title='请选择文件',
        filetypes=[('文本/Markdown', '*.txt;*.md'), ('图片', '*.png;*.jpg;*.jpeg'), ('所有文件', '*.*')]
    )
    if not path:                       # 用户点了"取消"，返回空字符串
        return
    status_var.set(f'已选择文件：{path}')
    if preview_widget is not None:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read(5000)  # 只读前 5000 字符，防止大文件卡死
        except UnicodeDecodeError:
            content = '（二进制文件，无法按文本预览）'
        except OSError as e:
            content = f'读取失败：{e}'
        preview_widget.delete('1.0', 'end')
        preview_widget.insert('1.0', content)

def choose_multi_files():
    """一次选择多个文件（返回元组）"""
    paths = filedialog.askopenfilenames(title='可按住 Ctrl 多选')
    if paths:
        status_var.set(f'共选择 {len(paths)} 个文件：' + '；'.join(paths))

def choose_directory():
    """选择文件夹"""
    d = filedialog.askdirectory(title='请选择文件夹')
    if d:
        status_var.set(f'已选择文件夹：{d}')

def save_file_dialog(preview_widget=None):
    """另存为对话框：选定路径后把预览区内容写出去"""
    path = filedialog.asksaveasfilename(
        title='保存为',
        defaultextension='.txt',
        initialfile='导出内容.txt',
        filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')]
    )
    if not path:
        return
    if preview_widget is not None:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(preview_widget.get('1.0', 'end'))
    status_var.set(f'已保存：{path}')


# ============================================================
# 3. 状态栏（先 pack 到底部，后面的主内容才能占满剩余空间）
# ============================================================
ttk.Label(root, textvariable=status_var, relief='sunken', anchor='w', padding=(8, 4)).pack(side='bottom', fill='x')


# ============================================================
# 4. 菜单栏 + 快捷键
# ============================================================
menubar = tk.Menu(root)
menu_file = tk.Menu(menubar, tearoff=0)
menu_file.add_command(label='打开文件...', accelerator='Ctrl+O', command=lambda: open_file_dialog())
menu_file.add_separator()
menu_file.add_command(label='退出', accelerator='Ctrl+Q', command=lambda: on_closing())
menubar.add_cascade(label='文件', menu=menu_file)

menu_help = tk.Menu(menubar, tearoff=0)
menu_help.add_command(label='关于', command=lambda: messagebox.showinfo('关于', 'tkinter 常用功能演示\n课程：PC 桌面 AI 应用开发'))
menubar.add_cascade(label='帮助', menu=menu_help)
root.config(menu=menubar)

root.bind('<Control-o>', lambda e: open_file_dialog())   # 全局快捷键
root.bind('<Control-q>', lambda e: on_closing())


# ============================================================
# 5. 各选项卡内容
# ============================================================
def build_tab_basic(nb):
    """基础组件：Label / Button / Entry / Text / Scale / Spinbox / Progressbar"""
    tab = ttk.Frame(nb, padding=12)
    nb.add(tab, text=' 基础组件 ')
    bold = ('微软雅黑', 12, 'bold')

    # Label：静态文本
    ttk.Label(tab, text='1. Label 标签', font=bold).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 6))
    ttk.Label(tab, text='普通文本标签').grid(row=1, column=0, sticky='w')
    ttk.Label(tab, text='彩色斜体标签', foreground='#0B5FFF', font=('微软雅黑', 10, 'italic')).grid(row=1, column=1, sticky='w', padx=12)

    # Entry：单行输入，配合 StringVar 读写
    ttk.Label(tab, text='2. Entry 单行输入框（回车可提交）', font=bold).grid(row=2, column=0, columnspan=3, sticky='w', pady=(14, 6))
    name_var = tk.StringVar(value='小明')
    entry = ttk.Entry(tab, textvariable=name_var, width=24)
    entry.grid(row=3, column=0, sticky='w')
    ttk.Button(tab, text='读取输入', command=lambda: status_var.set(f'你输入的是：{name_var.get()}')).grid(row=3, column=1, sticky='w', padx=12)
    entry.bind('<Return>', lambda e: status_var.set(f'回车提交：{name_var.get()}'))

    # Text：多行文本。索引 "1.0" = 第1行第0列，"end" = 末尾
    ttk.Label(tab, text='3. Text 多行文本框', font=bold).grid(row=4, column=0, columnspan=3, sticky='w', pady=(14, 6))
    text = tk.Text(tab, width=52, height=5, wrap='word')
    text.grid(row=5, column=0, columnspan=2, sticky='w')
    text.insert('1.0', 'Text 支持多行编辑。\nget("1.0", "end") 取全文；insert("end", s) 追加；delete("1.0", "end") 清空。\n')
    ttk.Button(tab, text='统计字数',
               command=lambda: status_var.set(f'共 {len(text.get("1.0", "end").strip())} 个字符')).grid(row=6, column=0, sticky='w', pady=6)

    # Scale 滑块 + Progressbar 进度条：绑定同一个 IntVar，实现联动
    ttk.Label(tab, text='4. 数值组件（滑块与进度条联动）', font=bold).grid(row=7, column=0, columnspan=3, sticky='w', pady=(14, 6))
    scale_var = tk.IntVar(value=30)
    tk.Scale(tab, from_=0, to=100, orient='horizontal', length=220,
             label='Scale 滑块', variable=scale_var).grid(row=8, column=0, sticky='w')
    ttk.Progressbar(tab, length=220, maximum=100, variable=scale_var).grid(row=8, column=1, sticky='w', padx=12)
    ttk.Spinbox(tab, from_=1, to=10, width=6).grid(row=8, column=2, sticky='w', padx=12)


def build_tab_select(nb):
    """选择组件：Checkbutton / Radiobutton / Combobox / Listbox"""
    tab = ttk.Frame(nb, padding=12)
    nb.add(tab, text=' 选择组件 ')
    bold = ('微软雅黑', 12, 'bold')

    # Checkbutton 复选框：每项一个 IntVar
    ttk.Label(tab, text='1. Checkbutton 复选框', font=bold).grid(row=0, column=0, columnspan=4, sticky='w')
    skills = {}
    for i, name in enumerate(['Python', 'PyTorch', 'LangChain', 'Gradio']):
        var = tk.IntVar(value=0)
        ttk.Checkbutton(tab, text=name, variable=var).grid(row=1, column=i, sticky='w')
        skills[name] = var

    def show_skills():
        chosen = '、'.join(k for k, v in skills.items() if v.get()) or '无'
        status_var.set(f'已选技能：{chosen}')
    ttk.Button(tab, text='查看勾选', command=show_skills).grid(row=2, column=0, sticky='w', pady=4)

    # Radiobutton 单选框：多个按钮共享一个变量，value 互斥
    ttk.Label(tab, text='2. Radiobutton 单选框', font=bold).grid(row=3, column=0, columnspan=4, sticky='w', pady=(14, 6))
    gender = tk.StringVar(value='保密')
    for i, g in enumerate(['男', '女', '保密']):
        ttk.Radiobutton(tab, text=g, value=g, variable=gender,
                        command=lambda: status_var.set(f'选择了：{gender.get()}')).grid(row=4, column=i, sticky='w')

    # Combobox 下拉框
    ttk.Label(tab, text='3. Combobox 下拉框', font=bold).grid(row=5, column=0, columnspan=4, sticky='w', pady=(14, 6))
    combo = ttk.Combobox(tab, values=['Qwen3-0.6B', 'Qwen2.5-7B', 'Llama3.1-8B'], state='readonly', width=24)
    combo.current(0)
    combo.grid(row=6, column=0, sticky='w')
    combo.bind('<<ComboboxSelected>>', lambda e: status_var.set(f'下拉选中：{combo.get()}'))

    # Listbox 列表框：滚动条 + 双击删除 + 多选
    ttk.Label(tab, text='4. Listbox 列表框（支持多选，双击删除）', font=bold).grid(row=7, column=0, columnspan=4, sticky='w', pady=(14, 6))
    listbox = tk.Listbox(tab, height=6, width=34, selectmode='extended')
    for item in ['苹果', '香蕉', '橙子', '西瓜', '葡萄']:
        listbox.insert('end', item)
    listbox.grid(row=8, column=0, rowspan=3, sticky='w')
    sb = ttk.Scrollbar(tab, orient='vertical', command=listbox.yview)
    listbox.config(yscrollcommand=sb.set)
    sb.grid(row=8, column=1, rowspan=3, sticky='ns')

    def del_selected(event=None):
        for i in reversed(listbox.curselection()):   # 必须倒序删除，防止索引错位
            listbox.delete(i)
        status_var.set('已删除选中项')

    def add_item():
        listbox.insert('end', new_item.get())
        status_var.set(f'已添加：{new_item.get()}')

    listbox.bind('<Double-Button-1>', del_selected)
    new_item = tk.StringVar(value='火龙果')
    ttk.Entry(tab, textvariable=new_item, width=16).grid(row=8, column=2, sticky='nw', padx=12)
    ttk.Button(tab, text='添加', command=add_item).grid(row=8, column=3, sticky='nw')
    ttk.Button(tab, text='删除选中', command=del_selected).grid(row=9, column=2, sticky='nw', padx=12, pady=4)


def build_tab_table(nb):
    """Treeview：表格数据展示（桌面应用里最常用的数据组件）"""
    tab = ttk.Frame(nb, padding=12)
    nb.add(tab, text=' 表格 ')

    ttk.Label(tab, text='Treeview 表格（双击行查看详情）', font=('微软雅黑', 12, 'bold')).pack(anchor='w')

    columns = ('name', 'version', 'size')
    tree = ttk.Treeview(tab, columns=columns, show='headings', height=10)
    tree.heading('name', text='模型名称')
    tree.heading('version', text='版本')
    tree.heading('size', text='大小')
    tree.column('name', width=240)
    tree.column('version', width=120, anchor='center')
    tree.column('size', width=120, anchor='center')
    for row in [('Qwen3-0.6B', '2025.4', '0.5 GB'),
                ('bge-m3', 'v1.5', '2.2 GB'),
                ('Whisper large-v3', '2023.11', '3.0 GB'),
                ('XTTS-v2', '2.0', '1.8 GB')]:
        tree.insert('', 'end', values=row)
    tree.pack(fill='both', expand=True, pady=8)

    def on_row_double_click(event):
        sel = tree.selection()
        if sel:
            v = tree.item(sel[0], 'values')
            messagebox.showinfo('行详情', f'模型：{v[0]}\n版本：{v[1]}\n大小：{v[2]}')

    tree.bind('<Double-Button-1>', on_row_double_click)


def build_tab_layout(nb):
    """三种布局管理器对比：pack / grid / place"""
    tab = ttk.Frame(nb, padding=12)
    nb.add(tab, text=' 布局管理 ')

    # pack：按方向堆叠，适合工具栏、状态栏、上下结构
    f1 = ttk.LabelFrame(tab, text='pack：按方向堆叠', padding=10)
    f1.pack(fill='x', pady=6)
    tk.Button(f1, text='side=top, fill=x').pack(side='top', fill='x')
    tk.Button(f1, text='side=left').pack(side='left', padx=4, pady=4)
    tk.Button(f1, text='side=right').pack(side='right', padx=4)

    # grid：行列网格，最常用，适合表单和复杂界面
    f2 = ttk.LabelFrame(tab, text='grid：行列网格（最常用）', padding=10)
    f2.pack(fill='x', pady=6)
    for r in range(3):
        for c in range(3):
            ttk.Label(f2, text=f'({r},{c})', relief='ridge', width=12,
                      anchor='center').grid(row=r, column=c, padx=2, pady=2, sticky='nsew')
    for c in range(3):
        f2.columnconfigure(c, weight=1)   # 列随窗口拉伸

    # place：绝对坐标，精确定位，不适合自适应布局
    f3 = ttk.LabelFrame(tab, text='place：绝对坐标（精确定位用）', padding=10)
    f3.config(height=120)
    f3.pack(fill='x', pady=6)
    f3.pack_propagate(False)
    tk.Button(f3, text='x=20, y=20').place(x=20, y=20)
    tk.Button(f3, text='x=160, y=60').place(x=160, y=60)


def build_tab_file(nb):
    """文件对话框：桌面端的"文件上传/下载" """
    tab = ttk.Frame(nb, padding=12)
    nb.add(tab, text=' 文件对话框 ')

    ttk.Label(tab, text='桌面应用的"文件上传" = 打开文件对话框选文件，再读内容（比如之后发给 AI）',
              font=('微软雅黑', 12, 'bold')).pack(anchor='w')

    preview = tk.Text(tab, wrap='word', height=16)
    preview.insert('1.0', '文件内容预览区……')

    btns = ttk.Frame(tab)
    ttk.Button(btns, text='选择文件并读取', command=lambda: open_file_dialog(preview)).pack(side='left', padx=(0, 8))
    ttk.Button(btns, text='选择多个文件', command=choose_multi_files).pack(side='left', padx=(0, 8))
    ttk.Button(btns, text='选择文件夹', command=choose_directory).pack(side='left', padx=(0, 8))
    ttk.Button(btns, text='另存为', command=lambda: save_file_dialog(preview)).pack(side='left')

    btns.pack(anchor='w', pady=10)
    preview.pack(fill='both', expand=True)


def build_tab_dialog_event(nb):
    """弹窗 + 事件绑定"""
    tab = ttk.Frame(nb, padding=12)
    nb.add(tab, text=' 弹窗与事件 ')

    # 标准弹窗
    f1 = ttk.LabelFrame(tab, text='标准弹窗', padding=10)
    f1.pack(fill='x')
    ttk.Button(f1, text='showinfo', command=lambda: messagebox.showinfo('提示', '这是一条信息')).pack(side='left', padx=4, pady=4)
    ttk.Button(f1, text='showwarning', command=lambda: messagebox.showwarning('警告', '这是一条警告')).pack(side='left', padx=4)
    ttk.Button(f1, text='showerror', command=lambda: messagebox.showerror('错误', '这是一条错误')).pack(side='left', padx=4)
    ttk.Button(f1, text='askyesno 确认框', command=ask_yes_no).pack(side='left', padx=4)
    ttk.Button(f1, text='输入框', command=ask_string).pack(side='left', padx=4)
    ttk.Button(f1, text='选择颜色', command=choose_color).pack(side='left', padx=4)

    # 自定义模态弹窗
    f2 = ttk.LabelFrame(tab, text='自定义弹窗 Toplevel', padding=10)
    f2.pack(fill='x', pady=8)
    ttk.Button(f2, text='打开模态设置窗口', command=open_settings_window).pack(side='left', padx=4)

    # 事件绑定：Canvas 点击画圆 + 右键菜单
    f3 = ttk.LabelFrame(tab, text='事件绑定 bind：左键点画圆，右键弹菜单', padding=10)
    f3.pack(fill='both', expand=True, pady=8)
    canvas = tk.Canvas(f3, bg='white', height=170)
    canvas.pack(fill='both', expand=True)

    def draw_dot(event):
        r = 6
        canvas.create_oval(event.x - r, event.y - r, event.x + r, event.y + r, fill='#0B5FFF', outline='')
        status_var.set(f'画布点击坐标：({event.x}, {event.y})')

    canvas.bind('<Button-1>', draw_dot)

    ctx = tk.Menu(canvas, tearoff=0)
    ctx.add_command(label='清空画布', command=lambda: canvas.delete('all'))
    canvas.bind('<Button-3>', lambda e: ctx.post(e.x_root, e.y_root))   # 右键在鼠标位置弹出菜单


def ask_yes_no():
    ok = messagebox.askyesno('确认', '确定要执行该操作吗？')   # 返回 True / False
    status_var.set(f'你点了：{"是" if ok else "否"}')

def ask_string():
    s = simpledialog.askstring('输入', '请输入你的名字：', parent=root)
    if s:
        status_var.set(f'你好，{s}！')

def choose_color():
    rgb, hex_color = colorchooser.askcolor(title='挑一个颜色')   # 返回 ((r,g,b), '#rrggbb')
    if hex_color:
        status_var.set(f'选中的颜色：{hex_color}  RGB={rgb}')

def open_settings_window():
    win = tk.Toplevel(root)
    win.title('设置')
    win.transient(root)     # 跟随主窗口（主窗口最小化时它也隐藏）
    win.grab_set()          # 模态：不关掉它就无法操作主窗口
    center_window(win, 320, 160)
    ttk.Label(win, text='这是一个模态子窗口\n设置项可以放这里').pack(pady=20)
    ttk.Button(win, text='关闭', command=win.destroy).pack()


# ============================================================
# 6. Notebook 选项卡容器：把上面 6 个功能页装进去
# ============================================================
nb = ttk.Notebook(root)
nb.pack(fill='both', expand=True, padx=10, pady=10)
build_tab_basic(nb)
build_tab_select(nb)
build_tab_table(nb)
build_tab_layout(nb)
build_tab_file(nb)
build_tab_dialog_event(nb)


# ============================================================
# 7. 关闭确认 + 进入事件循环
# ============================================================
def on_closing():
    if messagebox.askokcancel('退出', '确定要退出程序吗？'):
        root.destroy()

root.protocol('WM_DELETE_WINDOW', on_closing)   # 拦截窗口右上角 X
root.mainloop()                                  # 事件循环：程序停在这里等待用户操作


# ============================================================
# 【附录】打包成 exe（PyInstaller）
# ============================================================
# 1. 安装（建议在干净的虚拟环境里打包，体积小）：
#       pip install pyinstaller
#
# 2. 常用命令：
#       pyinstaller -F -w 01.认识tkinter.py
#         -F / --onefile     打成单个 exe（不加则生成文件夹，启动更快）
#         -w / --windowed    不显示黑色控制台窗口（GUI 程序必加）
#       pyinstaller -F -w -i app.ico 01.认识tkinter.py
#         -i                 指定 exe 图标（.ico 格式）
#
# 3. 程序里用到外部资源（图片/配置/模型）时：
#       pyinstaller -F -w --add-data "assets;assets" main.py
#       Windows 用分号分隔 "源目录;打包内目录"，代码里这样读：
#         import sys, os
#         def resource_path(rel):
#             base = getattr(sys, '_MEIPASS', os.path.abspath('.'))
#             return os.path.join(base, rel)
#
# 4. 常见问题：
#     - exe 太大：在干净虚拟环境打包；--exclude-module 排除用不到的库
#     - 杀毒误报：加 --noupx；或改用 nuitka
#     - 中文文件名：支持，但建议先用英文名排障
# 5. 产物在 dist\ 目录；build\ 和 *.spec 是中间文件（.spec 可留存复用配置）
