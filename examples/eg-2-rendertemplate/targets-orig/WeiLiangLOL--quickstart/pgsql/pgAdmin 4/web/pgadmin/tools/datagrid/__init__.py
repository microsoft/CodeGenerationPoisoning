##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2020, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""A blueprint module implementing the datagrid frame."""
MODULE_NAME = 'datagrid'

import simplejson as json
import pickle
import random

from threading import Lock
from flask import Response, url_for, session, request, make_response
from werkzeug.useragents import UserAgent
from flask import current_app as app
from flask_security import login_required
from pgadmin.tools.sqleditor.command import *
from pgadmin.utils import PgAdminModule
from pgadmin.utils.ajax import make_json_response, bad_request, \
    internal_server_error

from config import PG_DEFAULT_DRIVER
from pgadmin.model import Server
from pgadmin.utils.driver import get_driver
from pgadmin.utils.exception import ConnectionLost, SSHTunnelConnectionLost
from pgadmin.utils.preferences import Preferences
from pgadmin.settings import get_setting
from pgadmin.browser.utils import underscore_unescape


query_tool_close_session_lock = Lock()


class DataGridModule(PgAdminModule):
    """
    class DataGridModule(PgAdminModule)

        A module class for Edit Grid derived from PgAdminModule.
    """

    LABEL = "Data Grid"

    def get_own_menuitems(self):
        return {}

    def get_own_javascripts(self):
        return [{
            'name': 'pgadmin.datagrid',
            'path': url_for('datagrid.index') + "datagrid",
            'when': None
        }]

    def get_panels(self):
        return []

    def get_exposed_url_endpoints(self):
        """
        Returns:
            list: URL endpoints for backup module
        """
        return [
            'datagrid.initialize_datagrid',
            'datagrid.initialize_query_tool',
            'datagrid.initialize_query_tool_with_did',
            'datagrid.filter_validate',
            'datagrid.filter',
            'datagrid.panel',
            'datagrid.close'
        ]

    def on_logout(self, user):
        """
        This is a callback function when user logout from pgAdmin
        :param user:
        :return:
        """
        with query_tool_close_session_lock:
            if 'gridData' in session:
                for trans_id in session['gridData']:
                    close_query_tool_session(trans_id)

                # Delete all grid data from session variable
                del session['gridData']


blueprint = DataGridModule(MODULE_NAME, __name__, static_url_path='/static')


@blueprint.route("/")
@login_required
def index():
    return bad_request(
        errormsg=gettext('This URL cannot be requested directly.')
    )


@blueprint.route("/css/datagrid.css")
def datagrid_css():
    return make_response(
        render_template('datagrid/css/datagrid.css'),
        200, {'Content-Type': 'text/css'}
    )


@blueprint.route("/filter", endpoint='filter')
@login_required
def show_filter():
    return render_template(MODULE_NAME + '/filter.html')


@blueprint.route(
    '/initialize/datagrid/<int:trans_id>/<int:cmd_type>/<obj_type>/'
    '<int:sgid>/<int:sid>/<int:did>/<int:obj_id>',
    methods=["PUT", "POST"],
    endpoint="initialize_datagrid"
)
@login_required
def initialize_datagrid(trans_id, cmd_type, obj_type, sgid, sid, did, obj_id):
    """
    This method is responsible for creating an asynchronous connection.
    After creating the connection it will instantiate and initialize
    the object as per the object type. It will also create a unique
    transaction id and store the information into session variable.

    Args:
        cmd_type: Contains value for which menu item is clicked.
        obj_type: Contains type of selected object for which data grid to
        be render
        sgid: Server group Id
        sid: Server Id
        did: Database Id
        obj_id: Id of currently selected object
    """

    if request.data:
        filter_sql = json.loads(request.data, encoding='utf-8')
    else:
        filter_sql = request.args or request.form

    # Create asynchronous connection using random connection id.
    conn_id = str(random.randint(1, 9999999))
    try:
        manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(sid)
        # default_conn is same connection which is created when user connect to
        # database from tree
        default_conn = manager.connection(did=did)
        conn = manager.connection(did=did, conn_id=conn_id,
                                  auto_reconnect=False,
                                  use_binary_placeholder=True,
                                  array_to_string=True)
    except (ConnectionLost, SSHTunnelConnectionLost) as e:
        raise
    except Exception as e:
        app.logger.error(e)
        return internal_server_error(errormsg=str(e))

    status, msg = default_conn.connect()
    if not status:
        app.logger.error(msg)
        return internal_server_error(errormsg=str(msg))

    status, msg = conn.connect()
    if not status:
        app.logger.error(msg)
        return internal_server_error(errormsg=str(msg))
    try:
        # if object type is partition then it is nothing but a table.
        if obj_type == 'partition':
            obj_type = 'table'

        # Get the object as per the object type
        command_obj = ObjectRegistry.get_object(
            obj_type, conn_id=conn_id, sgid=sgid, sid=sid,
            did=did, obj_id=obj_id, cmd_type=cmd_type,
            sql_filter=filter_sql
        )
    except Exception as e:
        app.logger.error(e)
        return internal_server_error(errormsg=str(e))

    if 'gridData' not in session:
        sql_grid_data = dict()
    else:
        sql_grid_data = session['gridData']

    # Use pickle to store the command object which will be used later by the
    # sql grid module.
    sql_grid_data[str(trans_id)] = {
        # -1 specify the highest protocol version available
        'command_obj': pickle.dumps(command_obj, -1)
    }

    # Store the grid dictionary into the session variable
    session['gridData'] = sql_grid_data

    return make_json_response(
        data={
            'conn_id': conn_id
        }
    )


