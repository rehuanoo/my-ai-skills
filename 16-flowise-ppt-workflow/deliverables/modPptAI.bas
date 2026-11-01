Attribute VB_Name = "modPptAI"
Option Explicit

'=====================================================================
' AI PPT 助手 —— PowerPoint 调用 Flowise 智能 PPT 工作流
'
' 工作流：智能PPT生成（商汤 Kimi-K3 → U1.5 Lite）
'   1) outlineOnly=true  ：Kimi-K3 生成 JSON 大纲（限流自动回退文本模型）
'   2) outline=<大纲>    ：U1.5 Lite 按大纲逐页生成 16:9 幻灯片图片
'   3) ping             ：秒级连通性测试，不调用大模型
'
' 接口：POST http://127.0.0.1:3000/api/v1/prediction/{flowId}
' 请求：{"question":"<内部 JSON 字符串>"}
' 返回：{success, title, outline, slides:[{title,content,imageUrl}], meta}
'
' 依赖：JsonConverter.bas（JSON 解析/序列化）
'=====================================================================

Public Const DEFAULT_SERVER As String = "http://127.0.0.1:3000/api/v1/prediction/"
Public Const DEFAULT_FLOW_ID As String = "5f6f5ff3-22a0-4a52-9ce8-6a5f04ecb349"
Public Const PRIMARY_MODEL As String = "kimi-k3"
Public Const FALLBACK_MODEL As String = "glm-5.2"
Public Const IMAGE_MODEL As String = "sensenova-u1.5-lite"
Public Const FLOW_NAME As String = "智能PPT生成（商汤 Kimi-K3 → U1.5 Lite）"

Private Const CFG_DIR As String = "AIWordFlowise"
Private Const ICON_DIR As String = "icons"
Private Const IMG_DIR As String = "ppt_ai_imgs"
Private Const APP_TITLE As String = "AI PPT 助手"

Private gBusy As Boolean
Private gTip As String
Private gLastError As String
Private gSilent As Boolean
Private gImgOk As Long
Private gImgFail As Long

Private gTopic As String
Private gSlideCount As Long
Private gOutline As Object
Private gOutlineModel As String
Private gLastPpt As String

'=====================================================================
'  一、基础状态
'=====================================================================
Private Sub SetTip(ByVal msg As String)
    gTip = msg
End Sub

Public Function AI_当前进度() As String
    AI_当前进度 = gTip
End Function

Public Function AI_最后错误() As String
    AI_最后错误 = gLastError
End Function

Public Function AI_配图统计() As String
    AI_配图统计 = "ok=" & gImgOk & ",fail=" & gImgFail
End Function

Public Function AI_最后PPT() As String
    AI_最后PPT = gLastPpt
End Function

Public Sub AI_静默模式(ByVal onOff As Boolean)
    gSilent = onOff
    gLastError = ""
End Sub

Public Sub AI_静默开()
    AI_静默模式 True
End Sub

Public Sub AI_静默关()
    AI_静默模式 False
End Sub

Private Sub Warn(ByVal msg As String)
    gLastError = msg
    If Not gSilent Then MsgBox msg, vbCritical, APP_TITLE
End Sub

Private Sub Info(ByVal msg As String)
    If Not gSilent Then MsgBox msg, vbInformation, APP_TITLE
End Sub

'=====================================================================
'  二、HTTP 与 JSON
'=====================================================================
Private Function Utf8ToBytes(ByVal s As String) As Variant
    Dim st As Object
    Set st = CreateObject("ADODB.Stream")
    st.Type = 2
    st.Charset = "utf-8"
    st.Open
    st.WriteText s
    st.Position = 0
    st.Type = 1
    Utf8ToBytes = st.Read
    st.Close
End Function

Private Function BytesToUtf8(ByVal b As Variant) As String
    Dim st As Object
    If IsEmpty(b) Then Exit Function
    If LenB(b) = 0 Then Exit Function
    Set st = CreateObject("ADODB.Stream")
    st.Type = 1
    st.Open
    st.Write b
    st.Position = 0
    st.Type = 2
    st.Charset = "utf-8"
    BytesToUtf8 = st.ReadText
    st.Close
End Function

