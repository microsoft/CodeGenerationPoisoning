from datetime import datetime
from flask import Blueprint, request, render_template
from sqlalchemy import or_, not_

from api.models import db, models
from api.core import create_response, _generate_like_or_filters
from api.keywords import KEYWORDS
from api.auth import auth


_main = Blueprint("_main", __name__)


@_main.route("/")
@_main.route("/ssd_api", methods=["GET"])
def index():
    """ Graphical API debugger
    """
    return render_template("debug.html")


@_main.route("/ssd_api/get_table", methods=["GET"])
def get_table():
    """ Return all available tables
    """
    return create_response(data={"table_names": list(models.keys())})


@_main.route("/ssd_api/get_table_cols", methods=["GET"])
@auth.login_required
def get_table_cols():
    """ Get column names for a given table
    """
    if "table_name" not in request.args:
        return create_response(message="table_name missing", status=420)

    table_name = request.args["table_name"]
    col_names = models[table_name].__table__.columns.keys()

    return create_response(data={"table_name": table_name, "columns": col_names})


@_main.route("/ssd_api/get_distinct", methods=["GET"])
@auth.login_required
def get_distinct():
    """Get distinct values given a table_name and col_name
    special can be used to get eye_diagnosis and systemic_diagnosis
    """
    td = datetime.now()
    if "special" not in request.args:
        """Get distinct items from the given table column
        """
        col_name = request.args["col_name"]
        table_name = request.args["table_name"]

        if table_name not in models:
            return create_response(
                message="Table '{}' is not available.".format(table_name), status=420
            )

        try:
            tb = models[table_name]
            tb_col = tb.__dict__[col_name]
            data = tb.query.with_entities(tb_col).distinct().order_by(tb_col).all()
            data = [r[0] for r in data if r[0]]
        except Exception as e:
            return create_response(message=str(e), status=420)

        return create_response(
            data={
                "data": data,
                "table_name": table_name,
                "col_name": col_name,
                "time_taken_seconds": (datetime.today() - td).total_seconds(),
            }
        )

    elif "diagnosis" in request.args["special"]:
        """Get distinct eye_diagnosis or systemic_diagnosis
        """
        special = request.args["special"]
        tb = models["diagnosis_deid"]

        or_filters = _generate_like_or_filters(
            tb.diagnosis_name, KEYWORDS["eye_diagnosis_keywords"]
        )
        qry = (
            tb.query.with_entities(tb.diagnosis_name)
            .distinct()
            .order_by(tb.diagnosis_name)
        )

        if special == "eye_diagnosis":
            qry = qry.filter(or_(*or_filters))

        elif special == "systemic_diagnosis":
            qry = qry.filter(not_(or_(*or_filters)))

        data = qry.all()
        data = [r[0] for r in data]

        return create_response(
            data={
                "data": data,
                "special": special,
                "time_taken_seconds": (datetime.today() - td).total_seconds(),
            }
        )
    else:
        return create_response(message="Special item not recognised", status=420)


@_main.route("/ssd_api/filter_table_with_ptid", methods=["GET"])
@auth.login_required
def filter_table_with_ptid():
    pt_id = request.args.getlist("pt_id")
    table_name = request.args["table_name"]

    try:
        tb = models[table_name]
        data = tb.query.filter(tb.pt_id.in_(pt_id)).all()
        data = [v.to_dict() for v in data]
    except Exception as e:
        return create_response(message=str(e), status=420)

    return create_response(data={"data": data})