@blueprint.route(
    '/panel/<int:trans_id>',
    methods=["POST"],
    endpoint='panel'
)
def panel(trans_id):
    """
    This method calls index.html to render the data grid.

    Args:
        trans_id: unique transaction id
    """

    url_params = None
    if request.args:
        url_params = {k: v for k, v in request.args.items()}

    if request.form:
        url_params['title'] = request.form['title']
        if 'sql_filter' in request.form:
            url_params['sql_filter'] = request.form['sql_filter']
        if 'query_url' in request.form:
            url_params['query_url'] = request.form['query_url']

    # We need client OS information to render correct Keyboard shortcuts
    user_agent = UserAgent(request.headers.get('User-Agent'))

    """
    Animations and transitions are not automatically GPU accelerated and by
    default use browser's slow rendering engine. We need to set 'translate3d'
    value of '-webkit-transform' property in order to use GPU. After applying
    this property under linux, Webkit calculates wrong position of the
    elements so panel contents are not visible. To make it work, we need to
    explicitly set '-webkit-transform' property to 'none' for .ajs-notifier,
    .ajs-message, .ajs-modal classes.

    This issue is only with linux runtime application and observed in Query
    tool and debugger. When we open 'Open File' dialog then whole Query tool
    panel content is not visible though it contains HTML element in back end.

    The port number should have already been set by the runtime if we're
    running in desktop mode.
    """
    is_linux_platform = False

    from sys import platform as _platform
    if "linux" in _platform:
        is_linux_platform = True

    # Fetch the server details
    bgcolor = None
    fgcolor = None

    s = Server.query.filter_by(id=url_params['sid']).first()
    if s and s.bgcolor:
        # If background is set to white means we do not have to change
        # the title background else change it as per user specified
        # background
        if s.bgcolor != '#ffffff':
            bgcolor = s.bgcolor
        fgcolor = s.fgcolor or 'black'

    layout = get_setting('SQLEditor/Layout')

    return render_template(
        "datagrid/index.html",
        _=gettext,
        uniqueId=trans_id,
        is_desktop_mode=app.PGADMIN_RUNTIME,
        is_linux=is_linux_platform,
        title=underscore_unescape(url_params['title']),
        url_params=json.dumps(url_params),
        client_platform=user_agent.platform,
        bgcolor=bgcolor,
        fgcolor=fgcolor,
        layout=layout,
    )


