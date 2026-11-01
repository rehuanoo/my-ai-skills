from pyquery import PyQuery as pq
import requests
import os
import time
import random

# 基础URL
BASE_URL = "https://www.dogetu.com/biaoqing.html"
# 图片存储目录
IMG_DIR = "./imgs"

# 请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.dogetu.com/"
}

# 创建图片存储目录
def create_img_dir():
    os.makedirs(IMG_DIR, exist_ok=True)

# 获取页面HTML
def get_page(page_num):
    url = f"{BASE_URL}?page={page_num}"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        print(f"获取页面 {page_num} 失败: {e}")
        return None

# 解析页面获取图片URL
def parse_images(html):
    if not html:
        return []
    doc = pq(html)
    # 使用指定的选择器
    img_elements = doc("div.panel-body > div.pic-list > div > div > a > img")
    img_urls = []
    for img in img_elements.items():
        img_url = img.attr("src")
        if img_url:
            # 处理相对路径
            if not img_url.startswith("http"):
                img_url = "https://www.dogetu.com" + img_url
            img_urls.append(img_url)
    return img_urls

# 获取图片扩展名
def get_extension(url):
    if url.endswith('.png'):
        return '.png'
    elif url.endswith('.gif'):
        return '.gif'
    elif url.endswith('.webp'):
        return '.webp'
    else:
        return '.jpg'

# 下载单张图片并按顺序命名
def download_image(img_url, save_path):
    try:
        response = requests.get(img_url, headers=headers, timeout=10)
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"下载成功: {os.path.basename(save_path)}")
        return True
    except Exception as e:
        print(f"下载失败 {img_url}: {e}")
        return False

# 检查是否还有下一页
def has_next_page(html):
    if not html:
        return False
    doc = pq(html)
    # 查找分页导航，判断是否有下一页
    # 方法1: 检查是否有可点击的下一页链接
    next_page = doc("ul.pagination li.next")
    if next_page and not next_page.has_class("disabled"):
        return True
    
    # 方法2: 检查分页信息，看是否还有更多页
    pagination_info = doc("ul.pagination li.active")
    if pagination_info:
        current_page = pagination_info.text().strip()
        # 检查是否有下一页的数字
        next_page_num = doc(f"ul.pagination li:contains('{int(current_page) + 1}')")
        if next_page_num:
            return True
    
    return False

# 主爬虫函数
def main():
    create_img_dir()
    page_num = 2  # 从第2页开始
    total_downloaded = 0
    global_counter = 1  # 全局计数器，用于按顺序命名
    
    while True:
        print(f"\n===== 正在爬取第 {page_num} 页 =====")
        html = get_page(page_num)
        
        if not html:
            print(f"无法获取第 {page_num} 页，尝试下一页")
            page_num += 1
            continue
        
        img_urls = parse_images(html)
        
        if not img_urls:
            print(f"第 {page_num} 页未找到图片")
            # 检查是否还有下一页
            if not has_next_page(html):
                print("已到达最后一页，爬取结束")
                break
            page_num += 1
            continue
        
        print(f"第 {page_num} 页找到 {len(img_urls)} 张图片")
        
        # 下载本页所有图片，按顺序命名
        for i, img_url in enumerate(img_urls):
            # 按顺序命名：001.jpg, 002.jpg, ...
            ext = get_extension(img_url)
            filename = f"{global_counter:03d}{ext}"
            save_path = os.path.join(IMG_DIR, filename)
            
            if download_image(img_url, save_path):
                total_downloaded += 1
                global_counter += 1
            
            # 随机延迟，避免请求过快
            time.sleep(random.uniform(0.2, 0.5))
        
        # 检查是否还有下一页
        if not has_next_page(html):
            print("已到达最后一页，爬取结束")
            break
        
        page_num += 1
        # 每页之间延迟
        time.sleep(random.uniform(1, 2))
    
    print(f"\n✅ 爬取完成！共下载 {total_downloaded} 张图片")
    print(f"图片已按顺序命名：001.jpg, 002.jpg, ...")

if __name__ == "__main__":
    main()