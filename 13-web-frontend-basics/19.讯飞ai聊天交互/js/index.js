document.addEventListener('DOMContentLoaded', function () {
  let historysBtn = document.querySelector('.historys')
  let helperBtn = document.querySelector('.helpers')
  let historyPane = document.querySelector('.left-content-list.history')
  let helperPane = document.querySelector('.left-content-list.helper')

  historysBtn.addEventListener('click', function () {
    historysBtn.classList.add('active')
    helperBtn.classList.remove('active')
    historyPane.classList.add('active')
    helperPane.classList.remove('active')
  })

  helperBtn.addEventListener('click', function () {
    helperBtn.classList.add('active')
    historysBtn.classList.remove('active')
    helperPane.classList.add('active')
    historyPane.classList.remove('active')
  })

  // 列表的增删
  let lists = [
    {
      id: 1,
      name: 'nihao',
      chatList: [
        {
          user: 'nihao',
          ai: '你好，我是小智，有什么可以帮助你的吗？'
        }
      ]
    },
  
   {
      id: 2,
      name: '为什么天空是蓝色的？',
      chatList: [
        {
          user: '为什么天空是蓝色的？',
          ai: '太阳光被大气中的微小分子散射，蓝光波长更短，散射更强，所以天空看起来是蓝色。'
        }
      ]
  },
  {
      id: 3,
      name: '手机充电一整晚会不会伤电池？',
      chatList: [
        {
          user: '手机充电一整晚会不会伤电池？',
          ai: '现在手机都有过充保护，充满后会自动断电，正常情况下一整晚充电不会伤电池。'
        }
      ]
  },
  {
      id: 4,
      name: '蚊子为什么总咬我？蚊子为什么总咬我？蚊子为什么总咬我？蚊子为什么总咬我？蚊子为什么总咬我？',
      chatList: [
        {
          user: '蚊子为什么总咬我？蚊子为什么总咬我？蚊子为什么总咬我？蚊子为什么总咬我？蚊子为什么总咬我？',
          ai: '和体温、汗液气味、血型、穿衣颜色都有关，每个人吸引蚊子的程度不一样。'
        }
      ]
    }
  
  ]

  function renderhistoryPane() {
    
  
  let listStr = ''
  // 循环数组生成列表
  lists.forEach((item, i) => {
    
    let divStr = `
     <div class="list-item" data-index="${i}">
              <img src="image/Chat.png" alt="">
              <div class="chat-content">${item.name}</div>
              <div class="icons">
                <img src="image/编辑.png" title="编辑">
                <img src="image/删除.png" title="删除">
              </div>
              <div class="editMode">
                <input type="text" value="${item.name}"/>
                <div class="icons">
                  <img src="image/正确.png" title="确定">
                  <img src="image/错误.png" title="取消">
                </div>
              </div>

            </div>
  `
    listStr += divStr
    
    
  })
    historyPane.innerHTML = listStr
  }

  renderhistoryPane()

  historyPane.addEventListener('click', function (e) {
    console.log(e)
    console.log(e.target.getAttribute('title'))
    if (e.target.getAttribute('title') === '编辑') {
      console.log(e.target.parentNode.parentNode)
      let listItem = e.target.parentNode.parentNode
      let editMode = listItem.querySelector('.editMode')
      editMode.style.display = 'flex'
      let input = editMode.querySelector('input')
      input.focus()
      input.selectionStart = input.selectionEnd = input.value.length
      console.log(editMode) 
    }
    if (e.target.getAttribute('title') === '确定') {
      let editMode = e.target.parentNode.parentNode
      let listItem = e.target.parentNode.parentNode.parentNode
      let input = editMode.querySelector('input')
      let text = input.value
      let index = listItem.getAttribute('data-index')
      lists[index].name = text
      let chatContent = listItem.querySelector('.chat-content')
      chatContent.innerText = text
      editMode.style.display = 'none'
      console.log(lists[index])
      
    }
     if (e.target.getAttribute('title') === '取消') {
      let editMode = e.target.parentNode.parentNode
      let listItem = e.target.parentNode.parentNode.parentNode
      let input = editMode.querySelector('input')
      let index = listItem.getAttribute('data-index')
      input.value = lists[index].name
      editMode.style.display = 'none'
      console.log(lists[index])
      
    }
    if (e.target.getAttribute('title') === '删除') {
      let listItem = e.target.parentNode.parentNode
      let editMode = listItem.querySelector('.editMode')
      let index = listItem.getAttribute('data-index')
      lists.splice(index, 1)
      renderhistoryPane()

    }
  })
})