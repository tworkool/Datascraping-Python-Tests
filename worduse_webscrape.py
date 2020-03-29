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


class Site:
    def __init__(self, site_url: str, site_name=None):
        self.url = site_url
        if not site_name:
            self.name = site_url.replace('https://www.', '').split('.')[0].lower()
        else:
            self.name = site_name.lower()
        self.search = []
        self.html = self.get_site()

    @staticmethod
    def init_word_dict(search: list) -> dict:
        word_dict = {}
        for w in search:
            word_dict[w] = 0
        return word_dict

    @staticmethod
    def format_to_readable(inner_html_text: str) -> list:
        word_list = inner_html_text.lower().replace('\n', ' ').split(' ')
        return list(filter(None, word_list))

    def get_site(self):
        site = requests.get(self.url).text
        return BeautifulSoup(site, 'lxml')

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

    def get_frontpage_words(self) -> dict:
        """
        gets all content of main page (main url)
        :return:
        """
        all_articles = self.html.find_all('article')
        frontpage_text = ''
        for article in all_articles:
            frontpage_text += f'{article.text} '
            # article_name = article['aria-label']
        return {'totalWords': self.search_words(frontpage_text)}

    def get_article_words(self, specific_articles=False) -> dict:
        """
        gets all content included in articles which are on the frontpage
        :param specific_articles:
        :return:
        """
        html = self.get_site().find_all('article')
        article_list = []
        for article in html:
            article_name = article['aria-label']
            try:
                # print(article['aria-label'], article_name)
                article_href = article.section.a['href']
                time.sleep(0.1)
                rec_article = Site(article_href, article_name)
                rec_article.specifiy_search(self.search)
                rec_html = rec_article.get_site().find_all('article')

                article_text = ''
                for rec_rec_article in rec_html:
                    article_text += f'{rec_rec_article.text} '

                result = rec_article.search_words(article_text)
                rec_out = {'words': result, 'articleName': rec_article.name, 'articleLink': rec_article.url}
                article_list.append(rec_out)

                print(rec_article.name, result)
            except AttributeError:
                print(f'could not get {article_name}')

        total = self.init_word_dict(self.search)
        for article_info in article_list:
            for search_item in self.search:
                if article_info['words'][search_item] == 0:
                    continue
                total[search_item] += article_info['words'][search_item]

        ret = {
            'totalWords': total
        }
        if specific_articles:
            ret['articles'] = article_list

        return ret


spiegel_search = Site('https://www.spiegel.de/')
spiegel_search.specifiy_search(search_terms)

search_word_struct = {
    'createdAt': datetime.datetime.now(),
    'mainPage': spiegel_search.get_frontpage_words(),
    'mainPageArticles': spiegel_search.get_article_words()
}
db_struct = {
    '_id': spiegel_search.name,
    'url': spiegel_search.url,
    'data': [],
    'createdAt': datetime.datetime.now()
}
if db[col_name].count_documents({'_id': spiegel_search.name}) == 0:
    db[col_name].insert_one(db_struct)

db[col_name].update_one(
    {'_id': spiegel_search.name},
    {'$push': {'data': search_word_struct}}
)
