## Imports
import pytest
import re
import sqlite3

from pathlib import Path
from redbaron import RedBaron

from tests.utils import *
#!

## Paths
admin = Path.cwd() / 'cms' / 'admin'
admin_module = admin / '__init__.py'
models = admin / 'models.py'
auth = admin / 'auth.py'
migrations = Path.cwd() / 'migrations'
migrations_exists = Path.exists(migrations) and Path.is_dir(migrations)
versions = migrations / 'versions'
versions_exists = Path.exists(versions) and Path.is_dir(versions)
content_db = Path.cwd() / 'cms' / 'content.db'
content_db_exists = Path.exists(content_db) and Path.is_file(content_db)
login_template = template_data('login')
#!

## Module Functions
def get_source_code(file_path):
    with open(file_path.resolve(), 'r') as source_code:
        return RedBaron(source_code.read())
#!

## Source Code
admin_module_code = get_source_code(admin_module)
models_code = get_source_code(models)
auth_code = get_source_code(auth)
#!

## Tests
@pytest.mark.test_models_password_column_module1
def test_models_password_column_module1():
    # 1. Models - Password Column
    # password = db.Column(db.String(100), nullable=False)
    password = models_code.find('assign', lambda node: \
        node.target.value == 'password' and \
        node.value[0].value == 'db' and \
        node.value[1].value == 'Column' and \
        node.value[2].type == 'call')
    password_exists = password is not None
    assert password_exists, \
        'Are you assigning `password` a call to the `db.Column()` function?'

    first_argument = password.find('atomtrailers', lambda node: \
        node.parent.type == 'call_argument' and \
        node.value[0].value == 'db' and \
        node.value[1].value == 'String' and \
        node.value[2].type == 'call' and \
        node.value[2].value[0].value.value == '100')

    second_argument = password.find('call_argument', lambda node: \
        str(node.target) == 'nullable' and \
        node.value.value == 'False'
    )
    arguments_exist = first_argument is not None and second_argument is not None
    assert arguments_exist, \
            'Are you passing the correct arguments to the `db.Column()` function?'

@pytest.mark.test_models_check_password_module1
def test_models_check_password_module1():
    # 2. Models - Check Password
    # from werkzeug.security import check_password_hash
    # def check_password(self, value):
    #     return check_password_hash(self.password, value)
    security_import = get_imports(models_code, 'werkzeug.security')
    security_import_exits = security_import is not None
    assert security_import_exits, \
        'Do you have a `werkzeug.security` import statement?'
    check_password_hash_exists = 'check_password_hash' in security_import
    assert check_password_hash_exists, \
        'Are you importing `check_password_hash` from `werkzeug.security` in `cms/admin/models.py`?'
    def_check_password = models_code.find('def', lambda node: \
        node.name == 'check_password' and \
        node.arguments[0].target.value == 'self' and \
        node.arguments[1].target.value == 'value' and \
        node.parent.type == 'class' and \
        node.parent.name == 'User'
    )
    
    def_check_password_exists = def_check_password is not None
    assert def_check_password_exists, \
        'Have you created a function in the `User` model called `check_password`? Do you have the correct parameters?'
        
    check_password_return = def_check_password.find('return', lambda node: \
        node.value[0].value == 'check_password_hash' and \
        node.value[1].type == 'call')
    check_password_return_exists = check_password_return is not None
    assert check_password_return_exists, \
        'Are you returning a call to the `check_password_hash()` function?'
    
    first_argument = def_check_password.find('atomtrailers', lambda node: \
        node.parent.type == 'call_argument' and \
        node.value[0].value == 'self' and \
        node.value[1].value == 'password')

    second_argument = def_check_password.find('name', lambda node: \
        node.parent.type == 'call_argument' and \
        node.value == 'value')

    arguments_exist = first_argument is not None and second_argument is not None
    assert arguments_exist, \
        'Are you passing the correct arguments to the `check_password_hash()` function?'

