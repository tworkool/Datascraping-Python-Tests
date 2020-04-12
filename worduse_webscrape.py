"""
Author: Oliver Tworkowski
This script searches for words on a website which has <article> tags. This applies to almost all newspaper websites
To add or remove websites and words to be searched for, modify the settings.json file
"""

import requests
import pymongo
from bs4 import BeautifulSoup
import json
import datetime
import configparser
import time
import shutil
from os import system
import random

config = configparser.ConfigParser()
config.read('config.ini')
client = pymongo.MongoClient(config['mongo']['connection_string'])
db = client.get_database(config['mongo-testing']['db'])
col_name = config['mongo-testing']['worduse_coll']


# Stackoverflow Solution
def truncate(fl: float, n: int):
    """
    Truncates/pads a float f to n decimal places without rounding
    """
    s = '{}'.format(fl)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(fl, n)
    i, p, d = s.partition('.')
    return '.'.join([i, (d + '0' * n)[:n]])


# Stackoverflow Solution
def print_progress_bar(iteration, total, prefix='', suffix='', usepercent=True, decimals=1, fill='█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        usepercent  - Optoinal  : display percentage (Bool)
        decimals    - Optional  : positive number of decimals in percent complete (Int), ignored if usepercent = False
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    # length is calculated by terminal width
    twx, twy = shutil.get_terminal_size()
    length = twx - 1 - len(prefix) - len(suffix) - 4
    if usepercent:
        length = length - 6
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    # process percent
    if usepercent:
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='', flush=True)
    else:
        print('\r%s |%s| %s' % (prefix, bar, suffix), end='', flush=True)
    # Print New Line on Complete
    if iteration == total:
        print(flush=True)


# load settings file
with open('settings.json', 'r') as f:
    settings = json.load(f)
    search_terms = settings['search_terms']
    search_sites = settings['search_sites']


def random_color():
    rgb = [random.randrange(360), random.randrange(80, 100), random.randrange(80, 100)]
    return f'hsv({rgb[0]},{rgb[1]},{rgb[2]})'


print('display graph? (y/n): ')
display_graph = input().lower()
if display_graph == 'y':
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    data_query = list(db[col_name].find({}))
    # fig = go.Figure()
    titles = []
    for doc in data_query:
        titles.append(doc['_id'])
    fig = make_subplots(rows=len(data_query), cols=1, subplot_titles=tuple(titles))

    index = 0
    colors_words = {}
    for word in search_terms:
        colors_words[word] = random_color()
    for doc in data_query:
        index += 1
        data_x = []
        for day in doc['data']:
            data_x.append(day['createdAt'])
        for search_word in search_terms:
            data_y = []
            for day in doc['data']:
                word = None
                try:
                    word = day['mainPageArticles']['totalWords'][search_word]
                except KeyError:
                    pass
                data_y.append(word)

            fig.add_trace(
                go.Scatter(
                    x=data_x,
                    y=data_y,
                    name=search_word,
                    line=dict(color=colors_words[search_word], width=3),
                    mode='lines'
                ),
                row=index,
                col=1,
            )

    fig.update_layout(
        xaxis=dict(
            showline=True,
            showgrid=True,
            showticklabels=True,
            linecolor='rgb(204, 204, 204)',
            linewidth=2,
            ticks='outside',
            tickfont=dict(
                family='Arial',
                size=12,
                color='rgb(82, 82, 82)',
            ),
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            showticklabels=False,
        ),
        plot_bgcolor='white'
    )
    fig.update_layout(xaxis={'type': 'date'})
    # config = dict({'scrollZoom': True})
    fig.show(config=config)


