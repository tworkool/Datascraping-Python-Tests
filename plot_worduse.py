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

with open('settings.json', 'r') as f:
    settings = json.load(f)
    search_terms = settings['search_terms']
    search_sites = settings['search_sites']

client = pymongo.MongoClient(config['mongo']['connection_string'])
db = client.get_database(config['mongo-testing']['db'])
col_name = config['mongo-testing']['worduse_coll']


def random_color():
    rgb = [random.randrange(360), random.randrange(80, 100), random.randrange(80, 100)]
    return f'hsv({rgb[0]},{rgb[1]},{rgb[2]})'


data_query = list(db[col_name].find({}))
# fig = go.Figure()
titles = []
for doc in data_query:
    titles.append(doc['_id'])
fig = make_subplots(rows=len(data_query), cols=1, subplot_titles=tuple(titles))

index = 0
colors_words = {}
show_legend_temp = True
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
                legendgroup=search_word,
                x=data_x,
                y=data_y,
                name=search_word,
                showlegend=show_legend_temp,
                line=dict(color=colors_words[search_word], width=3),
                mode='lines',
            ),
            row=index,
            col=1,
        )
        # lines+markers
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

fig.update_layout(plot_bgcolor='white')
# config_plot = dict({'scrollZoom': True})
# fig.show(config=config_plot)
# fig.show()
file_name = str(datetime.datetime.now().replace(microsecond=0)).replace(':', '-').replace(' ', 'T')
plot(fig, filename=f'./backup/{file_name}.html')