Private Function JsonQuote(ByVal s As String) As String
    Dim i As Long, c As Long, r As String
    r = """"
    For i = 1 To Len(s)
        c = AscW(Mid$(s, i, 1))
        If c < 0 Then c = c + 65536
        Select Case c
            Case 34: r = r & "\"""
            Case 92: r = r & "\\"
            Case 8: r = r & "\b"
            Case 9: r = r & "\t"
            Case 10: r = r & "\n"
            Case 12: r = r & "\f"
            Case 13: r = r & "\r"
            Case Is < 32: r = r & "\u" & Right$("000" & Hex$(c), 4)
            Case Else: r = r & ChrW$(c)
        End Select
    Next
    JsonQuote = r & """"
End Function

' 返回 "状态码|响应体"
Private Function HttpPost(ByVal url As String, ByVal body As String, ByVal timeoutSec As Long) As String
    Dim xh As Object
    Set xh = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    xh.setTimeouts timeoutSec * 1000, timeoutSec * 1000, timeoutSec * 1000, timeoutSec * 1000
    On Error GoTo Fail
    xh.Open "POST", url, False
    xh.setRequestHeader "Content-Type", "application/json; charset=utf-8"
    xh.setRequestHeader "Accept", "application/json"
    xh.send Utf8ToBytes(body)
    HttpPost = CStr(xh.Status) & "|" & BytesToUtf8(xh.responseBody)
    Exit Function
Fail:
    HttpPost = "0|" & Err.Number & ":" & Err.Description
End Function

Private Function FlowUrl() As String
    Dim base As String
    base = DEFAULT_SERVER
    If Right$(base, 1) <> "/" Then base = base & "/"
    FlowUrl = base & DEFAULT_FLOW_ID
End Function

Private Function ServerMessage(ByVal text As String) As String
    Dim j As Object
    On Error Resume Next
    Set j = JsonConverter.ParseJson(text)
    If Not j Is Nothing Then
        If j.Exists("message") Then
            ServerMessage = CStr(j("message"))
            Exit Function
        End If
        If j.Exists("error") Then
            ServerMessage = CStr(j("error"))
            Exit Function
        End If
    End If
    ServerMessage = Left$(text, 800)
End Function

' 调用工作流。innerJson 是传给 $input 的 JSON 字符串。
Private Function CallWorkflow(ByVal innerJson As String, ByVal timeoutSec As Long) As Object
    Dim body As String, resp As String, status As Long, text As String, j As Object
    Dim parts() As String
    body = "{""question"":" & JsonQuote(innerJson) & "}"
    resp = HttpPost(FlowUrl(), body, timeoutSec)
    parts = Split(resp, "|")
    status = CLng(parts(0))
    text = Mid$(resp, InStr(resp, "|") + 1)

    If status <> 200 Then
        gLastError = "Flowise 返回 HTTP " & status & vbCrLf & ServerMessage(text)
        Exit Function
    End If

    On Error Resume Next
    Set j = JsonConverter.ParseJson(text)
    On Error GoTo 0
    If j Is Nothing Then
        gLastError = "Flowise 返回内容不是合法 JSON：" & vbCrLf & Left$(text, 800)
        Exit Function
    End If
    If j.Exists("success") Then
        If j("success") = False Then
            gLastError = "工作流执行失败：" & vbCrLf & Left$(text, 800)
            Exit Function
        End If
    End If
    Set CallWorkflow = j
End Function

'=====================================================================
'  三、大纲
'=====================================================================
Private Function GenerateOutlineInternal(ByVal topic As String, ByVal slideCount As Long, _
                                         ByVal showPreview As Boolean) As Boolean
    Dim inner As String, root As Object, outline As Object, meta As Object, model As String
    If gBusy Then Warn "正在生成中，请稍候……": Exit Function

    topic = Trim$(topic)
    If Len(topic) = 0 Then Warn "主题不能为空": Exit Function
    If slideCount < 3 Then slideCount = 3
    If slideCount > 10 Then slideCount = 10

    gBusy = True
    gLastError = ""
    On Error GoTo Fail

    SetTip "AI 正在生成大纲（" & PRIMARY_MODEL & "，限流自动回退）..."
    inner = "{""topic"":" & JsonQuote(topic) & ",""slideCount"":" & CStr(slideCount) & _
            ",""outlineOnly"":true}"
    Set root = CallWorkflow(inner, 240)
    If root Is Nothing Then GoTo Fail
    If Not root.Exists("outline") Then
        gLastError = "工作流没有返回 outline 字段"
        GoTo Fail
    End If

    Set outline = root("outline")
    If Not outline.Exists("slides") Then
        gLastError = "大纲缺少 slides 字段"
        GoTo Fail
    End If

    Set gOutline = outline
    gTopic = topic
    gSlideCount = outline("slides").Count
    If root.Exists("meta") Then
        Set meta = root("meta")
        If meta.Exists("outlineModel") Then model = CStr(meta("outlineModel"))
    End If
    If Len(model) = 0 Then model = PRIMARY_MODEL
    gOutlineModel = model

    SetTip "大纲生成完成（模型：" & model & "）"
    gBusy = False
    If showPreview Then Info "大纲已生成（模型：" & model & "）" & vbCrLf & vbCrLf & FormatOutline(gOutline)
    GenerateOutlineInternal = True
    Exit Function

