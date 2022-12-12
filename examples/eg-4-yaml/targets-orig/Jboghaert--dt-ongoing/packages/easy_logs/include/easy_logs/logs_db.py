import os
from collections import OrderedDict, namedtuple, defaultdict

import duckietown_utils as dtu
from duckietown_utils.yaml_pretty import yaml_dump_pretty
from .constants import EasyLogsConstants
from .logs_structure import PhysicalLog, yaml_from_physical_log, physical_log_from_yaml
from .resource_desc import create_dtr_version_1, DTR, get_local_filepath, NotLocalPath
from .time_slice import filters_slice



def get_easy_logs_db2(do_not_use_cloud, do_not_use_local, ignore_cache):
    if ignore_cache:
        delete_easy_logs_cache()

    db = EasyLogsDB()

    if not do_not_use_cloud:
        logs_cloud = dtu.get_cached(EasyLogsConstants.CACHE_CLOUD, get_logs_cloud, just_delete=False)
        assert isinstance(logs_cloud, OrderedDict)
        db.update_logs(logs_cloud)

    if not do_not_use_local:
        logs_local = dtu.get_cached(EasyLogsConstants.CACHE_LOCAL, get_logs_local, just_delete=False)
        db.update_logs(logs_local)

    return db


def invalidate_log_cache_because_downloaded():
    dtu.get_cached(EasyLogsConstants.CACHE_LOCAL, lambda: None, just_delete=True)


def delete_easy_logs_cache():
    dtu.get_cached(EasyLogsConstants.CACHE_LOCAL, lambda: None, just_delete=True)
    dtu.get_cached(EasyLogsConstants.CACHE_CLOUD, lambda: None, just_delete=True)

    cache_dir = dtu.get_duckietown_cache_dir()
    fn = os.path.join(cache_dir, 'candidate_cloud.yaml')

    if os.path.exists(fn):
        dtu.logger.info('Removing %s' % fn)
        os.unlink(fn)


def write_candidate_cloud(logs):
    cache_dir = dtu.get_duckietown_cache_dir()
    fn = os.path.join(cache_dir, 'candidate_cloud.yaml')
    s = yaml_representation_of_phy_logs(logs)
    dtu.write_data_to_file(s, fn)

    # try reading
    print('reading back logs')
    logs2 = logs_from_yaml(dtu.yaml_load_plain(s))
    print('read back %s' % len(logs2))


def logs_from_yaml(data):
    dtu.check_isinstance(data, dict)

    res = OrderedDict()
    for k, d in data.items():
        res[k] = physical_log_from_yaml(d)
    return res


def yaml_representation_of_phy_logs(logs):
    dtu.check_isinstance(logs, dict)
    res = OrderedDict()
    for k, l in logs.items():
        res[k] = yaml_from_physical_log(l)
    s = yaml_dump_pretty(res)
    return s


def get_logs_cloud():
    cloud_file = dtu.require_resource('cloud2.yaml')

    with dtu.timeit_wall("loading DB"):
        dtu.logger.info('Loading cloud DB %s' % dtu.friendly_path(cloud_file))
        with dtu.timeit_wall('YAML load file'):
            data = dtu.yaml_load_file(cloud_file, plain_yaml=True)
        # with dtu.timeit_wall('plain'):
        #     data = open(cloud_file).read()
        #     import yaml
        #     yaml.load(data)

        dtu.logger.debug('Conversion')
        logs = logs_from_yaml(data)

    logs = OrderedDict(logs)
    dtu.logger.info('Loaded cloud DB with %d entries.' % len(logs))

    return logs


class EasyLogsDB(object):
    _singleton = None

    def __init__(self):
        # ordereddict str -> PhysicalLog
        self.logs = OrderedDict()

    def update_logs(self, logs2):
        self.logs.update(logs2)

    @dtu.contract(returns=OrderedDict, query='str|list(str)')
    def query(self, query, raise_if_no_matches=True):
        return query_logs(logs=self.logs, query=query, raise_if_no_matches=raise_if_no_matches)


