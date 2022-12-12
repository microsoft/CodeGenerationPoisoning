import calcularfactura
from flask import Flask, render_template, request, Markup, session
import pandas as pd

app = Flask(__name__)

app.secret_key = "F4ctur4sEY2O2O"

@app.route("/factura", methods=["GET", "POST"])

def factura():
    if request.method=="POST":
        f_fin = request.form["fechafin"]
        f_inicio = request.form["fechainicio"]
        fecha_f = f_fin.split("-")[2] + "-" + f_fin.split("-")[1]
        fecha_i = f_inicio.split("-")[2] + "-" + f_inicio.split("-")[1]
        tabla = calcularfactura.calcularfactura(fecha_i, fecha_f)
    else:
        tabla = calcularfactura.calcularfactura("27-03", "24-04")
    tabla.append(tabla.agg(['sum']))
    tabla.iloc[-1, tabla.columns.get_loc("Resource Name")] = "Total"
    tabla["Total"] = "$ " + tabla["Total"].astype(str)
    tabla.reset_index(drop=True, inplace=True)
    codigo = pd.DataFrame.to_html(tabla, index=False)
    session["codigo"] = codigo
    return render_template("factura.html", codigo = Markup(codigo))

@app.route("/imprimir", methods=["POST"])

def imprimir():
    codigo = session["codigo"]
    return render_template("imprimir.html", codigo = Markup(codigo))
