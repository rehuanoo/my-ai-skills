document.addEventListener('DOMContentLoaded', function () {
  let historysBtn = document.querySelector('.historys')
  let helperBtn = document.querySelector('.helpers')
  let historyPane = document.querySelector('.left-content-list.history')
  let helperPane = document.querySelector('.left-content-list.helper')
  let lists = historyPages

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
  // let lists = historyPages

  function renderhistoryPane() {
    
  
  let listStr = ''
  // 循环数组生成列表
  lists.forEach((item, i) => {
    
    let divStr = `
     <div class="list-item" data-index="${i}">
              <img src="image/Chat.png" alt="">
              <div class="chat-content">${item.pageTitle}</div>
              <div class="icons">
                <img src="image/编辑.png" title="编辑">
                <img src="image/删除.png" title="删除">
              </div>
              <div class="editMode">
                <input type="text" value="${item.pageTitle}"/>
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
  window.renderhistoryPane = renderhistoryPane


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
      lists[index].pageTitle = text
      historyPages = lists  // 把修改后的 lists 同步给全局变量
      localStorage.setItem('historyPages', JSON.stringify(historyPages)) // 保存
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
      input.value = lists[index].pageTitle
      editMode.style.display = 'none'
      console.log(lists[index])
       
    }
    if (e.target.getAttribute('title') === '删除') {
      let listItem = e.target.parentNode.parentNode
      let editMode = listItem.querySelector('.editMode')
      let index = listItem.getAttribute('data-index')
      lists.splice(index, 1)

       // 修复：删除后重置索引，防止崩溃
      if(lists.length === 0){
        lists.push({ pageTitle: '新建聊天', historyList:[] })
        activeIndex = 0
      }else{
        activeIndex = Math.min(activeIndex, lists.length-1)
      }
      
      localStorage.setItem('historyPages', JSON.stringify(historyPages))
      localStorage.setItem('activeIndex', activeIndex)
      window.historyList = lists[activeIndex].historyList
      renderHistoryList()
      renderhistoryPane()
      // historyPages = lists  // 同步
      // localStorage.setItem('historyPages', JSON.stringify(historyPages)) // 保存
      // renderhistoryPane()

    }

    // if (e.target.classList.contains('list-item') ||
    //   e.target.classList.contains('chat-content')) {
    //   let listItem
    //   let index
    //   if (listItem.classList.contains('list-item')) {
    //     listItem = e.target
    //     index = listItem.getAttribute('data-index')
    //   } else if(e.target.classList.contains('chat-content')){
    //     listItem = e.target.parentNode
    //     index = listItem.getAttribute('data-index')
    //   } else {
    //     return
    //   }
    //   localStorage.activeIndex = index
    //   console.log(index)
    //   window.historyList = historyPane[index].historyList
    //   console.log(window.historyList)
    //   renderHistoryList()
    //   renderhistoryPane()
    // }

        if (e.target.closest('.list-item')) {
      const listItem = e.target.closest('.list-item')
      const index = Number(listItem.dataset.index)
      // 同步全局索引
      activeIndex = index
      localStorage.setItem('activeIndex', index)
      // 修复赋值错误：historyPages 而非 historyPane
      window.historyList = historyPages[index].historyList
      if (window.renderHistoryList) {
        window.renderHistoryList()
      }
      renderhistoryPane()
    }
  })
})