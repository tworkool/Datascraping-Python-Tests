import requests
import pymongo
from bs4 import BeautifulSoup
import json
import datetime
import configparser
import time

config = configparser.ConfigParser()
config.read('config.ini')
client = pymongo.MongoClient(config['mongo']['connection_string'])
db = client.get_database(config['mongo-testing']['db'])
col_name = config['mongo-testing']['worduse_coll']


def truncate(fl: float, n: int):
    """Truncates/pads a float f to n decimal places without rounding"""
    s = '{}'.format(fl)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(fl, n)
    i, p, d = s.partition('.')
    return '.'.join([i, (d + '0' * n)[:n]])


# db[col_name].update_one({'_id': 'spiegel'}, {'$pull': {''}})

# search terms (lower case all)
search_terms = [
    'krise',
    'corona',
    'trump',
    'pandemie',
    'covid-19',
    'putin',
    'ausgangssperre',
    'ausgangsbeschränkung'
]

search_sites = [
    {
        'url': 'https://www.spiegel.de/',
        'name': 'spiegel',
        'titleTag': 'title'
    },
    {
        'url': 'https://www.faz.net/aktuell/',
        'name': 'faz',
        'titleTag': 'title'
    }
]


class Site:
    def __init__(self, site_url: str, site_name=None):
        self.url = site_url
        if not site_name:
            self.name = site_url.replace('https://www.', '').split('.')[0].lower()
        else:
            self.name = site_name.lower()
        self.search = []
        self.html = self.get_site()
        self.article_title_tag = 'title'

    def set_article_title_tag(self, tag_name: str):
        self.article_title_tag = tag_name

    @staticmethod
    def init_word_dict(search: list) -> dict:
        word_dict = {}
        for w in search:
            word_dict[w] = 0
        return word_dict

    @staticmethod
    def format_to_readable(inner_html_text: str) -> list:
        word_list = inner_html_text.lower().replace('\n', ' ').replace('/', ' ').split(' ')
        return list(filter(None, word_list))

    def get_site(self):
        site_ = requests.get(self.url).text
        return BeautifulSoup(site_, 'lxml')

    def specifiy_search(self, srch: list):
        self.search = srch

    def search_words(self, inner_html_text: str) -> dict:
        wrd_cnt = self.init_word_dict(self.search)
        wrds = self.format_to_readable(inner_html_text)

        for w in wrds:
            for search_word in self.search:
                if search_word == w:
                    wrd_cnt[search_word] += 1
        return wrd_cnt

    def get_page_words(self, is_main_page: bool) -> dict:
        """
        gets all content of main page (main url)
        :return:
        """
        all_articles = self.html.find_all('article')
        frontpage_text = ''
        for article in all_articles:
            frontpage_text += f'{article.text} '
            # article_name = article['aria-label']
        ret = {'totalWords': self.search_words(frontpage_text)}
        if is_main_page:
            ret['totalArticles'] = len(all_articles)
        return ret

    @staticmethod
    def find_article_link(article, main_url: str):
        article_tags = article.find_all('a')
        for article_tag in article_tags:
            try:
                ret_url = article_tag['href']
                if main_url in ret_url:
                    return ret_url
            except KeyError:
                continue
        return None

    def get_article_name(self, article):
        article_tags = article.find_all('a')
        for article_tag in article_tags:
            try:
                art_name = article_tag[self.article_title_tag]
                return art_name
            except KeyError:
                continue
        return 'no title'

    def get_article_words(self, specific_articles=False) -> dict:
        """
        gets all content included in articles which are on the frontpage
        :param specific_articles:
        :return:
        """
        html = self.html.find_all('article')
        main_page_articles_total = len(html)
        current_article_index = 0
        article_list = []
        for article in html:
            current_article_index += 1
            article_name = self.get_article_name(article)
            # print(article['aria-label'], article_name)
            current_status = f'{current_article_index}/{main_page_articles_total}  |  {truncate((current_article_index / main_page_articles_total)*100.0, 2)}% \t'
            article_url = Site.find_article_link(article, main_url=self.url)

            if not article_url:
                print(current_status, f'could not find reference to article: \"{article_name}\"')
                continue

            time.sleep(0.1)
            rec_article = Site(article_url, article_name)
            rec_article.specifiy_search(self.search)

            result = rec_article.get_page_words(is_main_page=False)
            result['articleName'] = rec_article.name
            result['articleLink'] = rec_article.url
            # TODO: Add number of words for each articles

            article_list.append(result)

            print(current_status, rec_article.url)

        total = self.init_word_dict(self.search)
        for article_info in article_list:
            for search_item in self.search:
                if article_info['totalWords'][search_item] == 0:
                    continue
                total[search_item] += article_info['totalWords'][search_item]

        ret = {
            'totalWords': total,
            'totalArticles': len(article_list)
        }
        if specific_articles:
            ret['articles'] = article_list

        return ret

    def introduce_self(self):
        return f'{self.name} | {self.url}'


for site_item in search_sites:
    site = Site(site_item['url'], site_item['name'])
    site.specifiy_search(search_terms)
    # site.set_article_title_tag(site_item['titleTag'])
    print(f'-> gathering data for {site.introduce_self()}')

    search_word_struct = {
        'createdAt': datetime.datetime.now(),
        'mainPage': site.get_page_words(is_main_page=True),
        'mainPageArticles': site.get_article_words()
    }
    db_struct = {
        '_id': site.name,
        'url': site.url,
        'data': [],
        'createdAt': datetime.datetime.now()
    }

    json_name = f'./backup/{site.name}_dump.json'
    '''
    with open(json_name, 'r') as f:
        data = f.read()
    '''

    db_struct_cpy = db_struct.copy()
    update_time = db_struct_cpy['createdAt']
    update_time = f'ISODate({update_time.isoformat()})'
    db_struct_cpy['createdAt'] = update_time
    search_word_struct_cpy = search_word_struct.copy()
    search_word_struct_cpy['createdAt'] = update_time
    db_struct_cpy['data'].append(search_word_struct_cpy)
    with open(json_name, 'w+', encoding='utf-8') as f:
        json.dump(db_struct_cpy, f, ensure_ascii=False, indent=4)
    print(f'saved backup file: {json_name}')

    if db[col_name].count_documents({'_id': site.name}) == 0:
        db[col_name].insert_one(db_struct)
        print(f'created document for {site.name}')

    db[col_name].update_one(
        {'_id': site.name},
        {'$push': {'data': search_word_struct}}
    )
    print(f'saved mongo document to {col_name}')

# TODO: Save files to backup better
# TODO: Prevent saving data twice within 12 hours
