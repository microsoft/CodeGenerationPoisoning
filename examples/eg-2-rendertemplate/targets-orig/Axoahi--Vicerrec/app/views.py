from flask import Flask


app = Flask(__name__)

from flask import render_template
from flask import request, redirect, url_for
from werkzeug.utils import secure_filename
import os
import ConversionPDF

# Variable que nos marca que se permite subir
app.config["ALLOWED_EXTENSIONS"] = ["pdf"]

# Página index
@app.route("/")
def index():
    return render_template("/public/index.html")


@app.route("/about")
def about():
    return render_template("/public/about.html")


# Página de carga de archivos
@app.route("/upload", methods=['POST', 'GET'])
def loadWebpage():
    return render_template("public/upload.html")


# Procesamiento de subida de archivo, previo a muestra de
@app.route("/complete", methods=['POST', "GET"])
def upload():
    target = os.path.join(app.instance_path)

    # Si no existe el directorio donde dejar los archivos, se crea
    if not os.path.isdir(target):
        os.mkdir(target)

    # Miramos que la lista de archivos a subir no esté vacía
    if request.files['file'].filename == '':
        print("Se debe de subir un archivo por lo menos")
        return redirect(url_for('about'))
    else:
        archiValidos = []
        textoSacado = []
        # Recorremos los archivos, y aplicamos seguridad básica
        for file in request.files.getlist("file"):
            filename = file.filename

            # Si el archivo ha pasado la seguridad básica, se procesa.
            if archivoPermitido(filename):
                # Otra capa de seguridad
                filename = secure_filename(filename)
                destination = "/".join([target, filename])
                # Se guarda el archivo
                file.save(destination)
                # Leemos la información del archivo
                textoSacado.append(ConversionPDF.extraeInfo(destination))
                print(textoSacado)



        return render_template("public/complete.html")


def archivoPermitido(fileName):
    # 1 seg: Se mira que sea un archivo.
    if not "." in fileName:
        return False

    # 2 seg: Se mira la extensión pdf
    ext = fileName.rsplit(".", 1)[1]
    if ext.lower() in app.config["ALLOWED_EXTENSIONS"]:
        return True
    else:
        return False


if __name__ == "__main__":
    app.run(port=5000, debug=True)
