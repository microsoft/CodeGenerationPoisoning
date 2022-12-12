import os
import sys
import pathlib
import unittest
import yaml
import orthauth as oa
from .common import test_folder, s1, s2


class TestDeprecations(unittest.TestCase):
    def test_d_dynamic_config(self):
        auth = oa.configure_here('auth-config.py', __name__)
        dc = auth.dynamic_config


class TestAuthConfig(unittest.TestCase):
    def test_auth_config_in_binary_blob(self):
        auth = oa.configure_here('auth-config.py', __name__)
        blob = auth.load()
        assert blob == {'config-search-paths': ['../test/configs/user-1.yaml'],
                        'auth-variables': {'hrm': 'derp'}}

    def test_bad_alt_config(self):
        try:
            auth = oa.configure(test_folder / 'auth-config-bad-alt-config.yaml')
            auth.get('test')
            raise AssertionError('should have failed')
        except oa.exceptions.BadAuthConfigFormatError:
            pass


class TestConfigure(unittest.TestCase):
    def setUp(self):
        with open(test_folder / 'auth-config-1.yaml', 'rt') as f:
            self.tv = yaml.safe_load(f)

    def test_configure(self):
        auth = oa.configure(test_folder / 'auth-config-1.yaml')
        test = auth.load()
        assert test == self.tv

    def test_configure_here(self):
        auth = oa.configure_here('auth-config-0.yaml', __name__)
        test = auth.load()
        tv = {'config-search-paths': ['configs/user-1.yaml'],
              'auth-variables': {'default-example': None}}
        assert test == tv

    def test_configure_relative(self):
        auth = oa.configure_relative('auth-config-0.yaml')
        test = auth.load()
        tv = {'config-search-paths': ['configs/user-1.yaml'],
              'auth-variables': {'default-example': None}}
        assert test == tv