Fail:
    gBusy = False
    If Len(gLastError) = 0 Then gLastError = "生成大纲时发生错误 " & Err.Number & ": " & Err.Description
    Warn gLastError
    GenerateOutlineInternal = False
End Function

Private Function PromptAndGenerateOutline() As Boolean
    Dim topic As String, count As Long
    topic = InputBox("请输入 PPT 主题：", APP_TITLE, "人工智能赋能客户服务")
    If Len(Trim$(topic)) = 0 Then Exit Function
    count = Val(InputBox("请输入页数（3-10）：", APP_TITLE, "6"))
    If count = 0 Then Exit Function
    PromptAndGenerateOutline = GenerateOutlineInternal(topic, count, True)
End Function

Private Sub EnsureToolbar()
    Dim cb As Object
    On Error Resume Next
    Set cb = Application.CommandBars(APP_TITLE)
    If cb Is Nothing Then
        Err.Clear
        CreateToolbar True
    Else
        cb.Visible = True
    End If
    Err.Clear
End Sub

Public Sub AI_生成大纲()
    EnsureToolbar
    PromptAndGenerateOutline
End Sub

Private Function FormatOutline(ByVal outline As Object) As String
    Dim sb As String, slides As Object, item As Object
    Dim i As Long, j As Long, pts As Variant, st As String
    On Error Resume Next
    Set slides = outline("slides")
    If slides Is Nothing Then FormatOutline = "（大纲为空）": Exit Function
    sb = "标题：" & CStr(outline("title")) & vbCrLf & vbCrLf
    For i = 1 To slides.Count
        If i > 6 Then
            sb = sb & "……（共 " & slides.Count & " 页，后续页面将在 PPT 中生成）" & vbCrLf
            Exit For
        End If
        Set item = slides(i)
        st = CStr(item("title"))
        If i = 1 Then st = "[封面] " & st
        If i = slides.Count Then st = "[结尾] " & st
        sb = sb & i & ". " & st & vbCrLf
        pts = Split(CStr(item("content")), "；")
        For j = LBound(pts) To UBound(pts)
            If Len(Trim$(pts(j))) > 0 Then sb = sb & "   · " & Trim$(pts(j)) & vbCrLf
        Next
        sb = sb & vbCrLf
    Next
    FormatOutline = sb
End Function

'=====================================================================
'  四、生成图片 PPT
'=====================================================================
Private Function GeneratePptInternal() As Boolean
    Dim inner As String, root As Object, slides As Object
    Dim outPath As String

    If gOutline Is Nothing Then
        Warn "请先生成大纲"
        Exit Function
    End If
    If gBusy Then Warn "正在生成中，请稍候……": Exit Function

    gBusy = True
    gLastError = ""
    gImgOk = 0
    gImgFail = 0
    On Error GoTo Fail

    SetTip "AI 正在按大纲生成 " & gSlideCount & " 页幻灯片图片，约需 1-4 分钟..."
    inner = "{""topic"":" & JsonQuote(gTopic) & ",""slideCount"":" & CStr(gSlideCount) & _
            ",""outline"":" & JsonConverter.ConvertToJson(gOutline) & "}"
    Set root = CallWorkflow(inner, 600)
    If root Is Nothing Then GoTo Fail
    If Not root.Exists("slides") Then
        gLastError = "工作流没有返回 slides 字段"
        GoTo Fail
    End If
    Set slides = root("slides")
    If slides.Count = 0 Then
        gLastError = "工作流返回的 slides 为空"
        GoTo Fail
    End If

    SetTip "图片生成完成，正在组装 PPT..."
    outPath = BuildPresentation(slides, gTopic)
    If Len(outPath) = 0 Then GoTo Fail

    gLastPpt = outPath
    SetTip "生成完成：" & outPath
    gBusy = False
    GeneratePptInternal = True
    Exit Function