@pytest.mark.test_database_migration_module1
def test_database_migration_module1():
    # 3. Database Migration
    # > flask db init
    # > flask db migrate
    # > flask db upgrade
    # > flask add-content
    assert migrations_exists, \
        'Have you run the `flask db init` command?'
    versions_file_exists = versions_exists and len(list(versions.glob('*_.py'))) == 1 
    assert versions_file_exists, \
        'Have you run the `flask db migrate` command?'
        
    assert content_db_exists, \
        'Have you run the `flask db upgrade` command?'

    con = sqlite3.connect(content_db.resolve())
    con.row_factory = lambda cursor, row: row[0]
    cursor = con.cursor()
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    tables.sort()
    tables_exist = tables == ['alembic_version', 'content', 'setting', 'type', 'user']
    assert tables_exist, \
        'Have you run the `flask db upgrade` command?'
        
    content_table = cursor.execute("SELECT COUNT() FROM content").fetchone()
    user_table = cursor.execute("SELECT COUNT() FROM user").fetchone()
    content_imported = content_table == 3 and user_table == 1
    assert content_imported, \
        'Have you run the `flask add-content` command?'

@pytest.mark.test_template_login_form_module1
def test_template_login_form_module1():
    # 4. Template - Login Form
    # <input type="text" class="input" name="username">
    # <input type="password" class="input" name="password">
    # <input type="submit" class="button is-link" value="Login">
    username_exists = len(login_template.select('input[name="username"][class="input"][type="text"]')) == 1
    assert username_exists, \
        'Have you added an `<input>` with the correct attributes to the `Username` control `<div>`?'

    password_exists = len(login_template.select('input[name="password"][class="input"][type="password"]')) == 1
    assert password_exists, \
        'Have you added an `<input>` with the correct attributes to the `Password` control `<div>`?'

    submit_exists = len(login_template.select('input[type="submit"][value="Login"].button.is-link')) == 1
    assert submit_exists, \
        'Have you added a `submit` `<input>` with the correct attributes to the last control `<div>`?'

@pytest.mark.test_auth_imports_module1
def test_auth_imports_module1():
    # 5. Auth - Protected Decorator
    # from functools import wraps
    # from flask import session, g
    functools_import = get_imports(auth_code, 'functools')
    functools_import_exits = functools_import is not None
    assert functools_import_exits, \
        'Do you have a `functools` import statement?'
    wraps_exists = 'wraps' in functools_import
    assert wraps_exists, \
        'Are you importing `wraps` from `functools` in `cms/admin/auth.py`?'
    flask_import = get_imports(auth_code, 'flask')
    flask_import_exits = flask_import is not None
    assert flask_import_exits, \
        'Do you have a `flask` import statement?'
    g_exists = 'g' in flask_import
    assert g_exists, \
        'Are you importing `g` from `flask` in `cms/admin/auth.py`?'
    session_exists = 'session' in flask_import
    assert session_exists, \
        'Are you importing `session` from `flask` in `cms/admin/auth.py`?'

@pytest.mark.test_auth_protected_decorator_module1
def test_auth_protected_decorator_module1():
    # 6. Auth - Protected Decorator
    # def protected(route_function):
    #     def wrapped_route_function(**kwargs):
    #         return route_function(**kwargs)
    def_protected = auth_code.find('def', lambda node: \
        node.name == 'protected' and \
        node.arguments[0].target.value == 'route_function')
    def_protected_exists = def_protected is not None
    assert def_protected_exists, \
        'Have you created a function at the top of `auth.py` called `protected`? Do you have the correct parameters?'
    wrapped = def_protected.find('def', lambda node: \
        node.name == 'wrapped_route_function' and \
        node.arguments[0].type == 'dict_argument' and \
        node.arguments[0].value.value == 'kwargs')
    wrapped_exists = wrapped is not None
    assert wrapped_exists, \
        'Have you created a function in the `protected` function called `wrapped_route_function`? Do you have the correct parameters?'
    wrapped_return = wrapped.find('return', lambda node: \
        node.value.type == 'atomtrailers' and \
        node.value.value[0].value == 'route_function' and \
        node.value.value[1].type == 'call' and \
        node.value.value[1].value[0].type == 'dict_argument' and \
        node.value.value[1].value[0].value.value == 'kwargs')
    wrapped_return_exists = wrapped_return is not None
    assert wrapped_return_exists, \
        'Are you returning a call to the `route_function` function in the body of the `wrapped_route_function` function?'    

