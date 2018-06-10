import re
import os
import json
import requests
import pymongo
import urllib.request
from multiprocessing import Pool
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
from hashlib import md5

headers = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 \
                   (KHTML, like Gecko) Chrome/67.0.3396.62 Safari/537.36',
}

# 设置MongoDB数据库
MONGO_URL = 'localhost'
MONGO_DB = 'jinritoutiao_jiepai'
MONGO_TABLE = 'jiepai_images'

client = pymongo.MongoClient(MONGO_URL, connect=False)
db = client[MONGO_DB]

GROUP_START = 1
GROUP_END = 5       # 循环圈数
KEYWORD = '街拍'


def get_page_first(offset, keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 1,
        'from': 'search_tab'
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.text
        else:
            return None
    except RequestException:
        print('获取首页请求异常')
        return None


def parse_page_first(html):
    data = json.loads(html)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            # 构造一个生成器，把所有的article_url解析出来
            yield item.get('article_url')


def get_page_detail(page_url):
    try:
        page_res = requests.get(page_url, headers=headers)
        if page_res.status_code == 200:
            soup = BeautifulSoup(page_res.text, 'lxml')
            title = soup.select('title')[0].get_text()
            tag_pattern = re.compile("chineseTag: '(.*?)'", re.S)
            tag = re.findall(tag_pattern, page_res.text)[0]
            # 我们只获取图片，需要过滤掉视频。
            if tag == '视频':
                pass
            else:
                # 图集形式
                images_pattern_gallery = re.compile('gallery: JSON.parse\("(.*?)"\)', re.S)
                result_gallery = re.search(images_pattern_gallery, page_res.text)
                if result_gallery:
                    result_gallery = result_gallery.group(1).replace(r'\"', r'"').replace('\\', '')
                    data = json.loads(result_gallery)
                    if data and 'sub_images' in data.keys():
                        sub_images = data.get('sub_images')
                        imgs_url = [item.get('url') for item in sub_images]
                        print("准备下载: " + title + " 中的图片" + ", 地址为:" + page_url)
                        for img_url in imgs_url:
                            download_img(img_url, title)
                        return {
                            'title': title,
                            'url': page_url,
                            'images': imgs_url,
                        }
                else:
                    # 文章+图片形式
                    images_pattern_article = re.compile('http://p(.*?)&', re.S)
                    result_article = re.findall(images_pattern_article, page_res.text)
                    if result_article:
                        article_img_urls = ['http://p' + i for i in result_article]
                        for article_img_url in article_img_urls:
                            download_img(article_img_url, title)
                        return {
                            'title': title,
                            'url': page_url,
                            'images': article_img_urls,
                        }
        else:
            return None
    except RequestException:
        print("获取详细页面请求异常")
        return None


def download_img(img_url, title):
    try:
        img_res = requests.get(img_url, headers=headers)
        if img_res.status_code == 200:
            if not os.path.exists('img'):
                os.mkdir('img')
            pathname = 'img/'+title
            if not os.path.exists(pathname):
                os.mkdir(pathname)
            print("正在下载: " + img_url)
            filename = pathname + '/' + md5(img_res.content).hexdigest() + '.jpg'
            if not os.path.exists(filename):
                urllib.request.urlretrieve(img_url, filename=filename)
    except RequestException:
        print("请求图片出错：" + img_url)
        return None


def save_to_mongo(page_detail):
    if db[MONGO_TABLE].insert(page_detail):
        print("存储到MongoDB成功")
        return True
    return False


def main(offset):
    html = get_page_first(offset, KEYWORD)
    for page_url in parse_page_first(html):
        if page_url:
            page_detail = get_page_detail(page_url)
            if page_detail:
                save_to_mongo(page_detail)


if __name__ == '__main__':
    groups = [x * 20 for x in range(GROUP_START, GROUP_END+1)]
    pool = Pool()
    pool.map(main, groups)
    print("爬虫结束")

