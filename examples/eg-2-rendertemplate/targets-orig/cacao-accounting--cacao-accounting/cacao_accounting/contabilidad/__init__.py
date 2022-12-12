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

# pylint: disable=no-else-return

"""Modulo de Contabilidad."""

from flask import Blueprint, redirect, render_template, request
from flask.helpers import url_for
from flask_login import login_required
from cacao_accounting.contabilidad.auxiliares import (
    obtener_catalogo_base,
    obtener_catalogo_centros_costo_base,
    obtener_catalogo,
    obtener_centros_costos,
    obtener_entidad,
    obtener_entidades,
    obtener_lista_monedas,
    obtener_lista_entidades_por_id_razonsocial,
)
from cacao_accounting.database import STATUS
from cacao_accounting.database.helpers import obtener_registro_desde_uuid, MAXIMO_RESULTADOS_EN_CONSULTA_PAGINADA
from cacao_accounting.decorators import modulo_activo, verifica_acceso
from cacao_accounting.metadata import APPNAME
from cacao_accounting.transaccion import Transaccion

contabilidad = Blueprint("contabilidad", __name__, template_folder="templates")
LISTA_ENTIDADES = redirect("/accounts/entity/list")


# <------------------------------------------------------------------------------------------------------------------------> #
# Monedas
@contabilidad.route("/currency/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def monedas():
    """Listado de monedas registradas en el sistema."""
    from cacao_accounting.database import Moneda

    CONSULTA = Moneda.query.order_by(Moneda.codigo).paginate(
        request.args.get("page", default=1, type=int), MAXIMO_RESULTADOS_EN_CONSULTA_PAGINADA, False
    )
    TITULO = "Listado de Monedas - " + " - " + APPNAME
    return render_template(
        "contabilidad/moneda_lista.html",
        consulta=CONSULTA,
        titulo=TITULO,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Contabilidad
@contabilidad.route("/contabilidad")
@contabilidad.route("/conta")
@contabilidad.route("/accounts")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def conta():
    """Pantalla principal del modulo contabilidad."""
    TITULO = "Módulo Contabilidad - " + APPNAME
    return render_template(
        "contabilidad.html",
        titulo=TITULO,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Entidades
@contabilidad.route("/accounts/entity/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def entidades():
    """Listado de entidades."""
    from cacao_accounting.database import Entidad

    CONSULTA = Entidad.query.order_by(Entidad.entidad.desc()).paginate(
        request.args.get("page", default=1, type=int), MAXIMO_RESULTADOS_EN_CONSULTA_PAGINADA, False
    )
    TITULO = "Listado de Entidades - " + APPNAME
    return render_template(
        "contabilidad/entidad_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
        statusweb=STATUS,
    )


@contabilidad.route("/accounts/entity/<entidad_id>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def entidad(entidad_id):
    """Entidad individual."""
    from cacao_accounting.database import Entidad

    registro = Entidad.query.filter_by(entidad=entidad_id).first()
    return render_template(
        "contabilidad/entidad.html",
        registro=registro,
    )


@contabilidad.route("/accounts/entity/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def nueva_entidad():
    """Formulario para crear una nueva entidad."""
    from cacao_accounting.contabilidad.forms import FormularioEntidad

    formulario = FormularioEntidad()
    formulario.moneda.choices = obtener_lista_monedas()

    TITULO = "Crear Nueva Entidad - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        from cacao_accounting.contabilidad.registros.entidad import RegistroEntidad

        ENTIDAD = RegistroEntidad()
        DATA = {
            "entidad": request.form.get("id", None),
            "razon_social": request.form.get("razon_social", None),
            "nombre_comercial": request.form.get("nombre_comercial", None),
            "id_fiscal": request.form.get("id_fiscal", None),
            "moneda": request.form.get("moneda", None),
            "tipo_entidad": request.form.get("tipo_entidad", None),
            "correo_electronico": request.form.get("correo_electronico", None),
            "web": request.form.get("web", None),
            "telefono1": request.form.get("telefono1", None),
            "telefono2": request.form.get("telefono2", None),
            "fax": request.form.get("fax", None),
            "status": "activo",
            "habilitada": True,
            "predeterminada": False,
        }
        TRANSACCION_NUEVA_ENTIDAD = Transaccion(
            tipo="principal",
            accion="crear",
            datos=DATA,
            registro="Entidad",
            estatus_actual=None,
            nuevo_estatus=None,
            uuid=None,
            relaciones=None,
            relacion_id=None,
            datos_detalle=None,
        )
        ENTIDAD.ejecutar_transaccion(TRANSACCION_NUEVA_ENTIDAD)
        return LISTA_ENTIDADES

    return render_template(
        "contabilidad/entidad_crear.html",
        form=formulario,
        titulo=TITULO,
    )


@contabilidad.route("/accounts/entity/edit/<id_entidad>", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def editar_entidad(id_entidad):
    """Formulario para editar una entidad."""
    from cacao_accounting.contabilidad.forms import FormularioEntidad
    from cacao_accounting.database import database, Entidad

    ENTIDAD = Entidad.query.filter_by(entidad=id_entidad).first()

    if request.method == "POST":

        ENTIDAD.id_fiscal = request.form.get("id_fiscal", None)
        ENTIDAD.nombre_comercial = request.form.get("nombre_comercial", None)
        ENTIDAD.razon_social = request.form.get("razon_social", None)
        ENTIDAD.telefono1 = request.form.get("telefono1", None)
        ENTIDAD.telefono2 = request.form.get("telefono2", None)
        ENTIDAD.correo_electronico = request.form.get("correo_electronico", None)
        ENTIDAD.fax = request.form.get("fax", None)
        ENTIDAD.web = request.form.get("web", None)
        database.session.add(ENTIDAD)  # pylint: disable=no-member
        database.session.commit()  # pylint: disable=no-member
        return redirect(url_for("contabilidad.entidad", entidad_id=ENTIDAD.entidad))
    else:
        DATA = {
            "nombre_comercial": ENTIDAD.nombre_comercial,
            "razon_social": ENTIDAD.razon_social,
            "id_fiscal": ENTIDAD.id_fiscal,
            "correo_electronico": ENTIDAD.correo_electronico,
            "telefono1": ENTIDAD.telefono1,
            "telefono2": ENTIDAD.telefono2,
            "fax": ENTIDAD.fax,
            "web": ENTIDAD.web,
        }

        formulario = FormularioEntidad(data=DATA)
        formulario.moneda.choices = obtener_lista_monedas()
        return render_template("contabilidad/entidad_editar.html", form=formulario)


@contabilidad.route("/accounts/entity/delete/<id_entidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def eliminar_entidad(id_entidad):
    """Elimina una entidad de sistema."""
    from cacao_accounting.contabilidad.registros.entidad import RegistroEntidad
    from cacao_accounting.database import Entidad

    REGISTRO = RegistroEntidad()
    TRANSACCION = obtener_registro_desde_uuid(tabla=Entidad, uuid=id_entidad)
    TRANSACCION.accion = "eliminar"
    TRANSACCION.tipo = "principal"
    REGISTRO.ejecutar_transaccion(TRANSACCION)
    return LISTA_ENTIDADES


@contabilidad.route("/accounts/entity/set_inactive/<id_entidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def inactivar_entidad(id_entidad):
    """Estable una entidad como inactiva."""
    from cacao_accounting.contabilidad.registros.entidad import RegistroEntidad
    from cacao_accounting.database import Entidad

    REGISTRO = RegistroEntidad()
    TRANSACCION = obtener_registro_desde_uuid(tabla=Entidad, uuid=id_entidad)
    TRANSACCION.accion = "actualizar"
    TRANSACCION.tipo = "principal"
    TRANSACCION.nuevo_estatus = "inactivo"
    REGISTRO.ejecutar_transaccion(TRANSACCION)
    return LISTA_ENTIDADES


@contabilidad.route("/accounts/entity/set_active/<id_entidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def activar_entidad(id_entidad):
    """Estable una entidad como inactiva."""
    from cacao_accounting.contabilidad.registros.entidad import RegistroEntidad
    from cacao_accounting.database import Entidad

    REGISTRO = RegistroEntidad()
    TRANSACCION = obtener_registro_desde_uuid(tabla=Entidad, uuid=id_entidad)
    TRANSACCION.accion = "actualizar"
    TRANSACCION.tipo = "principal"
    TRANSACCION.nuevo_estatus = "activo"
    REGISTRO.ejecutar_transaccion(TRANSACCION)
    return LISTA_ENTIDADES


@contabilidad.route("/accounts/entity/set_default/<id_entidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def predeterminar_entidad(id_entidad):
    """Establece una entidad como predeterminada."""
    from cacao_accounting.contabilidad.registros.entidad import RegistroEntidad
    from cacao_accounting.database import Entidad

    REGISTRO = RegistroEntidad()
    TRANSACCION = obtener_registro_desde_uuid(tabla=Entidad, uuid=id_entidad)
    TRANSACCION.accion = "actualizar"
    TRANSACCION.tipo = "principal"
    TRANSACCION.nuevo_estatus = "predeterminado"
    REGISTRO.ejecutar_transaccion(TRANSACCION)
    return LISTA_ENTIDADES


# <------------------------------------------------------------------------------------------------------------------------> #
# Unidades de Negocio
@contabilidad.route("/accounts/unit/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def unidades():
    """Listado de unidades de negocios."""
    from cacao_accounting.database import Unidad

    CONSULTA = Unidad.query.order_by(Unidad.unidad.desc()).paginate(
        request.args.get("page", default=1, type=int), MAXIMO_RESULTADOS_EN_CONSULTA_PAGINADA, False
    )
    TITULO = "Listado de Unidades de Negocio - " + APPNAME
    return render_template(
        "contabilidad/unidad_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
        statusweb=STATUS,
    )


@contabilidad.route("/accounts/unit/<id_unidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def unidad(id_unidad):
    """Unidad de negocios."""
    from cacao_accounting.database import Unidad

    registro = Unidad.query.filter_by(unidad=id_unidad).first()
    return render_template("contabilidad/unidad.html", registro=registro)


@contabilidad.route("/accounts/unit/delete/<id_unidad>")
@modulo_activo("accounting")
@login_required
def eliminar_unidad(id_unidad):
    """Elimina una entidad de la base de datos."""
    return redirect("/app")


@contabilidad.route("/accounts/unit/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def nueva_unidad():
    """Formulario para crear una nueva unidad de negocios."""
    from cacao_accounting.contabilidad.forms import FormularioUnidad

    formulario = FormularioUnidad()
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    TITULO = "Crear Nueva Unidad de Negocios - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        from cacao_accounting.contabilidad.registros.unidad import RegistroUnidad

        UNIDAD = RegistroUnidad()
        DATA = {
            "unidad": request.form.get("id", None),
            "nombre": request.form.get("nombre", None),
            "entidad": request.form.get("entidad", None),
            "correo_electronico": request.form.get("correo_electronico", None),
            "web": request.form.get("web", None),
            "telefono1": request.form.get("telefono1", None),
            "telefono2": request.form.get("telefono2", None),
            "fax": request.form.get("fax", None),
            "status": "activo",
        }
        TRANSACCION_NUEVA_UNIDAD = Transaccion(
            tipo="principal",
            accion="crear",
            datos=DATA,
            registro="Unidad",
            estatus_actual=None,
            nuevo_estatus=None,
            uuid=None,
            relaciones=None,
            relacion_id=None,
            datos_detalle=None,
        )
        UNIDAD.ejecutar_transaccion(TRANSACCION_NUEVA_UNIDAD)
        return redirect("/accounts/unit/list")
    return render_template(
        "contabilidad/unidad_crear.html",
        titulo=TITULO,
        form=formulario,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Cuentas Contables


@contabilidad.route("/accounts/accounts", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def cuentas():
    """Catalogo de cuentas contables."""
    TITULO = "Catalogo de Cuentas Contables - " + APPNAME

    return render_template(
        "contabilidad/cuenta_lista.html",
        base_cuentas=obtener_catalogo_base(entidad_=request.args.get("entidad", None)),
        cuentas=obtener_catalogo(entidad_=request.args.get("entidad", None)),
        entidades=obtener_entidades(),
        entidad=obtener_entidad(ent=request.args.get("entidad")),
        titulo=TITULO,
    )


@contabilidad.route("/accounts/accounts/<id_cta>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def cuenta(id_cta):
    """Cuenta Contable."""
    from cacao_accounting.database import Cuentas

    registro = Cuentas.query.filter_by(codigo=id_cta).first()
    return render_template(
        "contabilidad/cuenta.html",
        registro=registro,
        statusweb=STATUS,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Centros de Costos
@contabilidad.route("/accounts/costs_center", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def ccostos():
    """Catalogo de centros de costos."""
    TITULO = "Catalogo de Centros de Costos - " + APPNAME

    return render_template(
        "contabilidad/centro-costo_lista.html",
        base_centrocostos=obtener_catalogo_centros_costo_base(entidad_=request.args.get("entidad", None)),
        ccostos=obtener_centros_costos(entidad_=request.args.get("entidad", None)),
        entidades=obtener_entidades(),
        entidad=obtener_entidad(ent=request.args.get("entidad", None)),
        titulo=TITULO,
    )


@contabilidad.route("/accounts/costs_center/<id_cc>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def centro_costo(id_cc):
    """Centro de Costos."""
    from cacao_accounting.database import CentroCosto

    registro = CentroCosto.query.filter_by(codigo=id_cc).first()
    return render_template(
        "contabilidad/centro-costo.html",
        registro=registro,
        statusweb=STATUS,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Proyectos
@contabilidad.route("/accounts/project/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def proyectos():
    """Listado de proyectos."""
    from cacao_accounting.database import Proyecto

    CONSULTA = Proyecto.query.order_by(Proyecto.codigo.desc()).paginate(
        request.args.get("page", default=1, type=int), MAXIMO_RESULTADOS_EN_CONSULTA_PAGINADA, False
    )
    TITULO = "Listados de Proyectos - " + APPNAME
    return render_template(
        "contabilidad/proyecto_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
        statusweb=STATUS,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Tipos de Cambio
@contabilidad.route("/accounts/exchange")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def tasa_cambio():
    """Listado de tasas de cambio."""
    from cacao_accounting.database import TasaDeCambio

    CONSULTA = TasaDeCambio.query.order_by(TasaDeCambio.fecha.desc()).paginate(
        request.args.get("page", default=1, type=int), MAXIMO_RESULTADOS_EN_CONSULTA_PAGINADA, False
    )
    TITULO = "Listado de Tasas de Cambio - " + APPNAME
    return render_template(
        "contabilidad/tc_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Períodos Contables
@contabilidad.route("/accounts/accounting_period")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def periodo_contable():
    """Lista de periodos contables."""
    from cacao_accounting.database import PeriodoContable

    CONSULTA = PeriodoContable.query.order_by(PeriodoContable.nombre.desc()).paginate(
        request.args.get("page", default=1, type=int), MAXIMO_RESULTADOS_EN_CONSULTA_PAGINADA, False
    )
    TITULO = "Listado de Períodos Contables - " + APPNAME
    return render_template(
        "contabilidad/periodo_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
        statusweb=STATUS,
    )