@pytest.mark.test_auth_redirect_user_module1
def test_auth_redirect_user_module1():
    # 7. Auth - Redirect User
    # @wraps(route_function)
    #
    #     if g.user is None:
    #         return redirect(url_for('admin.login'))
    #
    # return wrapped_route_function
    def_protected = auth_code.find('def', lambda node: \
        node.name == 'protected' and \
        node.arguments[0].target.value == 'route_function')
    wrapped = def_protected.find('def', name='wrapped_route_function')
    wrapped_exists = wrapped is not None
    assert wrapped_exists, \
        'Have you created a function in the `protected` function called `wrapped_route_function`? Do you have the correct parameters?'
    wrapped.find('decorator', lambda node: \
        str(node.value) == 'wraps' and \
        node.call.value[0].value.value == 'route_function')
        
    g_user = get_conditional(wrapped, ['g.user:is:None', 'g.user:==:None'], 'if')
    g_user_exists = g_user is not None
    assert g_user_exists, \
        'Do you have an `if` statement that tests if `g.user` is `None`?'

    return_redirect = g_user.parent.find('return', lambda node: \
        node.value[0].value == 'redirect' and \
        node.value[1].type == 'call')
    return_redirect_exists = return_redirect is not None
    assert return_redirect_exists, \
        'Are you returning a call to the `redirect()` function in the `if` statement?'
    
    url_for_call = return_redirect.find_all('atomtrailers', lambda node: \
        node.value[0].value == 'url_for' and \
        node.value[1].type == 'call')
    url_for_call_exists = url_for_call is not None
    assert url_for_call_exists, \
        'Are you passing a call to the `url_for()` function to the `redirect()` function?'
    
    url_for_args = list(url_for_call.find_all('call_argument').map(lambda node: str(node.target) + ':' + str(node.value.value).replace("'", '"')))
    url_content = 'None:"admin.login"' in url_for_args
    assert url_content, \
        "Are you passing the `'admin.login'` route to the `url_for()` function?"
    
    wrapped_return = def_protected.find('return', lambda node: \
        node.value.type == 'name' and \
        node.value.value == 'wrapped_route_function')
    wrapped_return_exists = wrapped_return is not None
    assert wrapped_return_exists, \
        'Are you returning the `wrapped_route_function` from the `protected` function?'

