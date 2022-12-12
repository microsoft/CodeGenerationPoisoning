from flask import Flask, render_template, url_for, request
import numpy as np
import matplotlib.pyplot as plt
import os
import tes

x = np.linspace(-3*np.pi, 3*np.pi, 200)
y = np.sinc(x)
fig, ax = plt.subplots()
ax.plot(x, y)
ax.grid()
plt.show()

project_root = os.path.dirname(__file__)
template_path = os.path.join(project_root, './')
dopchislo1 = 123456;
kolvoznachenii1 = 100

app = Flask(__name__, template_folder=template_path)

@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")
@app.route('/decide', methods=['post', 'get'])
def decide():
    dopchislo = 0
    kolvoznachenii = 0
    if request.method == 'POST':
        dopchislo = request.form.get('dopchislo')  # запрос к данным формы
        kolvoznachenii = request.form.get('kolvoznachenii')  # запрос к данным формы
    if dopchislo == 0:
        dopchislo = dopchislo1
    if kolvoznachenii == 0:
        kolvoznachenii = kolvoznachenii1
    print(kolvoznachenii)

    return render_template("decide.html", param1 = kolvoznachenii, param2 = dopchislo, data = tes.createNewGen(int(kolvoznachenii), dopchislo))
@app.route('/kmeans')
def kmeans():
    return render_template("kmeans.html")

if __name__ == "__main__":
    app.run(debug = True)