# coding: utf-8
import requests
from bs4 import BeautifulSoup
import pymysql
import json


# 链接数据库
conn = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='hycmysql',
    db='baidu_songlist',
    charset='utf8'
)
cursor = conn.cursor()

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
    'Host': 'music.baidu.com',
    'Connection': 'keep-alive',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
    'Upgrade-Insecure-Requests': '1'
}

def get_songlist_info(title, link):
    try:
        print("正在获取歌单：" + title + " 的详细信息...")
        songlistdata = requests.get(link, headers=headers).content
        soup = BeautifulSoup(songlistdata, 'lxml')
        songlist_name = soup.h1.get_text()   # 歌单名字
        songlist_url = link  # 歌单链接
        songlist_creater = soup.find(name="a", class_="songlist-info-username").get_text()  # 歌单创建者
        songlist_info_tags = soup.select("div.songlist-info-tag > a")
        songlist_tags = ""
        # 歌单标签
        for tag in songlist_info_tags:
            songlist_tags = songlist_tags + tag.get_text() + " "
        songlist_play_num = int(soup.find(name="span", class_="songlist-listen").get_text()[:-3])  # 播放次数
        songlist_share_num_str = soup.find(name="i", class_="share-num-text").get_text()  # 分享次数
        # 如果分享次数为0， 将"分享"换为0
        if songlist_share_num_str == "分享":
            songlist_share_num_str = 0
        songlist_share_num = int(songlist_share_num_str)
        songlist_collect_num = int(soup.find(name="em", class_="collectNum").get_text())  # 收藏次数
        songlist_comment_num = int(soup.find(name="em", class_="discuss-num").get_text())  # 评论数目
        songlist_song_num = int(soup.find(name="span", class_="songlist-num").get_text()[:-1])  # 歌曲数目
        # 如果该歌单中的歌曲数量超过20个，需要往后翻页，每页歌曲数量20个。
        for song_num in range(0, songlist_song_num, 20):
            songlist_url = link + "/offset/{0}?third_type=".format(song_num)
            songlistdata = requests.get(songlist_url, headers=headers).content
            songlistsoup = BeautifulSoup(songlistdata, 'lxml')
            songlist_musics = songlistsoup.select("div.normal-song-list > ul > li")
            for music_info in songlist_musics:
                music_data = json.loads(music_info["data-songitem"])
                songlist_musicname = music_data["songItem"]["sname"]
                songlist_musicsinger = music_data["songItem"]["author"]
                print(songlist_play_num, songlist_comment_num, songlist_share_num, \
                      songlist_musicname, songlist_musicsinger)
                try:
                    cursor.execute(
                        "insert into songlist_detail("
                        "songlist_name, songlist_url, songlist_creater, songlist_tags, songlist_collect_num, \
                         songlist_comment_num, songlist_share_num, songlist_play_num, songlist_musicname, \
                         songlist_musicsinger) \
                         values ('{songlist_name}', '{songlist_url}', '{songlist_creater}', \
                         '{songlist_tags}', '{songlist_collect_num}', '{songlist_comment_num}', \
                         '{songlist_share_num}', '{songlist_play_num}', '{songlist_musicname}', \
                         '{songlist_musicsinger}');".format(songlist_name=songlist_name, songlist_url=songlist_url, \
                            songlist_creater=songlist_creater, songlist_tags=songlist_tags,\
                            songlist_collect_num=songlist_collect_num, songlist_comment_num=songlist_comment_num, \
                            songlist_share_num=songlist_share_num, songlist_play_num=songlist_play_num,
                            songlist_musicname=songlist_musicname, songlist_musicsinger=songlist_musicsinger))
                    conn.commit()

                except Exception as e:
                    print(e)
            print("获取歌单：" + title + " 数据完毕...")
    except BaseException as e:
        print(e)


def get_song_list(page):
    songListUrl = \
        "http://music.baidu.com/songlist/tag/%E5%85%A8%E9%83%A8?orderType=1&offset={0}&third_type=".format(page)
    print("正在爬取链接: " + songListUrl)
    wbdata = requests.get(songListUrl, headers=headers).content
    soup = BeautifulSoup(wbdata, 'lxml')
    songListLinks = soup.select("p.text-title > a")
    for songListLink in songListLinks:
        title = songListLink.get('title')
        link = "http://music.baidu.com" + songListLink.get('href')
        get_songlist_info(title, link)


def get_page_num():
    url = "http://music.baidu.com/songlist/tag/%E5%85%A8%E9%83%A8?orderType=1&offset=0&third_type="
    wbdata = requests.get(url, headers=headers).content
    soup = BeautifulSoup(wbdata, 'lxml')
    page_num = int(soup.select("div.page-inner > a.page-navigator-number")[-1].get_text())
    return page_num


if __name__ == '__main__':
    # page_num = get_page_num()
    for page in range(50):
        get_song_list(page*20)
    print("爬取数据全部完成")
    cursor.close()
    conn.close()



