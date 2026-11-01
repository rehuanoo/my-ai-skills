from pyquery import PyQuery as pq
import requests

from playwright.sync_api import sync_playwright
import time


def get_dynamic_html(url, sleep_time=3):
    
    # 用 Playwright 获取动态渲染后的网页 HTML
    # :param url: 要爬的网址
    # :param sleep_time: 等待页面加载的时间，默认3秒
    # :return: 渲染后的完整网页源代码
    
    with sync_playwright() as p:
        # 无头模式（不弹出浏览器窗口）
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url)
            time.sleep(sleep_time)  # 等待页面JS渲染完成
             # 滚动页面，让动态内容全部加载出来
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            html = page.content()   # 获取最终HTML
        except Exception as e:
            print(f"爬取出错：{e}")
            html = None
        finally:
            browser.close()
    
    return html

# 通过url获取网页内容
# request请求只能获得没经js渲染的html源代码
# def get_page(url):
#     try:
#         r = requests.get(url)
#         r.encoding = 'utf-8'
#         return r.text
#     except:
#         return None
    

# htmlStr= get_page(url)
# print(htmlStr)

# 定义一个函数获取新闻列表，列表的选择器为#newslist > li > div.text_con > h > a
def get_news_list(html):
    if not html:
        print("未获取到页面内容")
        return
    
    doc = pq(html)
    news_list = doc('#newslist > li > div.text_con > h > a').items()
    print(news_list)
    for news in news_list:
        print(news.text())
        print(news.attr('href'))
        print('-----------------')



if __name__ == '__main__':
    # url = 'https://news.cctv.com/'
    html = get_dynamic_html("https://news.cctv.com/")
    # htmlStr = get_page(url)
    get_news_list(html)

