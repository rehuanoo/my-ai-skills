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
// 先判断是否存在历史记录
let historyList = localStorage.historyList ? JSON.parse(localStorage.historyList) : []

window.addEventListener('DOMContentLoaded', function () {
  let submitBtn = document.querySelector('.submit')
  let chatInput = document.querySelector('#chat')
  let chatList = document.querySelector('.rightChatList')
  
  historyList.forEach(item => {
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

  submitBtn.onclick = async function () {
    
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
    let chatObj = await getChatStream(value, function (data) {
      chatWrite.innerHTML += data
      
    })

    chatWrite.classList.remove('chatWrite')
    historyList.push({
      role: 'user',
      content: value
    })

    historyList.push({
      role: 'robot',
      content: chatWrite.innerHTML
    })
    // 保存历史记录
    localStorage.setItem('historyList', JSON.stringify(historyList))

  }
  chatInput.onkeydown = function (e) {
    if (e.key == 'Enter') {
      e.preventDefault()
      submitBtn.onclick()
    }
  }
})