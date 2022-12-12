import logging
from collections import OrderedDict

from flask import Flask, jsonify, render_template, request

from grice.db_service import DBService, DEFAULT_PAGE, DEFAULT_PER_PAGE, ColumnSort, SORT_DIRECTIONS, \
    ColumnPair, TableJoin, QueryArguments, SUPPORTED_FUNCS
from grice.complex_filter import ComplexFilter, ColumnFilter, ColumnFunction
from grice.errors import NotFoundError, JoinError

log = logging.getLogger(__name__)  # pylint: disable=invalid-name

def parse_pagination(page, per_page):
    try:
        page = int(page) - 1
    except (ValueError, TypeError):
        page = DEFAULT_PAGE

    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = DEFAULT_PER_PAGE

    if page < 0:
        page = DEFAULT_PAGE

    return page, per_page


def parse_filter(filter_string: str):
    """
    Parses a filter string from the URL.

    expected format:
        column_name,filter_type,value for single value filters i.e. eq, lt, gt.
        column_name,filter_type,values;delimited;with;semicolons for multi-value filters i.e. in, not_in, between.

    :param filter_string: the filter string from the URL.
    :return: ColumnFilter
    """
    column_name, filter_type, url_value = [s.strip() for s in filter_string.split(',')]

    return ColumnFilter(column_name, filter_type, url_value=url_value)

def _parse_filter_obj_dict(filters: dict, from_url: bool = False):
    """
    Parses a filter JSON dictionary.

    expected format:
        { "[OR|AND]" : [ ... list of filters ... ] }
        where a filter is either the above dict, or:
        column_name,filter_type,values;delimited;with;semicolons for multi-value filters i.e. in, not_in, between, or:
        [column_name, filter_type, values]

    :param filter_string: the filter dictionary.
    :param from_url: whether the data source was a URL parameter
    :return: ComplexFilter
    """

    if 'AND' in filters and 'OR' in filters:
        raise ValueError('Expecting an AND or an OR in the filter, not both')

    if 'AND' in filters:
        # Find any ANDed filters that are on the same column - assume that should be an OR
        grouped_filters = OrderedDict()
        combos = []
        for column_filter in filters.get('AND', []):
            filter_obj = parse_filter_obj(column_filter, from_url)
            if isinstance(filter_obj, ComplexFilter):
                combos.append(filter_obj)
            else:
                column_name = filter_obj.column_name
                if column_name not in grouped_filters:
                    grouped_filters[column_name] = []
                grouped_filters[column_name].append(filter_obj)

        combined_filters = []
        for filter_list in grouped_filters.values():
            if len(filter_list) == 1:
                combined_filters.append(filter_list[0])
            else:
                combined_filters.append(ComplexFilter(filter_list, False))
        list_of_filters = combos + combined_filters

    elif 'OR' in filters:
        list_of_filters = [parse_filter_obj(f, from_url) for f in filters.get('OR', [])]
    else:
        raise ValueError('Expecting an AND or an OR in the filter')

    return ComplexFilter(list_of_filters, 'AND' in filters)

def parse_filter_obj(filters, from_url=False):

    if isinstance(filters, dict):
        return _parse_filter_obj_dict(filters)

    if isinstance(filters, list):
        if len(filters) != 3:
            raise ValueError('Filter not correct length: {}'.format(str(filters)))
        if from_url:
            return ColumnFilter(filters[0], filters[1], url_value=filters[2])
        return ColumnFilter(filters[0], filters[1], value=filters[2])

    if isinstance(filters, str):
        return parse_filter_obj([s.strip() for s in filters.split(',')], from_url=True)


def parse_filters(filter_description: dict):
    """
    Parses the filter strings from the URL.

    :param filter_description: Dictionary defining the ANDs and ORs required for the filter
    :return: ComplexFilter object
    """

    filter_list = [parse_filter_obj(filter_description)]

    if filter_list:
        return ComplexFilter(list_of_filters=filter_list)

    return None


