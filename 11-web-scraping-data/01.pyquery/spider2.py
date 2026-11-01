from playwright.sync_api import sync_playwright
from pyquery import PyQuery as pq
import time
import random
import sqlite3
import requests
import os

# 数据库路径
DATABASE = './database/herolist.db'
# 基础域名，补全相对链接
BASE_URL = "https://pvp.qq.com/web201605/"

# 全局变量
category = ''
db = None

# 数据库连接
def connection():
    global db
    # 自动建文件夹
    os.makedirs('./database', exist_ok=True)
    db = sqlite3.connect(DATABASE)
    return db

# 请求页面方法（你原有保留）
def get_page(pageUrl):
    try:
        # 加简单请求头防拦截
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(pageUrl, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        return r.text
    except Exception as e:
        print("请求详情页失败：", e)
        return None

# 解析详情页并插入数据库
def insert_heroList(html):
    if not html:
        return
    doc = pq(html)
    # 你原来的选择器保留
    news_list = doc("div.zk-con3.zk-con")
    
    # 遍历每个技能块
    for item in news_list.items():
        skillName = item("div.skill.ls.fl > div > div > div p.skill-name b").text().strip()
        skillCon = item("div.skill.ls.fl > div > div > div p.skill-desc").text().strip()
        heroName = item("div.crumb > label").text().strip()

        # 过滤空数据
        if not heroName or not skillName or not skillCon:
            continue
        
        # 安全插入 不用字符串拼接，防SQL注入
        try:
            sql = "INSERT INTO heroList (heroName, skillName, skillCon) VALUES (?, ?, ?)"
            db.execute(sql, (heroName, skillName, skillCon))
            db.commit()
            print(f"入库成功：{heroName} - {skillName}")
        except Exception as e:
            print("入库失败：", e)

# 爬英雄列表主逻辑
def get_heroLists():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://pvp.qq.com/web201605/herolist.shtml", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    # 解析列表
    doc = pq(html)
    print("=" * 60)
    print("英雄列表爬取开始")
    print("=" * 60)

    news_list = doc("div.herolist-content ul li a")
    count = 0

    for item in news_list.items():
        # 修复：不要再 item("a") 重复取值
        title = item.text().strip()
        link = item.attr("href")

        if not title or not link:
            continue
        
        count += 1
        # 拼接完整详情链接
        full_link = BASE_URL + link
        print(f"\n【{count}】英雄：{title} | 详情链接：{full_link}")

        # 1. requests 获取详情页html
        htmlStr = get_page(full_link)
        # 2. 传入解析入库
        insert_heroList(htmlStr)

        # 随机延迟，防止请求过快
        time.sleep(random.uniform(0.3, 0.8))

    print(f"\n✅ 爬取完毕，共处理 {count} 个英雄")

if __name__ == "__main__":
    # 连接数据库
    connection()
    # 开始爬取
    get_heroLists()
    # 关闭数据库
    db.close()


# 如果要爬取登录后的数据，需要在请求头里加上cookie