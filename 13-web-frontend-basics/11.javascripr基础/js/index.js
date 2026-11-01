var btn = document.querySelector("button");
btn.onclick = function () {
  alert("hello world");
}
console.log(btn);

// 变量名var与let的区别：let只能在一个作用域中声明一次，var可以声明多次
// {
//   let btn1 = document.querySelector("button");
// }
// console.log(btn1);
// 这样就会报错
let btn1 = document.querySelector("button");
console.log(btn1);

// const是在let的基础上，加上不能修改
// {
//   const btn2 = document.querySelector("button");
//   console.log(btn2);
//   btn2 = 456
//   console.log(btn2);
// }
// 会报错

const btn2 = document.querySelector("button");
console.log(btn2);

let btn3 = document.querySelector("button");
console.log(btn3);

btn3 = 456;
console.log(btn3, typeof btn3);
btn3 = "456"
console.log(btn3, typeof btn3);
btn3 = true;
console.log(btn3, typeof btn3);
btn3 = [1, 5, 6]
console.log(btn3, typeof btn3);

// ------------------------------------------------------
// 所有字符串与其他内容拼接（+）结果都是字符串
// let a = 123;
// let b = "456";
// console.log(a + b); // 123456
// console.log("123" + true);// 123true

// 不是高精度机器语言都会有0.1 + 0.2=0.30000000000000004的问题

//   == 与 === （全相等）的区别：== 只比较值，=== 比较值和类型
//   ！= 与 !== （全不等）的区别：!= 只比较值，!== 比较值和类型

// &&，||，！（与，或，非）