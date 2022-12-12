from flask import Flask, request, render_template, session, redirect, send_file, make_response
import numpy as np
import pandas as pd
import io
from io import BytesIO

import matplotlib as mpl

## agg backend is used to create plot as a .png file
mpl.use('agg')

import matplotlib.pyplot as plt


app = Flask(__name__)  # Instantiate a new web application called `app`, with `__name__` representing the current file

data=pd.read_csv(r'/Users/kazba1/Downloads/Master-list-numeric.csv')
df=pd.DataFrame(data)
df=df.drop("Unnamed: 0", axis=1)
df=df.replace(" ",np.nan)
df=df[df['Target business description'].notnull()]
df=df.reset_index(drop=True)

@app.route("/", methods=["GET","POST"])
def index():
    return render_template('index.html')

@app.route("/result", methods=["POST"])
def result():
    if request.method == 'POST':
        keyword = request.form.get("keyword")
        Revenue_Turnover = request.form.get("Revenue_Turnover")
        EBITDA = request.form.get("EBITDA")
        Net_profit = request.form.get("Net_profit")
        Enterprise_value = request.form.get("Enterprise_value")
        keyword = keyword.split()
        global df
        df['Keyword count'] = 0
        for j in range(len(keyword)):
            df.loc[(df['Target business description'].str.contains(keyword[j])), 'Keyword count'] += 1
        df['variable difference %'] = 0
        if Revenue_Turnover != "":
            df = df.dropna(subset=['Pre-deal target operating revenue/turnover'])
            Revenue_Turnover = int(Revenue_Turnover)
            df['Variable difference %'] += ((df['Pre-deal target operating revenue/turnover'].astype(float) - Revenue_Turnover) / Revenue_Turnover).abs() * 100
        if EBITDA != "":
            df = df.dropna(subset=['Pre-deal target EBITDA'])
            EBITDA = int(EBITDA)
            df['Variable difference %'] += ((df['Pre-deal target EBITDA'].astype(float) - EBITDA) / EBITDA).abs() * 100
        if Net_profit != "":
            df = df.dropna(subset=['Net profit'])
            Net_profit = int(Net_profit)
            df['Variable difference %'] += ((df['Net profit'].astype(float) - Net_profit) / Net_profit).abs() * 100
        if Enterprise_value != "":
            df = df.dropna(subset=['Enterprise value'])
            Enterprise_value = int(Enterprise_value)
            df['Variable difference %'] += ((df['Enterprise value'].astype(float) - Enterprise_value) / Enterprise_value).abs() * 100
        df = df.sort_values(by=['Keyword count', 'variable difference %'], ascending=[False, True])
        df['Variable difference %']=df['Variable difference %'].round(2)
        df = df.reset_index(drop=True)
        df = df[:30]
        pd.options.display.float_format = "{:.1f}".format
        global data_to_plot
        data_to_plot = [df['Enterprise value'], df['Pre-deal target operating revenue/turnover'],df['Pre-deal target EBITDA'],
                        df['Net profit'], df['Deal value']]
        df=df.rename(columns={"Deal value": "Deal value th EUR", "Enterprise value": "Deal enterprise value th EUR", "Net profit": "Target net profit th EUR", "Pre-deal target EBITDA": "Target EBITDA th EUR", "Pre-deal target operating revenue/turnover": "Target operating revenue/turnover th EUR"})
        des = df[['Deal enterprise value th EUR', 'Target operating revenue/turnover th EUR', 'Target EBITDA th EUR',
                  'Target net profit th EUR', 'Deal value th EUR']].describe()
        return render_template('simple.html', tables=[df.to_html(classes='data')], tables1=[des.to_html(classes='data')], titles=df.columns.values)

@app.route('/do_box_1/')
def do_box_plot():
    # Create a figure instance
    fig = plt.figure(1, figsize=(9, 6))

    # Create an axes instance
    ax = fig.add_subplot(111)

    # Create the boxplot
    bp = ax.boxplot(data_to_plot, patch_artist=True)

    plt.yscale("log")

    for box in bp['boxes']:
        # change outline color
        box.set(color='#7570b3', linewidth=2)
        # change fill color
        box.set(facecolor='#1b9e77')

    ## change color and linewidth of the whiskers
    for whisker in bp['whiskers']:
        whisker.set(color='#7570b3', linewidth=2)

    ## change color and linewidth of the caps
    for cap in bp['caps']:
        cap.set(color='#7570b3', linewidth=2)

    ## change color and linewidth of the medians
    for median in bp['medians']:
        median.set(color='#b2df8a', linewidth=2)

    ## change the style of fliers and their fill
    for flier in bp['fliers']:
        flier.set(marker='o', color='#e7298a', alpha=0.5)

    ax.set_xticklabels(['Enterprise value', 'Revenue/Turnover', 'EBITDA', 'Net profit', 'Deal value'])
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()
    bytes_image = io.BytesIO()
    plt.savefig(bytes_image, format='png')
    bytes_image.seek(0)
    return send_file(bytes_image, mimetype='image/png')