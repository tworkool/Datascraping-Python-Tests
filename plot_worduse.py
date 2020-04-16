import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import plot
import random
import configparser
import pymongo
import json
import datetime

config = configparser.ConfigParser()
config.read('config.ini')

with open('settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)
    search_terms = settings['search_terms']
    search_sites = settings['search_sites']

client = pymongo.MongoClient(config['mongo']['connection_string'])
db = client.get_database(config['mongo-testing']['db'])
col_name = config['mongo-testing']['worduse_coll']


def random_color():
    rgb = [random.randrange(160), random.randrange(50, 100), random.randrange(90, 100)]
    return f'hsv({int(260+rgb[0])%360},{int(rgb[1]*1)},{int(rgb[2]*1)})'


def rgb_to_str(r: int, g: int, b: int) -> str:
    return f'rgb({r},{g},{b})'


def set_colors_for_words() -> dict:
    colors = {}
    word_count = len(search_terms)
    color_delta = 255/word_count
    index = 0
    for sw in search_terms:
        # set color for words
         colors[sw] = random_color()
        #col = int(color_delta * index)
        #colors[sw] = rgb_to_str(col, col, col)
        #index += 1

    return colors


data_query = list(db[col_name].find({}))
# fig = go.Figure()
titles = []
lowest_date = data_query[0]['data'][0]['createdAt']
highest_date = data_query[0]['data'][len(data_query[0]['data']) - 1]['createdAt']
for doc in data_query:
    # titles for graphs (subplots)
    titles.append(doc['_id'])
    # select min and max date to have all xaxis the same start and end date
    for day in doc['data']:
        cur_day_date = day['createdAt']
        if cur_day_date > highest_date:
            highest_date = cur_day_date
        else:
            if cur_day_date < lowest_date:
                lowest_date = cur_day_date

# create figure with subplots
fig = make_subplots(rows=len(data_query), cols=1, subplot_titles=tuple(titles))

# index of graph
index = 0
# color struct for words
colors_words = set_colors_for_words()
show_legend_temp = True

for doc in data_query:
    index += 1
    data_x = []
    total_words_data_y = []
    # find x axis data
    for day in doc['data']:
        data_x.append(day['createdAt'])
        day_total = None
        try:
            day_total = day['mainPageArticles']['totalArticles']
        except KeyError:
            pass
        total_words_data_y.append(day_total)

    # add lowest and highest date to have uniform x axis scale for all subplots
    if data_x[len(data_x)-1] < highest_date:
        data_x.append(highest_date)
        total_words_data_y.append(None)
    if data_x[0] > lowest_date:
        data_x.insert(0, lowest_date)
        total_words_data_y.insert(0, None)

    fig.add_trace(
        go.Scatter(
            legendgroup='total articles',
            x=data_x,
            y=total_words_data_y,
            name='total articles',
            showlegend=show_legend_temp,
            line=dict(color='black', width=1),
            mode='lines', # lines+markers
        ),
        row=index,
        col=1,
    )

    for search_word in search_terms:
        data_y = []
        for day in doc['data']:
            word = None
            try:
                word = day['mainPageArticles']['totalWords'][search_word]
            except KeyError:
                pass
            data_y.append(word)
        if lowest_date != doc['data'][0]['createdAt']:
            data_y.insert(0, None)
        if highest_date != doc['data'][len(doc['data']) - 1]['createdAt']:
            data_y.insert(0, None)
        # add trace (as subplot)
        fig.add_trace(
            go.Scatter(
                legendgroup=search_word,
                x=data_x,
                y=data_y,
                name=search_word,
                showlegend=show_legend_temp,
                line=dict(color=colors_words[search_word], width=2),
                mode='lines',
            ),
            row=index,
            col=1,
        )

    # update layout for each subplot
    show_legend_temp = False
    fig['layout'][f'xaxis{index}'].update(dict(
        rangemode='normal',
        showline=True,
        showgrid=False,
        showticklabels=True,
        linecolor='rgb(204, 204, 204)',
        linewidth=2,
        ticks='outside',
        tickfont=dict(
            family='Arial',
            size=12,
            color='rgb(82, 82, 82)',
        ),
        tickangle=-45,
    ))
    fig['layout'][f'yaxis{index}'].update(dict(
        showgrid=True,
        zeroline=False,
        showline=False,
        showticklabels=True,
    ))

'''fig.update_layout(
    xaxis=dict(
        rangemode='normal',
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
        tickangle=-45,
    ),
    yaxis=dict(
        showgrid=False,
        zeroline=False,
        showline=False,
        showticklabels=False,
    ),
    plot_bgcolor='white'
)'''

# update layout for general figure
fig.update_layout(plot_bgcolor='white')

# config_plot = dict({'scrollZoom': True})
# fig.show(config=config_plot)
# fig.show()

# save plot as html file with datetime as name
file_name = str(datetime.datetime.now().replace(microsecond=0)).replace(':', '-').replace(' ', 'T')
plot(fig, filename=f'./backup/{file_name}.html')
