from jinja2 import Environment, PackageLoader, select_autoescape

from datetime import datetime
import re

from lxml import html
from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.embed import components
from bokeh.document.document import Document
import numpy as np
from scipy.optimize import curve_fit

#import numpy as np
import pandas as pd
import holoviews as hv

import array

from .database import connection

hv.extension('bokeh')

#env = Environment(
#    loader=PackageLoader('richardmartinotron', 'templates'),
#    autoescape=select_autoescape(['html', 'xml'])
#)

class Analyser:
    def __init__(self):
        self.db_table_name = ""

    def get_all_cursor(self):
        cursor = connection.cursor()
        cursor.execute("""
                    SELECT 
                        date,
                        title,
                        content,
                        url
                    FROM {};
                """.format(self.db_table_name))
        return cursor

    def count_words(self):
        cursor = self.get_all_cursor()

        data = []

        for date, title, content, url in cursor.fetchall():
            if content:
                fragment = html.fromstring(content)
                count = len(re.findall(r'\w+', fragment.text_content()))
            else:
                count = 0
            print("{}: {}".format(url, count))
            data.append({
                'date': date,
                'title': title,
                'content': content,
                'url': url,
                'count': count
            })
        return data

    def count_exclamation_marks(self):
        cursor = self.get_all_cursor()
        data = []
        for date, title, content, url in cursor.fetchall():
            if content:
                fragment = html.fromstring(content)
                count = fragment.text_content().count("!")
            else:
                count = 0
            print("{}: {}".format(url, count))
            data.append({
                'date': date,
                'title': title,
                'content': content,
                'url': url,
                'count': count
            })
        return data


class JournalDeMontreal(Analyser):
    TABLE_NAME = "journal_montréal"

    def __init__(self):
        self.db_table_name = JournalDeMontreal.TABLE_NAME

    def count_words(self):
        results = super().count_words()
        #output_file("output/count.html")

        source = ColumnDataSource(data=dict(
            x=[datetime.strptime(result['date'], "%Y-%m-%d") for result in results],
            y=[result['count'] for result in results],
            title=[result['title'] for result in results],
            url=[result['url'] for result in results],
            date=[result['date'] for result in results]
        ))

        hover = HoverTool(tooltips=[
            ("title", "@title"),
            ("url", "@url"),
            ("date", "@date")
        ])

        p = figure(
            title="Nombre de mots des articles de Richard Martineau",
            x_axis_label="Articles écrits",
            x_axis_type="datetime",
            y_axis_label="Nombre de mots",
            tools=[hover]
        )

        #date_data = [datetime.strptime(result['date'], "%Y-%m-%d") for result in results]
        #count_data = [result['count'] for result in results]

        #p.line(date_data, count_data, legend="Mots", line_width=2)

        #p.circle('x', 'y', size=5, source=source)

        #script, div = components(p)
        #print("===")
        #print(script)
        #print(div)

        #show(p)

    def count_exclamation_marks(self):
        results = super().count_exclamation_marks()
        #output_file("output/exclamation.html")

        source = ColumnDataSource(data=dict(
            x=[datetime.strptime(result['date'], "%Y-%m-%d") for result in results],
            y=[result['count'] for result in results],
            title=[result['title'] for result in results],
            url=[result['url'] for result in results],
            date=[result['date'] for result in results]
        ))

        hover = HoverTool(tooltips=[
            ("title", "@title"),
            ("url", "@url"),
            ("date", "@date")
        ])

        p = figure(
            title="Nombre de «!» par article de Richard Martineau",
            x_axis_label="Articles écrits",
            x_axis_type="datetime",
            y_axis_label="Nombre de points d'exclamation",
            tools=[hover]
        )

        date_count = pd.DataFrame({
            "date": [datetime.strptime(result['date'], "%Y-%m-%d") for result in results],
            "count": [result['count'] for result in results]
        })

        scatter_style_opts = dict(color_index=2, size_index=3, scaling_factor=50)
        scatter_plot_opts = dict(width=500, height=300, size=150)
        scatter = hv.Scatter(
            date_count,
            kdims=['date'],
            vdims=['count'],
            group='Nombre de «!» par article de Richard Martineau'
        )(style={
            #'color': 'k',
            #'marker': 's',
            #'size': 10
            'plot': scatter_plot_opts,
            'style': scatter_style_opts
        })

        ordinal_dates = [datetime.strptime(result['date'], "%Y-%m-%d").toordinal() for result in results]
        min_ordinal_dates = min(ordinal_dates)
        time_frame = pd.DataFrame({
            "date": [ordinal_date - min_ordinal_dates for ordinal_date in ordinal_dates],
            "count": [result['count'] for result in results]
        })

        layout = scatter

        #renderer = hv.renderer('bokeh')
        #hvplot = renderer.get_plot(layout)
        #html = renderer.figure_data(hvplot)
        print(html)

        renderer = hv.renderer('bokeh')
        #renderer(layout)
        #doc = renderer.server_doc(layout)  # type: Document
        #doc.
        #print(doc)
        server = renderer.app(layout, show=True, new_window=True)

        #date_data = [datetime.strptime(result['date'], "%Y-%m-%d") for result in results]
        #count_data = [result['count'] for result in results]

        #p.line(date_data, count_data, legend="Points d'exclamations", line_width=2)

        #p.circle('x', 'y', size=5, source=source)

        #script, div = components(p)
        #print("===")
        #print(script)
        #print(div)

        #print(np.asarray(range(1, len(results) + 1)), np.asarray([result['count'] for result in results]))
        #fitted = fit_func(np.asarray(range(1, len(results) + 1)), np.asarray([result['count'] for result in results]))
        #print(fitted)

        #show(p)


def fit_func(xdata, ydata):

    def func(x,a,c):
        return a*(x**2)+a*x+c

    y = func(xdata, 1, 1)
    popt, pcov = curve_fit(func, xdata, ydata)
    new_x = np.arange(0,10,2)
    new_y = func(new_x,*popt)

    return (new_x, new_y)
