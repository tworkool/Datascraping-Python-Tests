import requests
import pymongo
from bs4 import BeautifulSoup
import json
import datetime
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
client = pymongo.MongoClient(config['mongo']['connection_string'])
db = client.get_database(config['mongo-testing']['db'])
col_name = config['mongo-testing']['covid_coll']

today = datetime.date.today()

if db[col_name].count_documents({'_id': str(today)}) == 0:

    site = requests.get('https://www.worldometers.info/coronavirus/').text
    html_parsed = BeautifulSoup(site, 'lxml')
    table = html_parsed.find('table', id="main_table_countries_today")
    # table_heading = str(table.thead.text).rstrip()
    '''table_heading = ['Country, Other', 'Total Cases', 'New Cases', 'Total Deaths', 'New Deaths', 'Total Recovered',
                     'Active Cases', 'Serious, Critical', 'Total Cases/ 1M Population', 'Deaths/ 1M Population',
                     'First Case']'''
    table_heading = ['country', 'totalCases', 'newCases', 'totalDeaths', 'newDeaths', 'totalRecovered',
                     'activeCases', 'criticalCases', 'totalCases_for1M', 'totalDeaths_for1M',
                     'firstCase']
    table_body = table.tbody
    content = []
    # data = []
    rows = table_body.find_all('tr')
    for row in rows:
        entry = {}
        cols = row.find_all('td')
        cols = [ele.text.replace(',', '').replace('+', '').strip() for ele in cols]
        if len(cols) != len(table_heading):
            print(f'FAILED to get data for {entry}')
            break
        for i in range(len(table_heading)):
            if i == 8 or i == 9:
                continue
            cur_value = cols[i]
            try:
                if '.' in cols[i]:
                    cur_value = float(cols[i])
                else:
                    cur_value = int(cols[i])
            except ValueError:
                pass
            entry[table_heading[i]] = cur_value
        print(f'got data for {entry[table_heading[0]]} successfully')
        content.append(entry)
        # data.append([ele for ele in cols])

    '''table_content = str(table.tbody.text).replace(',', '').replace('+', '').splitlines()
    table_content.pop(0)
    content = []

    index = 1
    while index < len(table_content):
        row = {}
        for col in table_heading:
            row[col] = table_content[index]
            if col == 'Deaths/ 1M Population':
                # skip empty field after this column
                index += 1
            index += 1
        # Error Handling
        try:
            int(row[table_heading[0]])
        except ValueError:
            print(f'got data for {row[table_heading[0]]} successfully')
        else:
            print(f'FAILED to get data for {row}')
            break

        content.append(row)
        # skip empty fields
        index += 2
    
    '''

    # now = datetime.datetime.now()
    # save_file_name = f'{now.date()}T{now.hour}-{now.minute}_covid_dump.json'

    # dump latest data
    with open('last_dump.json', 'w+', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

    mongo_format = {
        '_id': str(today),
        'updatedAt': datetime.datetime.now(),
        'data': content
    }
    db[col_name].insert_one(mongo_format)
else:
    print('already filled data for today')