def parse_sort(sort_string):
    """
    Parses a sort from the URL.

    expected format: column_name,direction where direction is 'asc' or 'desc'

    :param sort_string: string
    :return:
    """
    table_name = None
    column_name, direction = [s.strip() for s in sort_string.split(',')]
    direction = direction.lower()

    if column_name == '':
        raise ValueError('column_name cannot be blank')

    if direction.lower() not in SORT_DIRECTIONS:
        raise ValueError('invalid sort direction')

    try:
        table_name, column_name = column_name.split('.')
    except ValueError:
        # This means the column name is not in the table_name.column_name format, which is fine.
        pass

    return ColumnSort(table_name, column_name, direction)


def parse_sorts(sort_list):
    """
    This method parses sort strings from the URL.

    :param sort_list:
    :return:
    """

    # It only makes sense to have one sort per column, so we stash sorts in a dict. If multiple sorts exist for a
    # column, then we only keep the last sort for that column.
    sorts = OrderedDict()

    for sort_string in sort_list:
        try:
            column_sort = parse_sort(sort_string)
        except ValueError:
            continue

        sorts[column_sort.column_name] = column_sort

    if len(sorts):
        return list(sorts.values())

    return None


def parse_join(join_str, outer_join: bool):
    """
    Parses the join string from the URL.

    Expected format: table_name,from_col:to_col;from_col:to_col

    :param join_str: The join= string from the URL
    :param outer_join: boolean, true if the join is an outer join, false for inner join.
    :return: TableJoin
    """
    # TODO: find a way to notify user of bad join. Should we just completely fail? Should we just warn them?

    if join_str is None:
        return None

    try:
        table_name, column_pair_strings = join_str.split(',')
    except ValueError:
        return None

    column_pair_strings = column_pair_strings.split(';')
    column_pairs = []

    for column_pair_string in column_pair_strings:
        from_column, to_column = column_pair_string.strip().split(':')
        column_pairs.append(ColumnPair(from_column, to_column))

    if len(column_pairs) == 0:
        return None

    return TableJoin(table_name, column_pairs, outer_join)


def parse_column_func(column_string):
    """
    Parses a column from the URL.

    expected format: column_name
    expected format: function:column_name where function is 'avg' or 'count' etc
    expected format: function:column_name::operator::value where operator is DIV, + etc
    expected format: column_name::operator::value

    :param sort_string: string
    :return:
    """
    table_name = None
    clean_vals = [s.strip() for s in column_string.split('::')]
    if len(clean_vals) == 3:
        column_string, operator_name, operator_value = clean_vals
    else:
        column_string = clean_vals[0]
        operator_name = None
        operator_value = None

    clean_vals = [s.strip() for s in column_string.split(':')]
    column_name = clean_vals[-1]
    func_name = None

    if len(clean_vals) > 1:
        func_name = clean_vals[0].lower()

    if not func_name and column_name == '':
        raise ValueError('column_name cannot be blank')

    if func_name and func_name not in SUPPORTED_FUNCS:
        raise ValueError('invalid function')

    try:
        table_name, column_name = column_name.split('.')
    except ValueError:
        # This means the column name is not in the table_name.column_name format, which is fine.
        pass

    return ColumnFunction(table_name, column_name, func_name, operator_name, operator_value)

def parse_column_funcs(column_list):
    """
    This method parses column strings from the URL.

    :param column_list:
    :return:
    """

    funcs = []
    for col_string in column_list:
        try:
            column_func = parse_column_func(col_string)
        except ValueError:
            continue
        funcs.append(column_func)

    return funcs

def parse_col_names(column_names):
    """
    This method takes a string of comma-seperated column names and returns a list of unique
    column names, preserving order.

    :param column_names: string
    :return: column_names: list
    """
    if column_names:
        clean_cols = (column_name.strip() for column_name in column_names)
        unique_ordered = OrderedDict.fromkeys(clean_cols)
        return list(unique_ordered)

    return column_names

def parse_query_args(query_args):
    """
    This method takes the query string from the request and returns all of the items related to the query API.

    :param query_args: The query args from flask.request.args
    :return: column_names: list, page: int, per_page: int, filters: dict
    """
    page, per_page = parse_pagination(query_args.get('page'), query_args.get('perPage'))
    filters = parse_filters(dict(AND=query_args.getlist('filter')))
    sorts = parse_sorts(query_args.getlist('sort'))
    join = parse_join(query_args.get('join'), False) or parse_join(query_args.get('outerjoin'), True)
    column_names = parse_column_funcs(query_args.getlist('columns')) or parse_column_funcs(query_args.get('cols', '').split(','))
    group_by = parse_column_funcs(query_args.getlist('group_by', None))

    return column_names, page, per_page, filters, sorts, join, group_by


