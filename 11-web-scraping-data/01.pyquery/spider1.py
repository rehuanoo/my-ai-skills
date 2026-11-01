from playwright.sync_api import sync_playwright
from pyquery import PyQuery as pq

def get_cctv_news():
    with sync_playwright() as p:
        # 无头模式（不弹出浏览器窗口）
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 访问页面，允许更长加载时间
        page.goto("https://news.cctv.com/", timeout=60000)

        # 等待页面完全加载
        page.wait_for_load_state("networkidle", timeout=30000)

        # 等待一段时间让JavaScript渲染完成
        page.wait_for_timeout(3000)

        # 获取渲染完成的HTML
        html = page.content()
        browser.close()

    # 开始解析
    doc = pq(html)
    print("=" * 60)
    print("央视新闻 - 每日最新新闻")
    print("=" * 60)

    # 使用选择器获取新闻列表
    news_list = doc("#newslist li")

    count = 0
    for item in news_list.items():
        title = item("h3.title a").text().strip()
        link = item("h3.title a").attr("href")
        
        # 使用正确的时间选择器
        news_time = item("div.text_con div span.date").text().strip()

        if title:
            count += 1
            print(f"\n【{count}】{title}")
            print(f"时间：{news_time if news_time else '未获取到'}")
            print(f"链接：{link}")

    if count == 0:
        print("\n未找到新闻，可能页面结构已变化，请检查选择器")

if __name__ == "__main__":
    get_cctv_news()