Fail:
    gBusy = False
    If Len(gLastError) = 0 Then gLastError = "生成 PPT 时发生错误 " & Err.Number & ": " & Err.Description
    Warn gLastError
    GeneratePptInternal = False
End Function

Public Sub AI_生成PPT()
    Dim ans As VbMsgBoxResult
    EnsureToolbar
    If gOutline Is Nothing Then
        If Not PromptAndGenerateOutline() Then Exit Sub
    Else
        ans = MsgBox("当前大纲：" & vbCrLf & gTopic & "（" & gSlideCount & " 页）" & vbCrLf & vbCrLf & _
                     "是否直接生成图片 PPT？" & vbCrLf & "选择“否”可重新生成大纲。", _
                     vbYesNo + vbQuestion, APP_TITLE)
        If ans = vbNo Then
            If Not PromptAndGenerateOutline() Then Exit Sub
        End If
    End If

    If GeneratePptInternal() Then
        Info "PPT 已生成：" & vbCrLf & gLastPpt & vbCrLf & vbCrLf & _
             "配图统计：" & AI_配图统计()
    End If
End Sub

Private Function BuildPresentation(ByVal slides As Object, ByVal topic As String) As String
    Dim pres As Presentation, sld As Slide
    Dim item As Object, outDir As String, runDir As String
    Dim imgUrl As String, imgPath As String
    Dim i As Long, okCount As Long
    Dim title As String, content As String

    outDir = GetOutDir()
    runDir = ImgRunDir()
    If Len(runDir) = 0 Then
        gLastError = "无法创建图片缓存目录"
        Exit Function
    End If

    Set pres = Application.Presentations.Add(-1)
    pres.PageSetup.SlideWidth = 960
    pres.PageSetup.SlideHeight = 540

    For i = 1 To slides.Count
        SetTip "正在组装第 " & i & "/" & slides.Count & " 页..."
        Set item = slides(i)
        title = ""
        content = ""
        If item.Exists("title") Then title = CStr(item("title"))
        If item.Exists("content") Then content = CStr(item("content"))
        imgUrl = ""
        If item.Exists("imageUrl") Then imgUrl = CStr(item("imageUrl"))

        If Len(imgUrl) > 0 Then
            imgPath = runDir & "slide" & Format$(i, "00") & ".png"
            If Len(Dir(imgPath)) > 0 Then Kill imgPath
            If DownloadImage(imgUrl, imgPath, 120) <> "" Then
                Set sld = pres.Slides.Add(pres.Slides.Count + 1, 12) ' ppLayoutBlank
                On Error Resume Next
                Dim pic As Shape
                Set pic = sld.Shapes.AddPicture(imgPath, 0, -1, 0, 0, 960, 540)
                If Err.Number = 0 Then
                    pic.Name = "AI_SlideImage"
                    pic.AlternativeText = title & " | " & content
                    gImgOk = gImgOk + 1
                    okCount = okCount + 1
                Else
                    Err.Clear
                    sld.Delete
                    gImgFail = gImgFail + 1
                    AddTextSlide pres, title, content
                End If
                On Error GoTo 0
            Else
                gImgFail = gImgFail + 1
                AddTextSlide pres, title, content
            End If
        Else
            gImgFail = gImgFail + 1
            AddTextSlide pres, title, content
        End If
    Next

    If okCount = 0 Then
        gLastError = "所有页面图片都下载失败，请检查网络或 Flowise 图片链接"
        Exit Function
    End If

    Dim savePath As String
    savePath = outDir & "\" & SafeFileName(topic) & "_AI生成_" & Format$(Now, "mmdd_hhnn") & ".pptx"
    On Error Resume Next
    pres.SaveAs savePath, 24 ' ppSaveAsOpenXMLPresentation
    If Err.Number <> 0 Then
        gLastError = "保存失败(" & Err.Number & ")：" & Err.Description & vbCrLf & savePath
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    On Error GoTo 0

    BuildPresentation = savePath
End Function

