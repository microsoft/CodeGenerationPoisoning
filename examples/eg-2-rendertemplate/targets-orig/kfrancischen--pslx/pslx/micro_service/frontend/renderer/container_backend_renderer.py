import datetime
from galaxy_py import gclient
from flask import render_template, request
from flask_login import login_required
from pslx.micro_service.frontend import pslx_frontend_ui_app, pslx_frontend_logger
from pslx.schema.enums_pb2 import Status, ModeType, DataModelType
from pslx.schema.storage_pb2 import ContainerBackendValue
from pslx.storage.proto_table_storage import ProtoTableStorage
from pslx.util.env_util import EnvUtil
from pslx.util.file_util import FileUtil
from pslx.util.proto_util import ProtoUtil
from pslx.util.timezone_util import TimezoneUtil

container_backend_config = pslx_frontend_ui_app.config['frontend_config'].container_backend_config
backend_folder = FileUtil.join_paths_to_dir(
    root_dir=EnvUtil.get_pslx_env_variable('PSLX_INTERNAL_METADATA_DIR'),
    base_name='PSLX_CONTAINER_BACKEND_TABLE'
)
galaxy_viewer_url = pslx_frontend_ui_app.config['frontend_config'].galaxy_viewer_url
if galaxy_viewer_url and galaxy_viewer_url[-1] == '/':
    galaxy_viewer_url = galaxy_viewer_url[:-1]


def get_containers_info():
    containers_info = []
    existing_containers = {}
    all_proto_files = set()
    if not FileUtil.is_local_path(backend_folder):
        all_cells = ['']
    else:
        all_cells = gclient.list_cells()

    for cell_name in all_cells:
        folder = FileUtil.convert_local_to_cell_path(
            path=backend_folder, cell=cell_name)
        proto_files = FileUtil.list_files_in_dir(folder)
        all_proto_files = all_proto_files.union(set(proto_files))
    for proto_file in all_proto_files:
        storage = ProtoTableStorage()
        storage.initialize_from_file(
            file_name=proto_file
        )
        raw_data = storage.read_all()
        if not raw_data:
            continue
        key = sorted(raw_data.keys())[-1]
        val = raw_data[key]
        result_proto = ProtoUtil.any_to_message(
            message_type=ContainerBackendValue,
            any_message=val
        )
        ttl = result_proto.ttl

        if ttl > 0 and result_proto.updated_time and TimezoneUtil.cur_time_in_pst() - TimezoneUtil.cur_time_from_str(
                result_proto.updated_time) >= datetime.timedelta(days=ttl):
            FileUtil.remove_file(storage.get_file_name())
        else:
            container_info = {
                'container_name': result_proto.container_name,
                'status': ProtoUtil.get_name_by_value(
                    enum_type=Status, value=result_proto.container_status),
                'updated_time': result_proto.updated_time,
                'mode': ProtoUtil.get_name_by_value(enum_type=ModeType, value=result_proto.mode),
                'data_model': ProtoUtil.get_name_by_value(
                    enum_type=DataModelType, value=result_proto.data_model),
                'run_cell': result_proto.run_cell,
                'snapshot_cell': result_proto.snapshot_cell,
            }
            if container_info['container_name'] not in existing_containers:
                existing_containers[container_info['container_name']] = container_info['updated_time']
                containers_info.append(container_info)
            else:
                if container_info['updated_time'] >= existing_containers[container_info['container_name']]:
                    containers_info.append(container_info)

    return containers_info


def get_container_info(container_name, cell_name, start_time):
    container_info = {
        'log_file': '',
        'start_time': '',
        'end_time': '',
        'counter_info': [],
    }
    operators_info = []
    folder = FileUtil.convert_local_to_cell_path(
        path=backend_folder, cell=cell_name)
    pslx_frontend_logger.info(
        "Container backend checking folder [" + folder + '].')
    storage = ProtoTableStorage()
    storage.initialize_from_file(
        FileUtil.join_paths_to_file(
            root_dir=folder,
            base_name=container_name + '.pb'
        )
    )
    raw_data = storage.read_all()
    all_past_run = []
    for key in sorted(list(raw_data.keys()), reverse=True):
        val = ProtoUtil.any_to_message(
            message_type=ContainerBackendValue,
            any_message=raw_data[key]
        )
        all_past_run.append(
            {
                'start_time': val.start_time,
                'updated_time': val.updated_time,
                'end_time': val.end_time,
                'status': ProtoUtil.get_name_by_value(
                    enum_type=Status, value=val.container_status),
                'run_cell': val.run_cell,
                'snapshot_cell': val.snapshot_cell,
            }
        )
        if len(all_past_run) > 10:
            break

    key = start_time if start_time else sorted(raw_data.keys())[-1]
    val = raw_data[key]
    result_proto = ProtoUtil.any_to_message(
        message_type=ContainerBackendValue,
        any_message=val
    )
    container_info['log_file'] = galaxy_viewer_url + result_proto.log_file
    container_info['start_time'] = result_proto.start_time
    container_info['end_time'] = result_proto.end_time
    for key in sorted(dict(result_proto.counters).keys()):
        container_info['counter_info'].append(
            {
                'name': key,
                'count': result_proto.counters[key],
            }
        )
    for key, val in dict(result_proto.operator_info_map).items():
        operators_info.append({
            'operator_name': key,
            'status': ProtoUtil.get_name_by_value(
                enum_type=Status, value=val.status),
            'start_time': val.start_time,
            'end_time': val.end_time,
            'dependencies': ', '.join(val.parents),
            'log_file': galaxy_viewer_url + val.log_file,
        })
    return (container_info, sorted(operators_info, key=lambda x: (x['dependencies'], x['operator_name'])),
            all_past_run)


@pslx_frontend_ui_app.route("/container_backend.html", methods=['GET', 'POST'])
@login_required
def container_backend():
    containers_info = get_containers_info()
    try:
        return render_template(
            'container_backend.html',
            containers_info=sorted(
                containers_info, key=lambda x: x['container_name'])
        )
    except Exception as err:
        pslx_frontend_logger.error(
            "Got error rendering container_backend.html: " + str(err) + '.')
        return render_template(
            'container_backend.html',
            containers_info=[]
        )


@pslx_frontend_ui_app.route('/view_container', methods=['GET', 'POST'])
@login_required
def view_container():
    container_name = request.args.get('container_name')
    cell_name = request.args.get('cell')
    start_time = request.args.get('start_time')
    container_info, operators_info, all_past_run = get_container_info(
        container_name=container_name,
        cell_name=cell_name,
        start_time=start_time
    )
    try:
        return render_template(
            'container_backend_container_viewer.html',
            container_name=container_name,
            container_info=container_info,
            operators_info=operators_info,
            all_past_run=all_past_run
        )
    except Exception as err:
        pslx_frontend_logger.error(
            "Got error rendering container_backend.html: " + str(err) + '.')
        return render_template(
            'container_backend_container_viewer.html',
            container_name=str(err),
            container_info=container_info,
            operators_info=[],
            all_past_run=[]
        )
