import yaml

import rx
import rx.operators as ops

import cyclotron_std.sys.argv as argv
import cyclotron_std.argparse as argparse
import cyclotron_std.io.file as file
import cyclotron_consul.kv as kv


def parse_config():
    def _parse_config(config_data):
        ''' takes a stream with the content of the configuration file as input
        and returns a (hot) stream of arguments .
        '''
        return config_data.pipe(
            ops.map(lambda i: yaml.load(i, Loader=yaml.FullLoader)),
            ops.replay(buffer_size=1),
            ops.ref_count(),
        )

    return _parse_config


def parse_arguments(args, prog=None):
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument(
        '--config', required=True,
        help="Path of the configuration file")

    return args.pipe(
        ops.skip(1),
        argparse.parse(parser),
    )


def read_config_from_file(filename, file_response, scheduler=None):
    read_request, read_response = filename.pipe(
        ops.map(lambda i: file.Read(id='config', path=i)),
        file.read(file_response),
    )

    if scheduler is not None:
        read_request = read_request.pipe(
            ops.subscribe_on(scheduler),
        )

    config = read_response.pipe(
        ops.filter(lambda i: i.id == "config"),
        ops.flat_map(lambda i: i.data),
        parse_config(),
    )
    return config, read_request


def read_config_from_consul(kv_adapter, endpoint, key):

    value = kv_adapter.api.watch_key(endpoint, key).pipe(
        ops.map(lambda i: i.value),
        parse_config(),
    )

    return value


def identity_or_redirect(config, kv_adapter):
    '''Returns the configuration data as is, or the content from a redirection.

    Args:
        config: Dict containing the configuration content.
        kv_adapter: Consul adapter, used to monitor the configuration.

    Returns:
        Observable of configuration items
        Observable of http requests
    '''
    if 'redirect' in config and config['redirect']['connector'] == 'consul':
        return read_config_from_consul(
            kv_adapter,
            config['redirect']['endpoint'],
            config['redirect']['key'])
    else:
        return rx.just(config)


def read_config_from_args(args,
                          file_response, http_response,
                          scheduler=None):
    args = parse_arguments(args)
    filename = args.pipe(
        ops.filter(lambda i: i.key == 'config'),
        ops.map(lambda i: i.value),
    )

    config, read_request = read_config_from_file(
        filename, file_response,
        scheduler)

    kv_adapter = kv.adapter(http_response)
    config = config.pipe(
        ops.flat_map(lambda i: identity_or_redirect(i, kv_adapter))
    )

    return config, read_request, kv_adapter.sink