class Site:
    """
    handle requests and website information
    """

    def __init__(self, site_url: str, site_name=None):
        self.url = site_url
        if not site_name:
            self.name = site_url.replace('https://www.', '').split('.')[0].lower()
        else:
            self.name = site_name.lower()
        self.search = []
        self.html = self.get_site()
        self.article_title_tag = 'title'
        self.is_mainpage = False

    def set_article_title_tag(self, tag_name: str):
        """
        provide the tag name inside the article tag if given (doesn't influence result if no title found)
        :param tag_name:
        :return:
        """
        self.article_title_tag = tag_name

    def set_as_mainpage(self):
        """
        sets the current instance as main page (front page of newspaper)
        :return:
        """
        self.is_mainpage = True

    @staticmethod
    def init_word_dict(search: list) -> dict:
        """
        initiates a dict (probably obsolete)
        :param search:
        :return:
        """
        word_dict = {}
        for w in search:
            word_dict[w] = 0
        return word_dict

    @staticmethod
    def format_to_readable(inner_html_text: str) -> list:
        """
        converts a whole article inner html text into a beautiful list of words :)
        :param inner_html_text:
        :return:
        """
        word_list = inner_html_text.lower().replace('\n', ' ').replace('/', ' ').split(' ')
        return list(filter(None, word_list))

    def get_site(self):
        """
        gets website content and handles exceptions
        :return:
        """
        site_response = None
        while not site_response:
            try:
                site_response = requests.get(self.url, timeout=15)
                print(
                    f'status code: {site_response.status_code}, response time(s): {site_response.elapsed.total_seconds()}')
                site_response.close()
                if site_response.status_code == 404:
                    print('404 Error')
                    return BeautifulSoup("", 'lxml')
            except requests.exceptions.ConnectionError:
                site_response = None
                print('CONNECTION ERROR!, retry in 5 seconds')
                time.sleep(5)
            except requests.exceptions.ReadTimeout:
                site_response = None
                print('Read Timeout, retry in 2 seconds')
                time.sleep(2)
        return BeautifulSoup(site_response.text, 'lxml')

    def specifiy_search(self, srch: list):
        """
        sets searchlist for this instance
        :param srch:
        :return:
        """
        self.search = srch

    def search_words(self, inner_html_text: str) -> dict:
        """
        searches website for words
        :param inner_html_text:
        :return:
        """
        wrd_cnt = self.init_word_dict(self.search)
        wrds = self.format_to_readable(inner_html_text)

        for w in wrds:
            for search_word in self.search:
                if search_word == w:
                    wrd_cnt[search_word] += 1
        return wrd_cnt

    def get_page_words(self) -> dict:
        """
        counts the words for a website that have been found
        :return:
        """
        all_articles = self.html.find_all('article')
        frontpage_text = ''
        for article in all_articles:
            frontpage_text += f'{article.text} '
            # article_name = article['aria-label']
        ret = {'totalWords': self.search_words(frontpage_text)}
        if self.is_mainpage:
            ret['totalArticles'] = len(all_articles)
        return ret

    @staticmethod
    def find_article_link(article, main_url: str):
        """
        tries to find an article reference in article tag
        :param article: BeautifulSoup Pageelement <article>
        :param main_url: the main page url
        :return:
        """
        article_tags = article.find_all('a')
        for article_tag in article_tags:
            try:
                ret_url = str(article_tag['href'])
                parse = ret_url.split('.')
                if ret_url[0] == '/':
                    ret_url = main_url + ret_url[1:]
                link_ending = parse[len(parse) - 1]
                if (link_ending == 'html' or link_ending == 'htm' or ('.' not in link_ending)) and (
                        main_url in ret_url):
                    return ret_url
            except KeyError:
                continue
        return None

    def get_article_name(self, article):
        """
        tries to get the articles name
        :param article: BeautifulSoup Pageelement <article> tag
        :return:
        """
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
            article_url = Site.find_article_link(article, main_url=self.url)

            if not article_url:
                print(f'could not find reference to article: \"{article_name}\"')
            else:

                time.sleep(0.1)
                rec_article = Site(article_url, article_name)
                rec_article.specifiy_search(self.search)

                result = rec_article.get_page_words()
                result['articleName'] = rec_article.name
                result['articleLink'] = rec_article.url
                # TODO: Add number of words for each articles

                article_list.append(result)
                print(rec_article.url)

            print_progress_bar(current_article_index, main_page_articles_total,
                               prefix=f'{current_article_index}/{main_page_articles_total}')
            # new line
            print()

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


continue_flag = ''
for site_item in search_sites:
    now = datetime.datetime.now()
    site_item_name = None
    site_item_url = ''
    try:
        site_item_name = site_item['name']
        site_item_url = site_item['url']
    except KeyError:
        print('settings file keys cannot be found')
    last_updated = db[col_name].find_one({'_id': site_item_name})['updatedAt']
    if last_updated > (now - datetime.timedelta(hours=3)):
        print(
            f'{site_item_name} was updated less than 3 hours ago: {last_updated}, please run again at {last_updated + datetime.timedelta(hours=3)}')
        time.sleep(2)
        continue

    site = Site(site_item_url, site_item_name)
    site.specifiy_search(search_terms)
    site.set_as_mainpage()
    # site.set_article_title_tag(site_item['titleTag'])
    print(f'-> gathering data for {site.introduce_self()}')

    search_word_struct = {
        'createdAt': now,
        'mainPage': site.get_page_words(),
        'mainPageArticles': site.get_article_words()
    }
    now = datetime.datetime.now()
    db_struct = {
        '_id': site.name,
        'url': site.url,
        'data': [],
        'createdAt': now,
        'updatedAt': now
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
    db_struct_cpy['updatedAt'] = update_time
    search_word_struct_cpy = search_word_struct.copy()
    search_word_struct_cpy['createdAt'] = update_time
    db_struct_cpy['data'].append(search_word_struct_cpy)
    with open(json_name, 'w+', encoding='utf-8') as f:
        json.dump(db_struct_cpy, f, ensure_ascii=False, indent=4)
    print(f'saved backup file: {json_name}')

    if continue_flag != 'yy':
        print('continue saving to database? (y / n / yy = yes for all upcoming): ')
        continue_flag = str(input()).lower()
        if continue_flag == 'yy':
            print('will save to database for all!')

    if continue_flag == 'y' or continue_flag == 'yy':
        if db[col_name].count_documents({'_id': site.name}) == 0:
            db[col_name].insert_one(db_struct)
            print(f'created document for {site.name}')

        db[col_name].update_one(
            {'_id': site.name},
            {
                '$push': {'data': search_word_struct},
                '$set': {'updatedAt': now}
            }
        )
        print(f'saved mongo document {site.name} to {col_name}')
    else:
        print('will not save to database')

    time.sleep(3)
    print()

# TODO: Save files to backup better
# TODO: Prevent saving data twice within 12 hours