Private Sub AddTextSlide(ByVal pres As Presentation, ByVal title As String, ByVal content As String)
    Dim sld As Slide, shp As Shape, body As Shape
    Dim pts As Variant, i As Long, txt As String

    Set sld = pres.Slides.Add(pres.Slides.Count + 1, 12)
    sld.FollowMasterBackground = 0
    sld.Background.Fill.Solid
    sld.Background.Fill.ForeColor.RGB = RGB(9, 24, 46)
    sld.Tags.Add "AI_TEXT_FALLBACK", "1"

    Set shp = sld.Shapes.AddShape(1, 0, 0, 12, 540)
    shp.Fill.ForeColor.RGB = RGB(23, 184, 166)
    shp.Line.Visible = 0

    Set shp = sld.Shapes.AddTextbox(1, 70, 55, 820, 90)
    With shp.TextFrame
        .WordWrap = -1
        .MarginLeft = 0
        .MarginRight = 0
        .VerticalAnchor = 3
        .TextRange.Text = title
        .TextRange.Font.Name = "微软雅黑"
        .TextRange.Font.Size = 30
        .TextRange.Font.Bold = -1
        .TextRange.Font.Color.RGB = RGB(255, 255, 255)
    End With

    Set shp = sld.Shapes.AddShape(1, 70, 158, 120, 4)
    shp.Fill.ForeColor.RGB = RGB(23, 184, 166)
    shp.Line.Visible = 0

    pts = Split(content, "；")
    txt = ""
    For i = LBound(pts) To UBound(pts)
        If Len(Trim$(pts(i))) > 0 Then txt = txt & "•  " & Trim$(pts(i)) & vbCrLf & vbCrLf
    Next

    Set body = sld.Shapes.AddTextbox(1, 70, 190, 820, 270)
    With body.TextFrame
        .WordWrap = -1
        .MarginLeft = 0
        .MarginRight = 0
        .VerticalAnchor = 1
        .TextRange.Text = txt
        .TextRange.Font.Name = "微软雅黑"
        .TextRange.Font.Size = 20
        .TextRange.Font.Color.RGB = RGB(226, 236, 248)
        .TextRange.ParagraphFormat.SpaceAfter = 10
    End With
End Sub

Private Function GetOutDir() As String
    Dim d As String, i As Long
    d = ""
    On Error Resume Next
    d = Application.ActivePresentation.Path
    If Len(d) = 0 Then
        For i = 1 To Application.Presentations.Count
            d = Application.Presentations(i).Path
            If Len(d) > 0 Then Exit For
        Next
    End If
    Err.Clear
    On Error GoTo 0
    If Len(d) = 0 Then d = Environ$("USERPROFILE") & "\Documents"
    If Len(Dir(d, vbDirectory)) = 0 Then d = Environ$("USERPROFILE")
    GetOutDir = d
End Function

Private Function AppDir() As String
    Dim d As String
    d = Environ$("APPDATA") & "\" & CFG_DIR
    If Len(Dir(d, vbDirectory)) = 0 Then
        On Error Resume Next
        MkDir d
        On Error GoTo 0
    End If
    AppDir = d
End Function

Private Function GetIconDir() As String
    Dim d As String
    d = AppDir() & "\" & ICON_DIR
    If Len(Dir(d, vbDirectory)) = 0 Then
        On Error Resume Next
        MkDir d
        On Error GoTo 0
    End If
    GetIconDir = d & "\"
End Function

Private Function ImgRunDir() As String
    Dim d As String
    d = AppDir() & "\" & IMG_DIR & "\" & Format$(Now, "yyyymmdd_hhnnss")
    If Len(Dir(d, vbDirectory)) = 0 Then
        On Error Resume Next
        MkDir d
        On Error GoTo 0
    End If
    If Len(Dir(d, vbDirectory)) = 0 Then Exit Function
    ImgRunDir = d & "\"
End Function

Private Function DownloadImage(ByVal url As String, ByVal outPath As String, ByVal timeoutSec As Long) As String
    Dim xh As Object, st As Object
    On Error GoTo Fail
    Set xh = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    xh.setTimeouts timeoutSec * 1000, timeoutSec * 1000, timeoutSec * 1000, timeoutSec * 1000
    xh.Open "GET", url, False
    xh.send
    If xh.Status <> 200 Then Exit Function
    If LenB(xh.responseBody) < 1000 Then Exit Function
    Set st = CreateObject("ADODB.Stream")
    st.Type = 1
    st.Open
    st.Write xh.responseBody
    st.SaveToFile outPath, 2
    st.Close
    If Len(Dir(outPath)) = 0 Then Exit Function
    If FileLen(outPath) < 1000 Then Exit Function
    DownloadImage = outPath
    Exit Function