@pytest.mark.test_auth_load_user_module1
def test_auth_load_user_module1():
    # 8. Auth - Load User
    # @admin_bp.before_app_request
    # def load_user():
    #     user_id = session.get('user_id')
    #     g.user = User.query.get(user_id) if user_id is not None else None
    load_user = auth_code.find('def', name='load_user')
    load_user_exists = load_user is not None
    assert load_user_exists, \
        'Have you created a function called `load_user`?'

    in_protected = isinstance(load_user.parent, redbaron.redbaron.RedBaron) or \
        (load_user.parent.type == 'def' and load_user.parent.name == 'protected') is not True
    assert in_protected, \
        'The `load_user` function should be outside of the `protected` function.'

    decorator_exists = load_user.find('decorator', lambda node: node.find('dotted_name', lambda node: \
          node.value[0].value == 'admin_bp' and \
          node.value[1].type == 'dot' and \
          node.value[2].value == 'before_app_request')) is not None
    assert decorator_exists, \
        'The `load_user` function should have a decorator of `@admin_bp.before_app_request`.'

    user_id = load_user.find('assign', lambda node: node.target.value == 'user_id')
    user_id_exists = user_id is not None
    assert user_id_exists, \
        'Are you setting the `user_id` variable correctly?'
    get_call = user_id.find('atomtrailers', lambda node: \
        node.value[0].value == 'session' and \
        node.value[1].value == 'get' and \
        node.value[2].type == 'call'
        )
    get_call_exists = get_call is not None
    assert get_call_exists, \
        'Are you calling the `session.get()` function and assigning the result to `user_id`?'
    get_argument = get_call.find('call_argument', lambda node: \
        str(node.value.value).replace("'", '"') == '"user_id"'  
    ) is not None
    assert get_argument, \
        'Are you passing the `session.get()` function the correct argument?'
    
    ternary_if = get_conditional(load_user, ['user_id:is:not:None', 'user_id:!=:None'], 'ternary_operator') 
    ternary_if_exists = ternary_if is not None
    assert ternary_if_exists, \
        'Do you have a ternary `if` statement to set `g.user`?'

    ternary_parent = ternary_if.parent
    ternary_parent_exists = ternary_parent is not None
    assert ternary_parent_exists, \
        'Do you have a ternary `if` statement to set `g.user`?'
    
    ternary_assignment = ternary_parent.parent
    ternary_assignment_exists = ternary_assignment is not None
    assert ternary_assignment_exists, \
        'Do you have an assignment statement that sets `g.user`?'
        
    if_branch = ternary_parent.first.find('atomtrailers', lambda node: \
        node.value[0].value == 'User' and \
        node.value[1].value == 'query' and \
        node.value[2].value == 'get' and \
        node.value[3].type == 'call' and \
        node.value[3].value[0].value.value == 'user_id') is not None
    else_branch = ternary_parent.second.value == 'None'
    final_assignment = ternary_assignment.find('atomtrailers', lambda node: \
        node.value[0].value == 'g' and \
        node.value[1].value == 'user') is not None
    
    g_user_assignment = final_assignment and if_branch and final_assignment
    assert g_user_assignment, \
        'Do you have an assignment statement that sets `g.user` to the user_id from the database or `None`?'

@pytest.mark.test_auth_login_route_module1
def test_auth_login_route_module1():
    # 9. Auth - Login Route
    # @admin_bp.route('/login', methods=('GET', 'POST'))
    # def login():
    #     return render_template('admin/login.html')
    login_decorator = get_route(auth_code, 'login').find('dotted_name', lambda node: \
        node.value[0].value == 'admin_bp' and \
        node.value[1].type == 'dot' and \
        node.value[2].value == 'route' and \
        node.parent.call.type == 'call' and \
        rq(node.parent.call.value[0].value.value) == '/login') is not None
    assert login_decorator, \
        'Have you add a route decorator to the `login` route function? Are you passing the correct route pattern?'

    strings = list(get_methods_keyword(auth_code, 'login').find_all('string').map(lambda node: node.value.replace("'", '"')))
    post_check = '"GET"' in strings and '"POST"' in strings
    assert post_check, \
        'Have you added the `methods` keyword argument to the `edit` route allowing `POST` and `GET`?'
        
    return_render = get_route(auth_code, 'login').find('return', lambda node: \
        node.value[0].value == 'render_template' and \
        node.value[1].type == 'call')
    return_render_exists = return_render is not None
    assert return_render_exists, \
        'Are you returning a call to the `render_template()` function?'

    return_render_args = list(return_render.find_all('call_argument').map(lambda node: str(node.target) + ':' + str(node.value).replace("'", '"')))
    template_exists = 'None:"admin/login.html"' in return_render_args
    assert template_exists, \
        'Are you passing the correct HTML template to the `render_template()` function?'