@blueprint.route(
    '/initialize/query_tool/<int:trans_id>/<int:sgid>/<int:sid>/<int:did>',
    methods=["POST"], endpoint='initialize_query_tool_with_did'
)
@blueprint.route(
    '/initialize/query_tool/<int:trans_id>/<int:sgid>/<int:sid>',
    methods=["POST"], endpoint='initialize_query_tool'
)
@login_required
def initialize_query_tool(trans_id, sgid, sid, did=None):
    """
    This method is responsible for instantiating and initializing
    the query tool object. It will also create a unique
    transaction id and store the information into session variable.

    Args:
        sgid: Server group Id
        sid: Server Id
        did: Database Id
    """
    connect = True
    # Read the data if present. Skipping read may cause connection
    # reset error if data is sent from the client
    if request.data:
        _ = request.data

    reqArgs = request.args
    if ('recreate' in reqArgs and
            reqArgs['recreate'] == '1'):
        connect = False

    # Create asynchronous connection using random connection id.
    conn_id = str(random.randint(1, 9999999))

    # Use Maintenance database OID
    manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(sid)

    if did is None:
        did = manager.did
    try:
        command_obj = ObjectRegistry.get_object(
            'query_tool', conn_id=conn_id, sgid=sgid, sid=sid, did=did
        )
    except Exception as e:
        app.logger.error(e)
        return internal_server_error(errormsg=str(e))

    try:
        conn = manager.connection(did=did, conn_id=conn_id,
                                  auto_reconnect=False,
                                  use_binary_placeholder=True,
                                  array_to_string=True)
        if connect:
            status, msg = conn.connect()
            if not status:
                app.logger.error(msg)
                return internal_server_error(errormsg=str(msg))
    except (ConnectionLost, SSHTunnelConnectionLost) as e:
        app.logger.error(e)
        raise
    except Exception as e:
        app.logger.error(e)
        return internal_server_error(errormsg=str(e))

    if 'gridData' not in session:
        sql_grid_data = dict()
    else:
        sql_grid_data = session['gridData']

    # Set the value of auto commit and auto rollback specified in Preferences
    pref = Preferences.module('sqleditor')
    command_obj.set_auto_commit(pref.preference('auto_commit').get())
    command_obj.set_auto_rollback(pref.preference('auto_rollback').get())

    # Use pickle to store the command object which will be used
    # later by the sql grid module.
    sql_grid_data[str(trans_id)] = {
        # -1 specify the highest protocol version available
        'command_obj': pickle.dumps(command_obj, -1)
    }

    # Store the grid dictionary into the session variable
    session['gridData'] = sql_grid_data

    return make_json_response(
        data={
            'connId': str(conn_id),
            'serverVersion': manager.version,
        }
    )


@blueprint.route('/close/<int:trans_id>', methods=["DELETE"], endpoint='close')
def close(trans_id):
    """
    This method is used to close the asynchronous connection
    and remove the information of unique transaction id from
    the session variable.

    Args:
        trans_id: unique transaction id
    """
    with query_tool_close_session_lock:
        if 'gridData' not in session:
            return make_json_response(data={'status': True})

        grid_data = session['gridData']
        # Return from the function if transaction id not found
        if str(trans_id) not in grid_data:
            return make_json_response(data={'status': True})

        try:
            close_query_tool_session(trans_id)
            # Remove the information of unique transaction id from the
            # session variable.
            grid_data.pop(str(trans_id), None)
            session['gridData'] = grid_data
        except Exception as e:
            app.logger.error(e)
            return internal_server_error(errormsg=str(e))

    return make_json_response(data={'status': True})


@blueprint.route(
    '/filter/validate/<int:sid>/<int:did>/<int:obj_id>',
    methods=["PUT", "POST"], endpoint='filter_validate'
)
@login_required
def validate_filter(sid, did, obj_id):
    """
    This method is used to validate the sql filter.

    Args:
        sid: Server Id
        did: Database Id
        obj_id: Id of currently selected object
    """
    if request.data:
        filter_sql = json.loads(request.data, encoding='utf-8')
    else:
        filter_sql = request.args or request.form

    try:
        # Create object of SQLFilter class
        sql_filter_obj = SQLFilter(sid=sid, did=did, obj_id=obj_id)

        # Call validate_filter method to validate the SQL.
        status, res = sql_filter_obj.validate_filter(filter_sql)
    except Exception as e:
        app.logger.error(e)
        return internal_server_error(errormsg=str(e))

    return make_json_response(data={'status': status, 'result': res})


@blueprint.route("/datagrid.js")
@login_required
def script():
    """render the required javascript"""
    return Response(
        response=render_template("datagrid/js/datagrid.js", _=gettext),
        status=200,
        mimetype="application/javascript"
    )


def close_query_tool_session(trans_id):
    """
    This function is used to cancel the transaction and release the connection.

    :param trans_id: Transaction id
    :return:
    """
    if 'gridData' in session and str(trans_id) in session['gridData']:
        cmd_obj_str = session['gridData'][str(trans_id)]['command_obj']
        # Use pickle.loads function to get the command object
        cmd_obj = pickle.loads(cmd_obj_str)

        # if connection id is None then no need to release the connection
        if cmd_obj.conn_id is not None:
            manager = get_driver(
                PG_DEFAULT_DRIVER).connection_manager(cmd_obj.sid)
            if manager is not None:
                conn = manager.connection(
                    did=cmd_obj.did, conn_id=cmd_obj.conn_id)

                # Release the connection
                if conn.connected():
                    conn.cancel_transaction(cmd_obj.conn_id, cmd_obj.did)
                    manager.release(did=cmd_obj.did, conn_id=cmd_obj.conn_id)
