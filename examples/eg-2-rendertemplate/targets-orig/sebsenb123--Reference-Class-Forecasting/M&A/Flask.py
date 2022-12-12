from flask import Flask, request, render_template, session, redirect
import numpy as np
import pandas as pd

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
        if Revenue_Turnover != "n.a.":
            df = df.dropna(subset=['Pre-deal target operating revenue/turnover'])
            Revenue_Turnover = int(Revenue_Turnover)
            df['variable difference %'] += ((df['Pre-deal target operating revenue/turnover'].astype(int) - Revenue_Turnover) / Revenue_Turnover).abs() * 100
        if EBITDA != "n.a.":
            df = df.dropna(subset=['Pre-deal target EBITDA'])
            EBITDA = int(EBITDA)
            df['variable difference %'] += ((df['Pre-deal target EBITDA'].astype(int) - EBITDA) / EBITDA).abs() * 100
        if Net_profit != "n.a.":
            df = df.dropna(subset=['Net profit'])
            Net_profit = int(Net_profit)
            df['variable difference %'] += ((df['Net profit'].astype(int) - Net_profit) / Net_profit).abs() * 100
        if Enterprise_value != "n.a.":
            df = df.dropna(subset=['Enterprise value'])
            Enterprise_value = int(Enterprise_value)
            df['variable difference %'] += ((df['Enterprise value'].astype(int) - Enterprise_value) / Enterprise_value).abs() * 100
        df = df.sort_values(by=['Keyword count', 'variable difference %'], ascending=[False, True])
        df['variable difference %']=df['variable difference %'].round(2)
        df = df.reset_index(drop=True)
        df = df[:30]
        df = df.astype(str).apply(lambda x: x.str[:70])
        for i in range(0, 30):
            if len(df.loc[(i, 'Target business description')]) == 70:
                df.loc[(i, 'Target business description')] = df.loc[(i, 'Target business description')] + "..."
        return render_template('simple.html', tables=[df.to_html(classes='data')], titles=df.columns.values)