Fail:
    DownloadImage = ""
End Function

Private Function SafeFileName(ByVal s As String) As String
    Dim bad As Variant, i As Long, r As String
    bad = Array("\", "/", ":", "*", "?", """", "<", ">", "|")
    r = s
    For i = LBound(bad) To UBound(bad)
        r = Replace(r, CStr(bad(i)), "_")
    Next
    r = Replace(r, vbCr, "")
    r = Replace(r, vbLf, "")
    If Len(Trim$(r)) = 0 Then r = "AI_PPT"
    SafeFileName = Trim$(r)
End Function

'=====================================================================
'  五、测试、自检与开始页
'=====================================================================
Public Function AI_测试连接结果() As String
    Dim root As Object, msg As String
    SetTip "正在连接 Flowise..."
    Set root = CallWorkflow("__PING__", 30)
    If root Is Nothing Then
        AI_测试连接结果 = "连接失败：" & vbCrLf & vbCrLf & gLastError
        Exit Function
    End If
    If root.Exists("ping") Then
        If root("ping") = True Then
            msg = "Flowise 工作流连接正常。" & vbCrLf & vbCrLf & _
                  "接口：" & FlowUrl() & vbCrLf & _
                  "工作流：" & FLOW_NAME & vbCrLf & _
                  "大纲模型：" & PRIMARY_MODEL & "（回退 " & FALLBACK_MODEL & "）" & vbCrLf & _
                  "图片模型：" & IMAGE_MODEL
        Else
            msg = "Flowise 返回了非预期内容，请打开工作流检查。"
        End If
    Else
        msg = "Flowise 返回了非 ping 响应，请打开工作流检查。"
    End If
    AI_测试连接结果 = msg
End Function

Public Sub AI_测试连接()
    Dim msg As String
    EnsureToolbar
    msg = AI_测试连接结果()
    If Left$(msg, 4) = "连接失败" Then
        MsgBox msg, vbCritical, APP_TITLE
    Else
        MsgBox msg, vbInformation, APP_TITLE
    End If
End Sub

Public Sub AI_自检()
    Dim s As String
    s = "接口地址：" & FlowUrl() & vbCrLf & _
        "工作流 ID：" & DEFAULT_FLOW_ID & vbCrLf & _
        "大纲模型：" & PRIMARY_MODEL & vbCrLf & _
        "文本回退：" & FALLBACK_MODEL & vbCrLf & _
        "图片模型：" & IMAGE_MODEL & vbCrLf & vbCrLf & _
        "当前大纲：" & IIf(gOutline Is Nothing, "尚未生成", gTopic & "（" & gSlideCount & " 页）") & vbCrLf & _
        "大纲模型：" & IIf(Len(gOutlineModel) = 0, "-", gOutlineModel) & vbCrLf & _
        "最近 PPT：" & IIf(Len(gLastPpt) = 0, "-", gLastPpt) & vbCrLf & _
        "配图统计：" & AI_配图统计() & vbCrLf & _
        "最后错误：" & IIf(Len(gLastError) = 0, "无", gLastError)
    MsgBox s, vbInformation, APP_TITLE & " · 自检"
End Sub

Public Sub AI_关于()
    Dim s As String
    EnsureToolbar
    s = "AI PPT 助手" & vbCrLf & vbCrLf & _
        "1. 点击“生成大纲”：输入主题和页数，由商汤 Kimi-K3 生成大纲。" & vbCrLf & _
        "2. 点击“生成PPT”：U1.5 Lite 按大纲逐页生成 16:9 幻灯片图片，并自动组装成 PPT。" & vbCrLf & _
        "3. 若 Kimi-K3 限流，工作流会自动回退到 " & FALLBACK_MODEL & "。" & vbCrLf & _
        "4. U1.5 Lite 是文生图模型，不能生成文字大纲，因此专门负责页面图片。" & vbCrLf & vbCrLf & _
        "使用前请确认 Flowise 已启动：http://127.0.0.1:3000" & vbCrLf & _
        "图片为临时链接，生成后请及时保存 PPT。"
    MsgBox s, vbInformation, APP_TITLE
End Sub

' 供自动化自测使用：固定主题，不弹窗
Public Sub AI_SelfTest()
    Dim ok As Boolean, logPath As String, logText As String, t0 As Double
    gSilent = True
    gLastError = ""
    t0 = Timer
    On Error GoTo Fail

    ok = GenerateOutlineInternal("人工智能赋能客户服务", 4, False)
    If ok Then ok = GeneratePptInternal()

    logText = "ok=" & IIf(ok, "1", "0") & vbCrLf & _
              "elapsed=" & Format$(Timer - t0, "0.0") & vbCrLf & _
              "topic=" & gTopic & vbCrLf & _
              "slides=" & gSlideCount & vbCrLf & _
              "outlineModel=" & gOutlineModel & vbCrLf & _
              "images=" & AI_配图统计() & vbCrLf & _
              "ppt=" & gLastPpt & vbCrLf & _
              "error=" & gLastError & vbCrLf & _
              "progress=" & gTip
    logPath = Application.ActivePresentation.Path & "\selftest.log"
    WriteUtf8File logPath, logText
    gSilent = False
    Exit Sub

Fail:
    gSilent = False
    gLastError = gLastError & " / " & Err.Number & ": " & Err.Description
    On Error Resume Next
    WriteUtf8File Application.ActivePresentation.Path & "\selftest.log", "ok=0" & vbCrLf & "error=" & gLastError
End Sub

Private Sub WriteUtf8File(ByVal path As String, ByVal text As String)
    Dim st As Object
    On Error Resume Next
    Set st = CreateObject("ADODB.Stream")
    st.Type = 2
    st.Charset = "utf-8"
    st.Open
    st.WriteText text
    st.SaveToFile path, 2
    st.Close
End Sub

'=====================================================================
'  六、工具栏与开始页按钮
'=====================================================================
Public Sub AI_创建工具栏()
    CreateToolbar False
End Sub

Public Sub AI_创建工具栏Silent()
    CreateToolbar True
End Sub

Private Sub CreateToolbar(ByVal silentMode As Boolean)
    Dim cb As Object
    Dim iconDir As String
    iconDir = GetIconDir()

    On Error Resume Next
    Application.CommandBars(APP_TITLE).Delete
    Err.Clear
    On Error GoTo Fail

    Set cb = Application.CommandBars.Add(APP_TITLE)
    cb.Visible = True

    AddToolbarButton cb, "生成大纲", "AI_生成大纲", iconDir & "pptOutline.png"
    AddToolbarButton cb, "生成PPT", "AI_生成PPT", iconDir & "pptGenerate.png"
    AddToolbarButton cb, "测试连接", "AI_测试连接", iconDir & "pptTest.png"
    AddToolbarButton cb, "使用说明", "AI_关于", iconDir & "pptAbout.png"

    If Not silentMode And Not gSilent Then
        MsgBox "工具栏“" & APP_TITLE & "”已创建，位于 PowerPoint 标题栏下方。" & vbCrLf & _
               "也可以直接使用开始页上的四个按钮。", vbInformation, APP_TITLE
    End If
    Exit Sub
Fail:
    If Not silentMode And Not gSilent Then Warn "创建工具栏失败：" & Err.Description
End Sub

Private Sub AddToolbarButton(ByVal cb As Object, ByVal caption As String, _
                             ByVal macroName As String, ByVal iconPath As String)
    Dim btn As Object
    On Error Resume Next
    Set btn = cb.Controls.Add(1) ' msoControlButton
    btn.Caption = caption
    btn.OnAction = macroName
    btn.Tag = macroName
    btn.Style = 3 ' msoButtonIconAndCaption
    If Len(Dir(iconPath)) > 0 Then btn.Picture = LoadPicture(iconPath)
    Err.Clear
    On Error GoTo 0
End Sub

Public Sub AI_创建启动页()
    Dim pres As Presentation, sld As Slide, shp As Shape
    Dim iconDir As String

    If Application.Presentations.Count = 0 Then Exit Sub
    Set pres = Application.ActivePresentation
    iconDir = GetIconDir()

    Set sld = pres.Slides.Add(pres.Slides.Count + 1, 12) ' ppLayoutBlank
    sld.Tags.Add "AI_START", "1"
    sld.FollowMasterBackground = 0
    sld.Background.Fill.Solid
    sld.Background.Fill.ForeColor.RGB = RGB(7, 20, 40)

    ' 装饰
    Set shp = sld.Shapes.AddShape(9, 690, -80, 380, 380) ' oval
    shp.Fill.ForeColor.RGB = RGB(23, 184, 166)
    shp.Fill.Transparency = 0.86
    shp.Line.Visible = 0
    Set shp = sld.Shapes.AddShape(9, -90, 390, 260, 260)
    shp.Fill.ForeColor.RGB = RGB(42, 112, 190)
    shp.Fill.Transparency = 0.9
    shp.Line.Visible = 0
    Set shp = sld.Shapes.AddShape(1, 60, 44, 6, 70)
    shp.Fill.ForeColor.RGB = RGB(23, 184, 166)
    shp.Line.Visible = 0

    Set shp = sld.Shapes.AddTextbox(1, 88, 42, 700, 62)
    With shp.TextFrame
        .MarginLeft = 0
        .VerticalAnchor = 3
        .TextRange.Text = "AI PPT 助手"
        .TextRange.Font.Name = "微软雅黑"
        .TextRange.Font.Size = 38
        .TextRange.Font.Bold = -1
        .TextRange.Font.Color.RGB = RGB(255, 255, 255)
    End With

    Set shp = sld.Shapes.AddTextbox(1, 90, 108, 760, 44)
    With shp.TextFrame
        .MarginLeft = 0
        .TextRange.Text = "商汤 Kimi-K3 生成大纲  ·  SenseNova U1.5 Lite 生成幻灯片图片"
        .TextRange.Font.Name = "微软雅黑"
        .TextRange.Font.Size = 17
        .TextRange.Font.Color.RGB = RGB(150, 200, 220)
    End With

    AddIconButton sld, 100, 240, 360, 66, "1  生成大纲", "AI_生成大纲", iconDir & "pptOutline.png", RGB(22, 58, 92)
    AddIconButton sld, 500, 240, 360, 66, "2  生成图片 PPT", "AI_生成PPT", iconDir & "pptGenerate.png", RGB(23, 132, 130)
    AddIconButton sld, 100, 330, 360, 66, "3  测试连接", "AI_测试连接", iconDir & "pptTest.png", RGB(35, 74, 112)
    AddIconButton sld, 500, 330, 360, 66, "4  使用说明", "AI_关于", iconDir & "pptAbout.png", RGB(35, 74, 112)

    Set shp = sld.Shapes.AddTextbox(1, 90, 455, 780, 50)
    With shp.TextFrame
        .MarginLeft = 0
        .TextRange.Text = "使用前请启动 Flowise：http://127.0.0.1:3000    ·    图片为 AI 生成，生成后请及时保存"
        .TextRange.Font.Name = "微软雅黑"
        .TextRange.Font.Size = 11
        .TextRange.Font.Color.RGB = RGB(120, 155, 180)
    End With

    SetTip "开始页已创建"
End Sub

Private Sub AddIconButton(ByVal sld As Slide, ByVal x As Single, ByVal y As Single, _
                          ByVal w As Single, ByVal h As Single, ByVal caption As String, _
                          ByVal macroName As String, ByVal iconPath As String, ByVal fillColor As Long)
    Dim shp As Shape, pic As Shape
    Set shp = sld.Shapes.AddShape(5, x, y, w, h) ' rounded rectangle
    shp.Fill.ForeColor.RGB = fillColor
    shp.Line.Visible = 0
    On Error Resume Next
    shp.Adjustments(1) = 0.18
    Err.Clear
    On Error GoTo 0

    With shp.TextFrame
        .MarginLeft = 46
        .MarginRight = 10
        .VerticalAnchor = 3
        .TextRange.Text = caption
        .TextRange.Font.Name = "微软雅黑"
        .TextRange.Font.Size = 17
        .TextRange.Font.Bold = -1
        .TextRange.Font.Color.RGB = RGB(255, 255, 255)
    End With

    If Len(Dir(iconPath)) > 0 Then
        On Error Resume Next
        Set pic = sld.Shapes.AddPicture(iconPath, 0, -1, x + 14, y + (h - 28) / 2, 28, 28)
        If Err.Number = 0 Then pic.Name = "AI_BtnIcon"
        Err.Clear
        On Error GoTo 0
    End If

    shp.ActionSettings(1).Action = 8 ' ppActionRunMacro
    shp.ActionSettings(1).Run = "'" & sld.Parent.Name & "'!" & macroName
    shp.AlternativeText = "运行宏 " & macroName
End Sub

' 打开文件时自动挂工具栏（若 PowerPoint 允许）
Public Sub Auto_Open()
    On Error Resume Next
    CreateToolbar True
End Sub

Public Sub Auto_Close()
    On Error Resume Next
    Application.CommandBars(APP_TITLE).Delete
End Sub



