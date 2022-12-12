import io
import os
import random
from flask import Flask, Response, request
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_svg import FigureCanvasSVG


from matplotlib.figure import Figure


app = Flask(__name__)


@app.route("/fas")
def index():
    """ Returns html with the img tag for your plot.
    """
    
    
    # in a real app you probably want to use a flask template.
    return f"""
    <h1>Dashboard</h1>
    
    
    <h3>Ploting the temp data</h3>
    <img src="/image.svg"
         alt="random points as svg"
          
    >
    """
    # from flask import render_template
    # return render_template("yourtemplate.html", num_x_points=num_x_points)




@app.route("/image.svg")
def plot_svg(num_x_points=20):
    """ renders the plot on the fly.
    """
    fig = Figure()
    axis = fig.add_subplot()
    curpath=str(os.path.dirname(os.path.realpath(__file__)))
    path_temp=curpath+"/temperature.txt"
    with open(path_temp) as f:
            lines = f.read().splitlines()
    # print(lines)
    axis.plot(lines[-50:])
#     axis.set_ylabel('V')
#     axis.set_xlabel('t')

# # Turn off tick labels
#     axis.set_yticklabels([])
#     axis.set_xticklabels([])

#     plt.show()
    # plt.axis('off')

    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    return Response(output.getvalue(), mimetype="image/svg+xml")


if __name__ == "__main__":
    app.run(port=5001, debug=True)

