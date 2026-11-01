import asyncio
from pyppeteer import launch

async def main():
  # 启动浏览器,设置显示浏览器窗口
  browser = await launch(headless=False)
  # 打开百度
  page = await browser.newPage()
  await page.goto('https://www.baidu.com')
  
  # 停留60s
  await asyncio.sleep(60)
  # 关闭浏览器
  await browser.close()


# 运行异步程序
asyncio.run(main())