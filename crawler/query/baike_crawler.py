import os
import urllib
from bs4 import BeautifulSoup
import traceback
import time
import re
import codecs
import logging
from concurrent.futures import ThreadPoolExecutor
logger = logging.getLogger(__name__)
local_file = os.path.split(__file__)[-1]
logging.basicConfig(
    format='%(asctime)s : %(filename)s : %(funcName)s : %(levelname)s : %(message)s',
    level=logging.DEBUG)

class Thread_Pool():
    def __init__(self, max_thread_num):
        self.max_thread_num = max_thread_num
    def run(self, function, args):
        with ThreadPoolExecutor(self.max_thread_num) as executor:
            executor.map(function, args)


def run_thread_pool(*dargs, **dkargs):
    def wrapper(func):
        def inner(*args):
            thread_pool = Thread_Pool(*dargs)
            thread_pool.run(func, *args)
        return inner
    return wrapper


KUOHAO_PATTERN = re.compile("\(.*?\)|\[.*?\]|（.*?）|（.*?\)|\(.*?）")


def remove_parentheses(entity):
    keys = {'［', '(', '[', '（'}
    symbol = {'］':'［', ')':'(', ']':'[', '）':'（'}
    stack = []
    remove = []
    for index, s in enumerate(entity):
        if s in keys:
            stack.append((s, index))
        if s in symbol:
            if not stack:continue
            temp_v, temp_index = stack.pop()
            if entity[index-1] == '\\':
                t = entity[temp_index-1:index+1]
                remove.append(t)
            else:
                remove.append(entity[temp_index:index+1])

    for r in remove:
        entity = entity.replace(r, '')
    return entity


def url_parse(url, word):
    word = urllib.parse.quote(word)
    url = url.format(a=word)
    return url


def get_text_from_tag(tag):
    return tag.get_text()


def get_info_box(soup):
    new_dict = dict()
    # base_info
    base_info = soup.find(attrs={"class": "basic-info cmn-clearfix"})
    if base_info is not None:
        all_name = base_info.find_all(attrs={"class": "basicInfo-item name"})
        all_value = base_info.find_all(attrs={"class": "basicInfo-item value"})
        if len(all_name) != len(all_value):
            logging.error('name and value not equal')
            raise Exception('name and value not equal')
        info_size = len(all_name)
        for i in range(info_size):
            name, value = all_name[i], all_value[i]
            name, value = name.get_text(strip=True).replace(u'\xa0', ''), value.get_text(strip=True)
            new_dict[name] = value
    return new_dict


def get_description(soup):
    new_dict = dict()
    desc_label = soup.select('meta[name="description"]')
    if not desc_label: new_dict['description'] = ''
    else:
        description = soup.select('meta[name="description"]')[0].get('content')
        new_dict['description'] = description
    return new_dict


def baike_synonym_detect(word_code_list):
    out_path = '../output/baike_synonym.txt'
    if os.path.exists(out_path):
        os.remove(out_path)

    multi_thread_search(word_code_list)


@run_thread_pool(50)
def multi_thread_search(params):
    baike_search(params)


def baike_search(params):
    key_word, word_code, outfile = params
    key_word = remove_parentheses(key_word)
    fw = None
    if outfile is not None:
        fw = open(outfile, 'a', encoding='utf8')
    try:
        base_url = 'https://baike.baidu.com/item/{a}'
        url = url_parse(base_url, key_word)
        response = urllib.request.urlopen(url)
        data = response.read()
        soup = BeautifulSoup(data,'html.parser')

        item_json = dict()

        des_dict = get_description(soup)
        item_json.update(des_dict)

        info_box_dict = get_info_box(soup)
        item_json.update(info_box_dict)

        synonym_list = get_synonym(item_json)
        if len(synonym_list) > 0 and fw is not None:
            write_line = word_code + '\t' + key_word + '\t' + '|'.join(synonym_list) + '\n'
            fw.write(write_line)
            fw.close()

        logger.debug(' input word = {a}, find {b} synonyms:{c}...'.format(a=key_word,b=len(synonym_list),c=synonym_list))
        return synonym_list

    except Exception:
        logger.error(' input word = {a}, occur an error!'.format(a=key_word))
        traceback.print_exc()
    time.sleep(0.1)


def get_synonym(baike_json):
    info_key = ['别称', '英文名称', '又称', '英文别名', '西医学名', "外文名",'又名','中文名']
    pattern_list = ['俗称', '简称', '又称','又称为', '简称为', '也叫','别称']

    info_set = set()
    for key in info_key:
        if key in baike_json:
            value = baike_json[key]
            value = re.sub(KUOHAO_PATTERN, "", value)
            if len(value) < 1:
                continue
            if value[-1] == '等':
                value = value[:-1]
            value = seg(value)
            info_set = info_set | set(value)

    description = baike_json['description']
    for p in pattern_list:
        pattern = r'' + p
        result = re_match(pattern, description)
        for r in result:
            value = seg(r)
            info_set = info_set | set(value)

    info_set = [s.strip().replace(u'\xa0', '').replace('"', '').replace('“', '').replace('”', '').
                    replace('（', '').replace('：', '')   for s in info_set]
    return info_set


def re_match(word, text):
    p_str = r'{a}(.+?)[，。）\s)（(、]'.format(a=word)
    pattern = re.compile(p_str)
    result = re.findall(pattern, text)
    return result

def seg(text):
    segment = [',', '，', '、', '；']
    current_seg = '&&'
    for seg in segment:
        if seg in text:
            current_seg = seg
    return text.split(current_seg)

def load_product_word(candidate_product_word_path):
    word_pair_list = []
    with codecs.open(candidate_product_word_path, "r", encoding="utf8") as fr:
        for i, line in enumerate(fr):
            item = line.strip().split("\t")
            word = item[0]
            word_pair_list.append([word, str(i)])
    return word_pair_list
def run_multi_search():
    candidate_product_word_path = "/Users/deep/Workspace/PycharmProjects/synonym_detection/input/product_word/recrawler.txt"
    outfile = candidate_product_word_path + '.search'
    word_pair_list = load_product_word(candidate_product_word_path)
    for idx, word_pair in enumerate(word_pair_list):
        # if int(word_pair[1]) < 24969:
        #    continue
        # if getLetterRatio(word_pair[0].lower()) < 0.7:
        #    #print("%s->%s"%(word_pair[0], getLetterRatio(word_pair[1].lower())))
        #    continue
        multi_thread_search((word_pair + [None], None))


if __name__ == '__main__':
    print(baike_search(['土豆', '1' ,None]))
    #run_multi_search()