@pytest.mark.test_auth_post_request_module1
def test_auth_post_request_module1():
    # 10. Auth - Post Request
    # if request.method == 'POST':
    #     username = request.form['username']
    #     password = request.form['password']
    #     error = None
    post_check = str(get_request_method(auth_code, 'login', False)).find('POST')
    assert post_check, \
        'Are you testing if the request method is `POST`?'
    try:
        get_form_data(auth_code, 'login', {'username', 'password'}, 'username')
        get_form_data(auth_code, 'login', {'username', 'password'}, 'password')
    except:
        assert False, 'Are you setting `username` and `password` with the correct form data?'
        
    error = get_request_method(auth_code, 'login').find('assign', lambda node: \
        node.target.value == 'error')
    error_exists = error is not None
    assert error_exists, \
        'Do you have a variable named `error`?'
    error_none = error.value.to_python() is None
    assert error_none, \
        'Are you setting the `error` variable correctly?'
    
@pytest.mark.test_auth_get_user_module1
def test_auth_get_user_module1():
    # 11. Auth - Get User
    # user = User.query.filter_by(username=username).first()
    user = get_route(auth_code, 'login').find('assign', lambda node: \
        node.target.value == 'user')
    user_exists = user is not None
    assert user_exists, \
        'Are you setting the `user` variable correctly?'
    filter_by = user.find('atomtrailers', lambda node: \
        node.value[0].value == 'User' and \
        node.value[1].value == 'query' and \
        node.value[2].value == 'filter_by' and \
        node.value[3].type == 'call'
        )
    filter_by_exists = filter_by is not None
    assert filter_by_exists, \
        'Are you calling the `User.query.filter_by()` function and assigning the result to `user`?'

    filter_by_argument = filter_by.find('call_argument', lambda node: \
        node.target.value == 'username' and \
        node.value.value == 'username') is not None
    assert filter_by_argument, \
        'Are you passing the correct keyword argument to the `User.query.filter_by()` function?'
    first_call = len(filter_by.value) == 6 and filter_by.value[4].value == 'first' and filter_by.value[5].type == 'call'
    assert first_call, \
        'Have you a append a call to `first()` on `User.query.filter_by()`?'

@pytest.mark.test_auth_validate_form_data_module1
def test_auth_validate_form_data_module1():
    # 12. Auth - Validate Form Data
    # if user is None:
    #     error = 'Incorrect username.'
    # elif not user.check_password(password):
    #     error = 'Incorrect password.'
    user_error = get_conditional(get_request_method(auth_code, 'login'), [ 'not:user', 'user:is:None', 'user:==:None', 'user:is:""', 'user:==:""'], 'if', True)

    user_if_exists = user_error is not None
    assert user_if_exists, \
        'Do you have a nested `if` statement that tests if `user` is `not` empty.'
    user_error_message = user_error.parent.find('assign', lambda node: node.target.value == 'error')
    user_error_message_exists = user_error_message is not None and user_error_message.value.type == 'string'
    assert user_error_message_exists, \
        'Are you setting the `error` variable to the appropriate `string` in the `if` statement.'

    check_error = get_conditional(get_request_method(auth_code, 'login'), ['not:user.check_password(password)'], 'elif', True)

    check_elif_exists = check_error is not None
    assert check_elif_exists, \
        'Do you have an `elif` statement that tests if `check` is `not` empty?'
    check_error_message = check_error.parent.find('assign', lambda node: node.target.value == 'error')
    check_error_message_exists = check_error_message is not None and check_error_message.value.type == 'string'
    assert check_error_message_exists, \
        'Are you setting the `error` variable to the appropriate `string` in the `elif` statement.'

