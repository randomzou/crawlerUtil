# coding：utf8
# @author: zackzou
"""
function: use baidu search the keyword to get the page info and then parse the page to generate the followding info
red_word part : red flag word of the return page
title_abstract part: title and abstract body part of the return page
ads_title_abstract: tilte and abstract ads body part of the return page
side_relate : info in the right side part of the return page
bottom_relate: related search info on the bottom part of the return page

"""

import requests
from bs4 import BeautifulSoup
import re
import json

import os
import logging
class Log(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Log, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_filename='./running.log'):
        log_folder = os.path.split(log_filename)[0]
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        logging.basicConfig(
            filename=log_filename,
            level=logging.DEBUG,
            format='%(asctime)s [%(filename)s:%(lineno)s][%(levelname)s] %(message)s',
            filemode="a",
            datefmt='%Y-%m-%d %H:%M:%S')

    @staticmethod
    def info(msg):
        """"Log info message
            msg: Message to log
        """
        logging.info(msg)
        #sys.stdout.write(msg + "\n")

    @staticmethod
    def warn(msg):
        """Log warn message
           msg: Message to log
        """
        logging.warning(msg)
        #sys.stdout.write(msg + "\n")

    @staticmethod
    def debug(msg):
        """Log warn message
           msg: Message to log
        """
        logging.debug(msg)
        # sys.stdout.write(msg + "\n")

