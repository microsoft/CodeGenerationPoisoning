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

"""Modulo administrativo."""

from flask import Blueprint, render_template
from flask_login import login_required
from cacao_accounting.decorators import modulo_activo

admin = Blueprint("admin", __name__, template_folder="templates")


@admin.route("/admin")
@admin.route("/ajustes")
@admin.route("/administracion")
@admin.route("/configuracion")
@admin.route("/settings")
@login_required
@modulo_activo("admin")
def admin_():
    """Definición del modulo administrativo."""
    return render_template("admin.html")


@admin.route("/settings/modules")
@login_required
@modulo_activo("admin")
def lista_modulos():
    """Define vista para listar modulos del sistema."""
    return render_template("admin/modulos.html")
