from flask import Flask, render_template
import scraper

app = Flask(__name__)

trademe = "https://www.trademe.co.nz/gaming/playstation-4/consoles"
theList = scraper.process(scraper.scrape(trademe))
mini, maxi, ave = scraper.priceProcess(theList)

@app.route("/")
def home():
    return render_template("index.html", len=len(theList), items=theList, mini=mini, maxi=maxi, ave=ave)
    
if __name__ == "__main__":
    app.run(debug=True)