# Copyright 2020 William José Moreno Reyes
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Contributors:
# - William José Moreno Reyes

"""Página principal de la aplicación."""

from os import environ
from flask import Blueprint, current_app, render_template, redirect
from flask_login import login_required
from cacao_accounting.database import DBVERSION
from cacao_accounting.version import VERSION


cacao_app = Blueprint("cacao_app", __name__, template_folder="templates")


@cacao_app.route("/app")
@login_required
def pagina_inicio():
    """Esta es la primer pagina mostrada al usuario luego de iniciar sesion."""
    return render_template("app.html")


def bd_actual():
    """Devuelve el motor de base de datos."""
    uri = str(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
    if uri.startswith("sqlite"):
        db_engine = "Sqlite"
    elif uri.startswith("postgresql"):
        db_engine = "Postgresql"
    elif uri.startswith("mysql"):
        db_engine = "MySQL"
    elif uri.startswith("mssql"):
        db_engine = "MS SQL Server"
    elif uri.startswith("mariadb"):
        db_engine = "Mariadb"
    else:
        db_engine = None
    return db_engine


def dev_info():
    """Funcion auxiliar para obtener información del sistema."""
    info = {
        "app": {
            "version": VERSION,
            "dbversion": DBVERSION,
        }
    }
    return info


@cacao_app.route("/development")
@cacao_app.route("/info")
def informacion_para_desarrolladores():
    """Pagina con información para desarrolladores o administradores del sistema."""
    if (current_app.config.get("ENV") == "development") or ("CACAO_TEST" in environ):  # pylint: disable=no-else-return
        return render_template("development.html", info=dev_info(), db=bd_actual(), current_app=current_app)
    else:
        return redirect("/login")