def table_not_found(name):
    code = 404
    error_title = "{}: Table Not Found".format(code)
    msg = 'A table with name "{}" could not be found.'.format(name)

    return render_template('error.html', code=code, error_title=error_title, msg=msg), code


class DBController:
    def __init__(self, app: Flask, db_service: DBService):
        self.app = app
        self.db_service = db_service
        self.register_routes()

    def get_query_args(self):
        content = request.get_json(silent=True)

        if not content:
            column_names, page, per_page, filters, sorts, join, group_by = parse_query_args(request.args)
            quargs = QueryArguments(column_names, page, per_page, filters, sorts, join, group_by,
                                    format_as_list=request.args.get('_list', '').lower() in ['t', 'true', '1'])

        else:
            page, per_page = parse_pagination(content.get('page'), content.get('perPage'))
            filters = parse_filters(content.get('filter', []))
            sorts = parse_sorts(content.get('sort', []))
            join = parse_join(content.get('join'), False) or parse_join(content.get('outerjoin'), True)
            column_names = parse_column_funcs(content.get('columns', [])) or parse_column_funcs(content.get('cols', '').split(','))
            group_by = parse_column_funcs(content.get('group_by', []))
            quargs = QueryArguments(column_names, page, per_page, filters, sorts, join, group_by, content.get('_list'))

        return quargs

    def tables_api(self):
        return jsonify(schemas=self.db_service.get_tables())

    tables_api.methods = ['GET']

    def table_api(self, name):
        try:
            table_info = self.db_service.get_table(name)
        except NotFoundError as e:
            return jsonify(success=False, error=str(e)), 404

        return jsonify(**table_info)

    table_api.methods = ['GET', 'POST']

    def query_api(self, name):
        quargs = self.get_query_args()

        try:
            table_info = self.db_service.get_table(name)
        except NotFoundError as e:
            return jsonify(success=False, error=str(e)), 404

        try:
            rows, columns = self.db_service.query_table(name, quargs)
        except JoinError as e:
            return jsonify(error=str(e)), 400

        return jsonify(table=table_info, rows=rows, columns=columns)

    query_api.methods = ['GET', 'POST']

    def tables_page(self):
        tables = self.db_service.get_tables()

        return render_template('tables.html', tables=tables)

    tables_page.methods = ['GET']

    def table_page(self, name):
        quargs = self.get_query_args()

        try:
            table = self.db_service.get_table(name)
        except NotFoundError:
            return table_not_found(name)

        rows, columns = self.db_service.query_table(name, quargs)
        title = "{} - Grice".format(name)

        return render_template('table.html', title=title, table=table, rows=rows, columns=columns, page=quargs.page + 1,
                               per_page=quargs.per_page)

    def chart_page(self, name):
        quargs = self.get_query_args()
        join_table = None

        try:
            table = self.db_service.get_table(name)
        except NotFoundError:
            return table_not_found(name)

        if quargs.join:
            try:
                join_table = self.db_service.get_table(quargs.join.table_name)
            except NotFoundError:
                # Bad join table name. Should probably warn the user, but ignoring for now.
                pass

        title = "{} - Charting - Grice".format(name)

        columns = table['columns']

        if join_table:
            columns = columns + join_table['columns']

        return render_template('chart.html', title=title, table=table, columns=columns)

    table_page.methods = ['GET']

    def register_routes(self):
        # API Routes
        self.app.add_url_rule('/api/db/tables', 'tables_api', self.tables_api)
        self.app.add_url_rule('/api/db/tables/<name>', 'table_api', self.table_api)
        self.app.add_url_rule('/api/db/tables/<name>/query', 'query_api', self.query_api)

        # HTML Pages
        self.app.add_url_rule('/db', 'db_index', self.tables_page)
        self.app.add_url_rule('/db/tables', 'tables_page', self.tables_page)
        self.app.add_url_rule('/db/tables/<name>', 'table_page', self.table_page)
        self.app.add_url_rule('/db/tables/<name>/chart', 'chart_page', self.chart_page)