@pytest.mark.test_auth_store_user_in_session_module1
def test_auth_store_user_in_session_module1():
    # 13. Auth - Store User in Session
    # if error is None:
    #     session.clear()
    #     session['user_id'] = user.id
    #     return redirect(url_for('admin.content', type='page'))
    # flash(error)
    error_check = get_request_method(auth_code, 'login').find('comparison', lambda node: \
        'error' in [str(node.first), str(node.second)])
    error_check_exists = error_check is not None and error_check.parent.type == 'if' and \
        ((error_check.first.value == 'error' and error_check.second.value == 'None') or \
        (error_check.first.value == 'None' and error_check.second.value == 'error')) and \
        (error_check.value.first == '==' or error_check.value.first == 'is')
    assert error_check_exists, \
        'Do you have an `if` statment that is checking if `error` is `None`?'

    error_check_if = error_check.parent
    clear_call = error_check_if.find('atomtrailers', lambda node: \
        node.value[0].value == 'session' and \
        node.value[1].value == 'clear' and \
        node.value[2].type == 'call'
        ) is not None
    assert clear_call, \
        'Are you calling the `session.clear()` function?'
        
    session_user = error_check_if.find('assign', lambda node: \
        node.target.value[0].value == 'session' and \
        rq(node.target.value[1].value.value) == 'user_id' and \
        node.value.value[0].value == 'user' and \
        node.value.value[1].value == 'id') is not None
    assert session_user, \
        'Are you setting the `user_id` `session` key to the value `user.id`?'
        
    return_redirect = error_check_if.find('return', lambda node: \
        node.value[0].value == 'redirect' and \
        node.value[1].type == 'call')
    return_redirect_exists = return_redirect is not None
    assert return_redirect_exists, \
        'Are you returning a call to the `redirect()` function?'

    url_for_call = return_redirect.find_all('atomtrailers', lambda node: \
        node.value[0].value == 'url_for' and \
        node.value[1].type == 'call')
    url_for_call_exists = url_for_call is not None
    assert url_for_call_exists, \
        'Are you passing a call to the `url_for()` function to the `redirect()` function?'

    url_for_args = list(url_for_call.find_all('call_argument').map(lambda node: \
        str(node.target) + ':' + str(node.value).replace("'", '"')))
    url_content = 'None:"admin.content"' in url_for_args
    assert url_content, \
        "Are you passing the `'admin.content'` to the `url_for()` function?"
        
    url_type = 'type:"page"' in url_for_args
    assert url_type, \
        'Are you passing a `type` keyword argument set to `type.name` to the `url_for()` function?'

    flash_exists = get_request_method(auth_code, 'login').find('atomtrailers', lambda node: \
        node.value[0].value == 'flash' and \
        node.value[1].type == 'call' and \
        node.value[1].value[0].value.value == 'error') is not None
    assert flash_exists, \
        'Are you flashing an `error` at the end of the `request.method` `if`?'