class BaiduCrawler(object):

    Headers_Parameters = {
        'Connection': 'Keep-Alive',
        'Accept': 'text/html, application/xhtml+xml, */*',
        'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'User-Agent': 'Mozilla/6.1 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko'
    }

    def __init__(self, log=None, log_filename=None):
        if log is not None:
            self.log = log
        elif log_filename is not None:
            self.log = Log(log_filename)
        else:
            self.log = Log()

    def deal_exception(self):
        pass

    def get_search_page(self, query):
        # TO_DO : 有些页面没有解析到，比如页面中的百科，贴吧
        search_result = {}
        html = None
        max_retry = 3
        for i in range(0, max_retry):
            try:
                response = requests.get(
                    'https://www.baidu.com/baidu?wd=' + query + '&tn=monline_dg&ie=utf-8',
                    headers=BaiduCrawler.Headers_Parameters, timeout=5)
            except Exception as e:
                search_result["code"] = "404"
                search_result["msg"] = "crawler can't search baidu"
                continue
            if response.ok is False:
                search_result["code"] = "-1"
                search_result["msg"] = "crawler page fail"
                continue
            html = response.text
            if html is not None:
                break
        if html is None:
            search_result["code"] = "-1"
            search_result["msg"] = "crawler page fail"
        else:
            soup = BeautifulSoup(html, 'html.parser')
            search_result["code"] = 0
            search_result["msg"] = "success"
            search_result["query"] = query
            search_result["doc_recall"] = self.get_doc_recall(soup)
            search_result["red_word"] = self.get_red_word(soup)
            search_result["bottom_relate"] = self.get_bottom_relate(soup)
            search_result["side_relate"] = self.get_side_relate(soup)
            search_result["title_abstract"] = self.get_title_abstract(soup, html)
            search_result["ads_title_abstract"] = self.get_ads_title_abstract(soup)
        parse_page_json = json.dumps(search_result)
        #print(search_result)
        #self.log.info(parse_page_json)
        return parse_page_json

    def get_doc_recall(self, soup):
        page_recall_list = soup.select('span[class="nums_text"]')
        if len(page_recall_list) == 0:
            return 0
        text = page_recall_list[0].get_text()
        pattern = re.compile("([0-9]+)")
        doc_recall = pattern.findall(text.replace(",", ""))[0]
        try:
            doc_recall = int(doc_recall)
        except:
            doc_recall = -1
        return doc_recall

    def get_title_abstract(self, soup, html):
        title_abstract_soup = soup.select('div[tpl="se_com_default"]')
        title_list = []
        abstract_list = []
        for tsoup in title_abstract_soup:
            t_title_list = []
            title_soup = tsoup.select('h3[class="t"]')

            if len(title_soup) < 1:
                continue
            for em in title_soup[0]:
                t_title_list.append(em.get_text())
            title_list.append(",".join(t_title_list))
            abstract_soup = tsoup.select('div[class="c-abstract"]')
            if len(abstract_soup) < 1:
                continue
            station = tsoup.select('div[class="c-abstract"]')
            t_abstract_list = []
            for em in station:
                t_abstract_list.append(em.get_text())
            abstract_list.append(",".join(t_abstract_list))
        tilt_abstruct_list = []
        for title, abstract in zip(title_list, abstract_list):
            title_abstract = {}
            title_abstract["title"] = title
            title_abstract["abstract"] = abstract
            tilt_abstruct_list.append(title_abstract)
        return tilt_abstruct_list
    def get_title_abstract_bk(self, soup, html):
        tt = soup.select('div[tpl="se_com_default"]')
        for t in tt:
            print("t->%s"%t)
            print(t.get_text())
        title_list = []
        data_tools = re.findall(u"data-tools='{\"title\":\".*\"\,\"url\":\".*\"}'", html)
        if len(data_tools) > 0:
            for a_data_tool in data_tools:
                # title = re.findall(u"\:.*\,", a_data_tool)
                a_data_tool = a_data_tool[12:-1]
                try:
                    title = json.loads(a_data_tool)['title']
                    title_final = re.sub(u"\:|\"|\,", '', title)
                except:
                    title_final = ""
                title_list.append(title_final)
        station = soup.select('div[class="c-abstract"]')
        # abstract
        abstract_list = []
        for em in station:
            abstract = em.get_text()
            abstract_list.append(abstract.strip())
        # ti,ab写入文件
        tilt_abstruct_list = []
        for title, abstruct in zip(title_list, abstract_list):
            title_abstruct = {}
            title_abstruct["title"] = title
            title_abstruct["abstract"] = abstract
            tilt_abstruct_list.append(title_abstruct)
        return tilt_abstruct_list

    def get_bottom_relate(self, soup):
        bottom_list = []
        rs_soup = soup.select('div[id="rs"]')
        if len(rs_soup) < 1:
            return bottom_list.append("")
        station = soup.select('div[id="rs"]')[0]
        try:
            th_list = station.select('th')
            for th_ in th_list:
                try:
                    th_text = th_.get_text()
                    bottom_list.append(th_text)
                except:
                    continue
        except:
            pass
        return bottom_list

    def get_side_relate(self, soup):
        right_list = []
        try:
            station = soup.select('div[class="opr-recommends-merge-content"]')[0]
            right = station.select('div[class="c-gap-top-small"]')
            for item in right:
                right_list.append(item.get_text())
        except:
            pass
        return right_list

    def get_red_word(self, soup):
        # 标红词写入result
        station = soup.select('h3[class="t"]')
        out_em_list_t = []
        for index, item in enumerate(station):
            piaohong = item.select('em')
            in_em_list_t = []
            for ph in piaohong:
                in_em_list_t.append(ph.get_text())
            if 0 != len(in_em_list_t):
                out_em_list_t.append(','.join(in_em_list_t))
        station = soup.select('div[class="c-abstract"]')
        word_cnt = {}
        for index, item in enumerate(station):
            piaohong = item.select('em')
            in_em_list_b = []
            for ph in piaohong:
                in_em_list_b.append(ph.get_text())
            if 0 != len(in_em_list_b):
                for word in in_em_list_b:
                    word_cnt[word] = word_cnt.get(word, 0) + 1
        return word_cnt

    def get_ads_title_abstract(self, soup):
        content_left_list = soup.select('div[id=content_left]')
        ad_title_list = []
        ad_desc_list = []
        ad_url_list = []
        if len(content_left_list) > 0:
            content_left = content_left_list[0]
            for ad_item in content_left.children:
                if ad_item.name == 'div':
                    if ad_item.get('class') != None and 'c-container' not in ad_item.get('class'):
                        div_list = ad_item.find_all('div', id=re.compile('^\d+$'), class_=re.compile(''))
                        for div_item in div_list:
                            # print div_item
                            inner_title = div_item.div.text
                            inner_content = ''
                            inner_url = ''
                            img_list = div_item.find_all('div', class_=re.compile('general_image_pic'))
                            content_list = div_item.find_all('div', class_=re.compile('c-span-last'))
                            if len(img_list) > 0:
                                try:
                                    inner_url = img_list[0].a.img.get('src')
                                except:
                                    inner_url = ''
                            if len(content_list) > 0:
                                content_array = []
                                for content_item in content_list[0].children:
                                    if content_item.name == 'div':
                                        content_array.append(content_item.text)
                                inner_content = ' '.join(content_array)
                            if len(inner_content) == 0:
                                inner_content = div_item.text
                            if inner_content.startswith(inner_title):
                                inner_content = inner_content[len(inner_title):]

                            ad_title_list.append(inner_title)
                            ad_desc_list.append(inner_content)
                            ad_url_list.append(inner_url)
        ad_title_abstruct_list = []
        for i in range(len(ad_title_list)):
            ad_title = ad_title_list[i].replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
            ad_desc = ad_desc_list[i].replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
            ad_url = ad_url_list[i].replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
            ad_title_abstruct = {}
            ad_title_abstruct["title"] = ad_title
            ad_title_abstruct["desc"] = ad_desc
            ad_title_abstruct["img_url"] = ad_url
            ad_title_abstruct_list.append(ad_title_abstruct)
        return ad_title_abstruct_list

if __name__ == "__main__":
    log_filename = "baiducrawler.log"
    baiduCrawlwer = BaiduCrawler()
    query_list = ["兰蔻"]#, "艾罗伯特irobot", "ysl"]
    for query in query_list:
        response_json = baiduCrawlwer.get_search_page(query)
        obj = json.loads(response_json)
        print(obj)