@dtu.contract(returns=OrderedDict, query='str|list(str)')
def query_logs(logs, query, raise_if_no_matches=True):
    """
        query: a string or a list of strings

        Returns an OrderedDict str -> PhysicalLog.

        The query can also be a filename.

    """
    if isinstance(query, list):
        res = OrderedDict()
        for q in query:
            res.update(query_logs(logs, q, raise_if_no_matches=False))
        if raise_if_no_matches and not res:
            msg = "Could not find any match for the queries:"
            for q in query:
                msg += '\n- %s' % q
            raise dtu.DTNoMatches(msg)
        return res
    else:
        dtu.check_isinstance(query, str)

        filters = OrderedDict()
        filters.update(filters_slice)
        filters.update(dtu.filters0)
        aliases = OrderedDict()
        aliases.update(logs)
        # adding aliases unless we are asking for everything
        if query != '*':
            # print('adding more (query = %s)' % query)
            for _, log in logs.items():
                dtr = DTR.from_yaml(log.resources['bag'])

                original_name = dtr.name

                # print ('alias: %s %s' % (original_name, dtr.name))
                aliases[original_name] = log
                original_name = original_name.replace('.bag', '')
                aliases[original_name] = log

        result = dtu.fuzzy_match(query, aliases, filters=filters,
                                 raise_if_no_matches=raise_if_no_matches)
        # remove doubles after
        # XXX: this still has bugs
        present = defaultdict(set)
        for k, v in result.items():
            present[id(v)].add(k)

        def choose(options):
            if len(options) == 1:
                return list(options)[0]
            else:
                options = sorted(options, key=len)
                return options[0]

        c = OrderedDict()
        for k, v in result.items():
            chosen = choose(present[id(v)])
            if k == chosen:
                c[k] = v

        return c


def _read_stats(pl, use_filename):
    assert isinstance(pl, PhysicalLog)

    info = dtu.rosbag_info_cached(use_filename)
    if info is None:
        return pl._replace(valid=False, error_if_invalid='Not indexed')

    # print yaml.dump(info)
    length = info['duration']
    if length is None:
        return pl._replace(valid=False, error_if_invalid='Empty bag.')

    pl = pl._replace(length=length, t0=0, t1=length, bag_info=info)

    try:
        vehicle = which_robot_from_bag_info(info)
        pl = pl._replace(vehicle=vehicle, has_camera=True)
    except ValueError:
        vehicle = None
        pl = pl._replace(valid=False, error_if_invalid='No camera data.')

    date_ms = info['start']
    if date_ms < 156600713:
        pl = pl._replace(valid=False, error_if_invalid='Date not set.')
    else:
        date = dtu.format_time_as_YYYY_MM_DD(date_ms)
        pl = pl._replace(date=date)

    return pl


def which_robot_from_bag_info(info):
    import re
    pattern = r'/(\w+)/camera_node/image/compressed'
    for topic in info['topics']:
        m = re.match(pattern, topic['topic'])
        if m:
            vehicle = m.group(1)
            return vehicle
    msg = 'Could not find a topic matching %s' % pattern
    raise ValueError(msg)


def is_valid_name(basename):
    forbidden = [',', '(', 'conflicted'
                 # , ' '
                 ]
    for f in forbidden:
        if f in basename:
            return False
    return True


def _get_base_base(x):
    if not '.' in x:
        msg = 'Invalid: %s' % x
        raise ValueError(msg)
    return x[:x.index('.')]


AllResources = namedtuple('AllResources',
                          'basename2filename base2basename2filename')


@dtu.memoize_simple
def get_all_resources():
    patterns = [
        '*.bag',
        # We only care about <log>.XXX.mp4
        '*.*.mp4',
        '*.*.jpg',
        '*.*.webm',
        '*.*.png',
        '*.*.mov',
        '*.*.mts',
        '*.*.gif',
    ]
    basename2filename = dtu.look_everywhere_for_files(patterns=patterns, silent=True)
    base2basename2filename = defaultdict(lambda: {})
    for basename, fn in basename2filename.items():
        base = _get_base_base(basename)
        #        print('basename: %s base: %s filename: %s' % (basename, base, fn))
        base2basename2filename[base][basename] = fn
    return AllResources(basename2filename=basename2filename,
                        base2basename2filename=base2basename2filename)


