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

"""Modulo de Compras."""

from flask import Blueprint, render_template
from flask_login import login_required
from cacao_accounting.decorators import modulo_activo

compras = Blueprint("compras", __name__, template_folder="templates")


@compras.route("/compras")
@compras.route("/buying")
@modulo_activo("buying")
@login_required
def compras_():
    """Pantalla principal del modulo de compras."""
    return render_template("compras.html")