class TestSimple(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'auth-config-1.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_null_path(self):
        assert self.auth.get('test-null-path') is None
        assert self.auth.get_path('test-null-path') is None

    def test_config_vars(self):
        g = self.auth.get('test-config-vars')
        d = self.auth.get_default('test-config-vars')
        assert g != d
        gtv = self.auth._pathit(g)
        dtv = self.auth._pathit(d)
        assert gtv != dtv

        test = self.auth.get_path('test-config-vars')
        assert test == pathlib.Path(sys.prefix, 'share/orthauth/.does-not-exist')
        assert test == gtv
        assert test != dtv

    def test_get_default(self):
        g = self.auth.get('test-config-vars')
        d = self.auth.get_default('test-config-vars')
        assert g != d
        gtv = self.auth._pathit(g)
        dtv = self.auth._pathit(d)
        assert gtv != dtv

        test = self.auth.get_path_default('test-config-vars')
        assert test == pathlib.Path.cwd() / 'share/orthauth/.does-not-exist'
        assert test != gtv
        assert test == dtv

    def test_user(self):
        print(self.auth)
        assert self.auth.user_config._path == self.auth.user_config_path, 'big oops'

    def test_tangential(self):
        @self.auth.tangential('api_key', 'full-complexity-example')
        class Test:
            pass

        assert Test.api_key, [d for d in dir(Test) if not d.startswith('__')]

    def test_tangential_env_none(self):
        @self.auth.tangential('should_be_none', 'test-env-none')
        class Test:
            pass

        assert Test.should_be_none is None

    def test_tangential_init_env_none(self):
        @self.auth.tangential_init('should_be_none', 'test-env-none')
        class Test:
            pass

        t = Test()
        assert t.should_be_none is None

    def test_path_list_variant(self):
        assert self.auth.get('paths-as-list-example') == 'lol'

    def test_path_strings(self):
        assert self.auth.get('paths-example') == 'yay!'

    def test_implicit_env(self):
        assert self.auth.get('env-example') == os.environ.get('USER', None)

    def test_env_list(self):
        tv = 'so'
        os.environ['QUITE'] = tv
        try:
            assert self.auth.get('env-list-example') == tv
        finally:
            os.environ.pop('QUITE')

    def test_env_none(self):
        assert self.auth.get('test-env-none') is None

    def test_expanduser(self):
        tv = pathlib.Path('~/').expanduser()
        assert self.auth.get_path('test-expanduser') == tv

    def test_default(self):
        assert self.auth.get('default-example') == 42

    def test_multi_path_1(self):
        assert self.auth.get_path('test-multi-path-1') == self.auth._path

    def test_multi_path_2(self):
        assert self.auth.get_path('test-multi-path-2') == self.auth.user_config._path

    def test_multi_path_3(self):
        assert self.auth.get_path('test-multi-path-3') == self.auth.user_config._path

    def test_get_list(self):
        tv = self.auth.get_list('test-get-list')
        assert tv == ['this', 'is', 'a', 'list', 'from', 'user', 'config']

    def test_get_list_default(self):
        tv = self.auth.get_list('test-get-list-default')
        assert tv == ['this', 'is', 'a', 'list', 'default']

    def test_get_list_empty(self):
        tv = self.auth.get_list('test-get-list-empty')
        assert isinstance(tv, list) and not tv

    def test_get_list_not_in_user_config(self):
        tv = self.auth.get_list('test-get-list-not-in-user-config')
        assert isinstance(tv, list) and not tv

    def test_get_list_default_and_user(self):
        tv = self.auth.get_list('test-get-list-default-and-user')
        assert tv == ['user']

    def test_key_only_in_user_config(self):
        # FIXME the issue only surfaces if the value is None which is bad
        tv_nn = self.auth.get('test-key-only-in-user-config-not-null')
        assert tv_nn == 'hello'
        # we need to warn on this ?? I'm pretty sure that I have made
        # use of the ability to do this at some point in time to issue
        # a patch fix or something like that, might be worth keeping for
        # that reason?
        try:
            tv = self.auth.get('test-key-only-in-user-config')
            # FIXME not sure if correct behavior, pretty sure
            # we don't want this to fall through here but
            # instead want it to be an error because it is
            # something can only happen during development
            # since it requires the code to know about an
            # auth variable that the auth config does not contain
            # FIXME we may have to do this in the linting pass
            assert tv == None
            assert False, 'should not get here? see comments'
        except KeyError as e:
            pass


class TestMakeUserConfig(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'auth-config-1.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_exists(self):
        try:
            self.auth.write_user_config()
            raise AssertionError('should not have written')
        except oa.exceptions.ConfigExistsError:
            pass

    def test_make_user(self):
        output = self.auth._make_user()
        assert output['auth-variables'].keys() == self.auth.get_blob('auth-variables').keys(), 'hrm'

    def _roundtrip(self, format):
        ser = self.auth._serialize_user_config(format=format)
        reloaded = self.auth._load_string(ser, format)
        test = self.auth._make_user()
        assert reloaded == test, 'roundtrip failed for {format}'

    def test_serialize_json(self):
        self._roundtrip('json')

    def test_serialize_py(self):
        self._roundtrip('py')

    def test_serialize_yaml(self):
        self._roundtrip('yaml')

    def test_serialize_sxpr(self):
        self._roundtrip('sxpr')


class TestWithStores(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'auth-config-8.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_path_relative_store(self):
        tv = s2.parent / 'some-other-relative-path.ext'
        test = self.auth.get_path('rel-secrets-path')
        assert test == tv


class TestPathInConfig(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'auth-config-9.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_path_in_user_config(self):
        tv = test_folder / 'somewhere-else' / 'some-other-file.ext'
        test = self.auth.get_path('path-in-user-config')
        assert test == tv

    def test_paths_in_user_config(self):
        tv = test_folder / 'somewhere-else' / 'some-other-file.ext'
        test = self.auth.get_path('paths-in-user-config')
        assert test == tv


class TestConfigPathNoKeyFilePath(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'auth-get-path.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_get_file_path_from_config_path(self):
        # the case where a default value is a valid path in a secrets
        # files could be added to linting, but cannot be default
        # behavior due to ambiguity
        try:
            test = self.auth.get_path('some-path-var')
            assert False, 'should have failed'
        except oa.exceptions.SomethingWrongWithVariableInConfig as e:
            pass

    def test_config_path_ok(self):
        tv = test_folder / 'somewhere-else' / 'some-other-file.ext'
        test = self.auth.get_path('spv-1')
        assert test == tv

    def test_config_path_missing(self):
        try:
            test = self.auth.get_path('spv-2')
            assert False, 'should have failed'
        except oa.exceptions.SecretError as e:
            pass

    def test_config_path_beyond(self):
        try:
            test = self.auth.get_path('spv-3')
            assert False, 'should have failed'
        except oa.exceptions.SecretError as e:
            pass


class TestBadPaths(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'auth-config-bad-paths.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_path_relative_store(self):
        try:
            test = self.auth.get_path('test')
            assert False, 'should have failed'
        except oa.exceptions.SomethingWrongWithVariableInConfig as e:
            print(e)


class TestEmptySecrets(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'auth-config-empty-secrets.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_empty_path(self):
        try:
            test = self.auth.get_path('missing')
            assert False, 'should have failed'
        except oa.exceptions.EmptyConfigError as e:
            print(e)

    def test_empty_value(self):
        try:
            test = self.auth.get('missing')
            assert False, 'should have failed'
        except oa.exceptions.EmptyConfigError as e:
            print(e)