def get_logs_local():
    raise_if_duplicated = False
    all_resources = get_all_resources()

    logs = OrderedDict()
    ignored = []
    for basename, filename in all_resources.basename2filename.items():
        if not basename.endswith('.bag'):
            continue

        censor = ['ii-datasets', 'RCDP', '160122_3cars_dark-mercedes']
        to_censor = False
        for c in censor:
            if c in filename:
                to_censor = True
        if to_censor:
            ignored.append(filename)
            dtu.logger.warn('Ignoring %s' % filename)
            continue

        if not is_valid_name(basename):
            msg = 'Ignoring Bag file with invalid file name "%r".' % (basename)
            msg += '\n Full path: %s' % filename
            dtu.logger.warn(msg)
            continue

        base = _get_base_base(basename)

        if basename != base + '.bag':
            continue
        #        print('basename: %s base: %s filename: %s related : %s' % (basename, base, filename,
        #                                                      related))
        l = physical_log_from_filename(filename, all_resources.base2basename2filename)

        if l.log_name in logs:
            old = logs[l.log_name]

            old_sha1 = DTR.from_yaml(old.resources['bag']).hash['sha1']
            new_sha1 = DTR.from_yaml(l.resources['bag']).hash['sha1']

            if old_sha1 == new_sha1:
                # just a duplicate
                msg = 'File is a duplicate: %s ' % filename
                dtu.logger.warn(msg)
                continue
            # Actually a different log
            msg = 'Found twice this log: %s' % l.log_name
            msg += '\nProbably it is a processed version.'
            msg += "\n\nVersion 1:"

            msg += '\n\n' + dtu.indent(str(old), '  ')
            msg += "\n\n\nVersion 2:"
            msg += '\n\ncurrent: %s' % filename
            msg += '\n\ncurrent: %s' % ("RCDP" in filename)
            msg += '\n\n' + dtu.indent(str(l), '  ')
            if raise_if_duplicated:
                raise Exception(msg)
            else:
                dtu.logger.error(msg)

        logs[l.log_name] = l

    return logs


@dtu.contract(returns=PhysicalLog, filename=str)
def physical_log_from_filename(filename, base2basename2filename):
    """

        related: basename -> filename
    """
    date = None
    size = os.stat(filename).st_size
    b = os.path.basename(filename)
    base, bagext = os.path.splitext(b)
    if bagext != '.bag':
        raise Exception(filename)

    def ignore_record(rname):
        forbidden = [' ',  # names with spaces,
                     'active.avi',
                     'bag.info.yaml',
                     'bag.info ',
                     'zip',
                     ".timestamps",
                     ".metadata.yaml",
                     ]
        for f in forbidden:
            if f in rname:
                #                msg = 'Ignoring resource %s' % rname
                #                dtu.logger.warning(msg)
                return True

        return False

    description = OrderedDict()

    resources = OrderedDict()

    l = PhysicalLog(log_name=base,  # might be replaced later
                    resources=resources,
                    description=description,
                    length=None,
                    t0=None, t1=None,
                    date=date,
                    size=size,
                    has_camera=None,
                    vehicle=None,
                    filename=None,
                    #                    filename=filename,
                    bag_info=None,
                    valid=True,
                    error_if_invalid=None)

    l = _read_stats(l, use_filename=filename)
    if l.bag_info is not None:
        start = l.bag_info['start']
        canonical = dtu.format_time_as_YYYYMMDDHHMMSS(start)

        if l.vehicle is not None:
            s = l.vehicle
            M = 8
            if len(s) > M:
                s = s[:M]
        else:
            s = 'unknown'
        canonical = canonical + '_' + s
        # print('canonical: %s' % canonical)
        l = l._replace(log_name=canonical)

    possible_bases = set()
    possible_bases.add(base)
    possible_bases.add(l.log_name)

    for _base in possible_bases:
        for s, filename_resource in base2basename2filename[_base].items():
            basedot = _base + '.'
            if s.startswith(basedot):
                rest = s[len(basedot):]
                record_name = rest.lower()
                if not ignore_record(record_name):
                    dtr = create_dtr_version_1(filename_resource)
                    resources[record_name] = dtr

    # at least the bag file should be present
    assert 'bag' in resources

    return l


class NotAvailableLocally(Exception):
    pass


def get_local_file(dtr):
    """ Returns the local hostname if it exists, otherwise raises NotAvailableLocally() """
    for url in dtr['urls']:
        try:
            filename = get_local_filepath(url)
            if not os.path.exists(filename):
                msg = 'DB said this file existed but it does not: %s' % url
                dtu.logger.error(msg)
                continue
            return filename
        except NotLocalPath:
            pass
    msg = 'None of the paths are local:\n%s' % "\n".join(dtr['urls'])
    raise NotAvailableLocally(msg)


def get_local_bag_file(log):
    """
    Raise NotAvailableLocally.
    :param log:
    :return:
    """
    dtr = log.resources['bag']
    return get_local_file(dtr)
