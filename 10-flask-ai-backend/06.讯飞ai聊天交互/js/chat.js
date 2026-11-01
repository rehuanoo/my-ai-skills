function getChatStream(chat, callback) {
      return new Promise((resolve, reject) => {
        // 创建 SSE 连接，请求你的后端接口 /api/chat_stream，把用户问题传过去，不支持post请求，只能get请求
        let eventSource = new EventSource('http://127.0.0.1:8080/api/chat_stream?chat=' + chat)
        let result = []
        eventSource.onmessage = function (e) {
          // console.log(e.data)
          if (e.data == '!!!finish!!!') {
            eventSource.close()
            resolve(result.join(''))
            return
          }
          if (e.data == '!!!error!!!') {
            console.log('error出错了')
            return
          }
          result.push(e.data)
          callback(e.data)
        }
      })

}

async function fetchAsStream(url, callback) {
      let response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          historyList: window.historyList,
        }),
      })

      if (!response.ok) {
        throw new Error('Network response was not ok ')
      }
      // 流式输出不断获取内容
      const reader = response.body.getReader()
      // 浏览器内置的解码器
      let decoder = new TextDecoder()
      let content = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }
        let txt = decoder.decode(value, { stream: true })
        content += txt
        console.log(txt)
        callback(txt)
      }

      return content

    }
// 先判断是否存在历史记录
let historyPages = localStorage.historyPages ? JSON.parse(localStorage.historyPages) : [
  {
    pageTitle: '新建聊天',
    historyList:[]
  }
]
// 修复点2：统一全局变量，activeIndex转数字（本地存储是字符串）
// let activeIndex = localStorage.activeIndex ? localStorage.activeIndex : 0
let activeIndex = localStorage.activeIndex ? Number(localStorage.activeIndex) : 0
// let historyList = localStorage.historyList ? JSON.parse(localStorage.historyList) : []
window.historyList = historyPages[activeIndex].historyList

window.addEventListener('DOMContentLoaded', function () {
  let submitBtn = document.querySelector('.submit')
  let chatInput = document.querySelector('#chat')
  let chatList = document.querySelector('.rightChatList')
  let newchatBtn = document.querySelector('#newChat')
  
  window.renderHistoryList = renderHistoryList
  function renderHistoryList() {
    chatList.innerHTML = ''
    window.historyList.forEach(item => {
    if (item.role == 'user') {
      chatList.innerHTML += `
    <div class="chatContentItem">
          <div class="chatAvater">
            <img src="image/logo5.png" alt="">
          </div>
          <div class="chatMain">
            <div class="txt">${item.content}</div>
          </div>`
    } else {
      chatList.innerHTML += `
    <div class="chatContentItem robot">
          <div class="chatAvater">
            <img src="image/robot-fill.png" alt="">
          </div>
          <div class="chatMain">
            <div class="txt">
              ${item.content}
            </div>
            <div class="chatIconList">
              <div class="refresh">
                <img src="image/refresh.png" alt="">
              </div>
              <div class="copy">
                <img src="image/copy.png" alt="">
              </div>
            </div>
          </div>
        </div>
    `
    }
  })
  }
  renderHistoryList()
  

  submitBtn.onclick = async function () {
      // 🔥 加这一行：空内容不发送
    const inputValue = chatInput.value.trim()
    if (!inputValue) return

    if (window.historyList.length == 0) {
      historyPages[activeIndex].pageTitle = inputValue.slice(0, 10)
      if (window.renderhistoryPane) {
        window.renderhistoryPane()
      }
    }
    window.historyList.push({
      role: 'user',
      content: inputValue
    })
    
    chatList.innerHTML += `
    <div class="chatContentItem">
          <div class="chatAvater">
            <img src="image/logo5.png" alt="">
          </div>
          <div class="chatMain">
            <div class="txt">${chatInput.value}</div>
          </div>
        </div>
    `



    // 保存当前机器人回复框的数量
    let robotCount = document.querySelectorAll('.chatContentItem.robot').length
    
    chatList.innerHTML += `
    <div class="chatContentItem robot">
          <div class="chatAvater">
            <img src="image/robot-fill.png" alt="">
          </div>
          <div class="chatMain">
            <div class="txt chatWrite">
            </div>
            <div class="chatIconList">
              <div class="refresh">
                <img src="image/refresh.png" alt="">
              </div>
              <div class="copy">
                <img src="image/copy.png" alt="">
              </div>
            </div>
          </div>
        </div>
    `
//  let chatWrite = document.querySelector('.txt.chatWrite')
    // 获取最新添加的机器人回复框
    let robots = document.querySelectorAll('.chatContentItem.robot')
    let chatWrite = robots[robots.length - 1].querySelector('.txt')
    let value = chatInput.value
    chatInput.value = ''
    let chatObj = await fetchAsStream('http://127.0.0.1:8080/api/chat_stream', function (data) {
        chatWrite.innerHTML += data
    })

    // chatWrite.classList.remove('chatWrite')
    
// 必须 await
// 必须等 fetchAsStream 执行完
// 再 push 机器人消息
// 再存 localStorage
    window.historyList.push({
      role: 'robot',
      content: chatObj
    })
    // 保存历史记录
    localStorage.setItem('historyPages', JSON.stringify(historyPages))

  }
  chatInput.onkeydown = function (e) {
    if (e.key == 'Enter') {
      e.preventDefault()
      submitBtn.onclick()
    }
  }

  newchatBtn.onclick = function () {
    historyPages.push({
    pageTitle: '新建聊天',
    historyList:[]
    })
    activeIndex = historyPages.length - 1
    window.historyList = historyPages[activeIndex].historyList
    localStorage.setItem('historyPages', JSON.stringify(historyPages))
    localStorage.setItem('activeIndex', activeIndex)
    console.log(window.historyList)
    renderHistoryList()
    if (window.renderhistoryPane) {
      window.renderhistoryPane()
    }
  }
})