@pytest.mark.test_auth_logout_route_module1
def test_auth_logout_route_module1():
    # 14. Auth - Logout Route
    # @admin_bp.route('/logout')
    # def logout():
    #     session.clear()
    #     return redirect(url_for('admin.login'))
    login_decorator = get_route(auth_code, 'logout').find('dotted_name', lambda node: \
        node.value[0].value == 'admin_bp' and \
        node.value[1].type == 'dot' and \
        node.value[2].value == 'route' and \
        node.parent.call.type == 'call' and \
        rq(node.parent.call.value[0].value.value) == '/logout') is not None
    assert login_decorator, \
        'Have you added a route decorator to the `logout` route function? Are you passing the correct route pattern?'
    
    clear_call = get_route(auth_code, 'logout').find('atomtrailers', lambda node: \
        node.value[0].value == 'session' and \
        node.value[1].value == 'clear' and \
        node.value[2].type == 'call'
        ) is not None
    assert clear_call, \
        'Are you calling the `session.clear()` function?'
    
    return_redirect = get_route(auth_code, 'logout').find('return', lambda node: \
        node.value[0].value == 'redirect' and \
        node.value[1].type == 'call')
    return_redirect_exists = return_redirect is not None
    assert return_redirect_exists, \
        'Are you returning a call to the `redirect()` function?'

    url_for_call = return_redirect.find_all('atomtrailers', lambda node: \
        node.value[0].value == 'url_for' and \
        node.value[1].type == 'call')
    url_for_call_exists = url_for_call is not None
    assert url_for_call_exists, \
        'Are you passing a call to the `url_for()` function to the `redirect()` function?'

    url_for_args = list(url_for_call.find_all('call_argument').map(lambda node: str(node.target) + ':' + str(node.value.value).replace("'", '"')))
    url_content = 'None:"admin.login"' in url_for_args
    assert url_content, \
        "Are you passing the `'admin.login'` route to the `url_for()` function?"

    logout_el = template_data('layout').select('a.button.is-light')
    logout_exists = len(logout_el) == 1
    assert logout_exists, \
        'Have you added an `<a>` with the correct attributes to the `navbar-item` `<div>` in `layout.html`?'
    
    a_contents_len = len(logout_el[0].contents) >= 1 
    assert a_contents_len, \
            'Does your logout link contain the word `Logout`?'

    a_contents = (logout_el[0].contents[0]).lower() == 'logout'
    assert a_contents, \
        'Does your logout link contain the word `Logout`?'

    links = 'admin.logout:' in template_functions('layout', 'url_for')
    assert links, \
        'Do you have an `href` with a call to `url_for` pointing to `admin.logout`?'

@pytest.mark.test_admin_protect_routes_module1
def test_admin_protect_routes_module1():
    # 15. Admin - Protect Routes
    # Protect all routes with the custom decorator.
    # from cms.admin import auth
    # @auth.protected
    admin_import = get_imports(admin_module_code, 'cms.admin')
    admin_import_exits = admin_import is not None
    assert admin_import_exits, \
        'Do you have a `cms.admin` import statement?'
    auth_exists = 'auth' in admin_import
    assert auth_exists, \
        'Are you importing `auth` from `cms.admin` in `cms/admin/__init__.py`?'
    function_names = ['content', 'create', 'edit', 'settings', 'users']
    decorators = list(admin_module_code.find_all('decorator', lambda node: \
        str(node.value) == 'auth.protected').map(lambda node: node.parent.name))
    decorators.sort()
    decorators_exist = function_names == decorators
    assert decorators_exist, \
        'Have you added the `@auth.protected` decorator to the five route functions in `admin/__init.py`?'

    content_last_decorator = admin_module_code.find('def', lambda node: \
        node.name == 'content' and \
        str(node.decorators[-1].value) == 'auth.protected') is not None
    assert content_last_decorator, \
        'Is the `@auth.protected` decorator immediately above the `content` function?'

    create_last_decorator = admin_module_code.find('def', lambda node: \
        node.name == 'create' and \
        str(node.decorators[-1].value) == 'auth.protected') is not None
    assert create_last_decorator, \
        'Is the `@auth.protected` decorator immediately above the `create` function?'

    edit_last_decorator = admin_module_code.find('def', lambda node: \
        node.name == 'edit' and \
        str(node.decorators[-1].value) == 'auth.protected') is not None
    assert edit_last_decorator, \
        'Is the `@auth.protected` decorator immediately above the `edit` function?'

    settings_last_decorator = admin_module_code.find('def', lambda node: \
        node.name == 'settings' and \
        str(node.decorators[-1].value) == 'auth.protected') is not None
    assert settings_last_decorator, \
        'Is the `@auth.protected` decorator immediately above the `settings` function?'

    users_last_decorator = admin_module_code.find('def', lambda node: \
        node.name == 'users' and \
        str(node.decorators[-1].value) == 'auth.protected') is not None
    assert users_last_decorator, \
        'Is the `@auth.protected` decorator immediately above the `users` function?'
#!
