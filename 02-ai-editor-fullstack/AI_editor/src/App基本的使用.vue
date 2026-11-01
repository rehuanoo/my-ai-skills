<script setup>
// import HelloWorld from './components/HelloWorld.vue'
import { reactive } from 'vue'

let data = reactive({
  name: '张三',
  age: 18
})
// let name = '张三'

let changename = () => {
  data.name = '李四'
}
</script>

<template>
  <h1>你好，{{ data.name }}</h1>
  <button @click="changename">改变名字</button>
  <input type="text" v-model="data.name">
  <a-input v-model:value="data.name" placeholder="Basic usage" />
  <a-button type="primary" @click="changename">更改名字</a-button>

</template>
