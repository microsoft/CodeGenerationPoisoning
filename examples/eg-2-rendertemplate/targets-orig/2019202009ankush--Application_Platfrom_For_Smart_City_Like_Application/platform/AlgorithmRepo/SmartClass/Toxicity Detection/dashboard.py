import io
import os
import random
from flask import Flask, Response, request
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_svg import FigureCanvasSVG


from matplotlib.figure import Figure


app = Flask(__name__)

lines=""

@app.route("/td")
def index():
    global lines
    curpath=str(os.path.dirname(os.path.realpath(__file__)))
    path_temp=curpath+"/display.txt"

    f=open(path_temp,"r")
    lines=f.readlines()
    f.close()
    """ Returns html with the img tag for your plot.
    """
    
    
    # in a real app you probably want to use a flask template.
    return f"""
    <h1>Dashboard</h1>
    
    
    <h3>Current Status is as follows</h3>
    """+str(lines)
    # from flask import render_template
    # return render_template("yourtemplate.html", num_x_points=num_x_points)





if __name__ == "__main__":
    import webbrowser
    # os.system("google-chrome --no-sandbox 'http://127.0.0.1:5000/'")
    webbrowser.open("http://127.0.0.1:5004/")
    app.run(debug=True)
