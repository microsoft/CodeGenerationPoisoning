import ssl

import ldap3

from lookup import sds_mock_connection_factory
from utilities import certs, config, integration_adaptors_logger as log, secrets

import definitions
from utilities.string_utilities import str2bool

_LDAP_CONNECTION_RETRIES = int(config.get_config('LDAP_CONNECTION_RETRIES', default='3'))
_LDAP_CONNECTION_TIMEOUT_IN_SECONDS = int(config.get_config('LDAP_CONNECTION_TIMEOUT_IN_SECONDS', default='5'))
logger = log.IntegrationAdaptorsLogger(__name__)


def build_sds_connection(ldap_address: str) -> ldap3.Connection:
    """
    Given an ldap service address this will return a ldap3 connection object
    """
    ldap3.set_config_parameter('RESTARTABLE_TRIES', _LDAP_CONNECTION_RETRIES)
    server = ldap3.Server(ldap_address, connect_timeout=_LDAP_CONNECTION_TIMEOUT_IN_SECONDS)
    logger.info('Configuring LDAP connection without TLS')
    return _configure_ldap_connection(server)


def build_sds_connection_tls(ldap_address: str, private_key: str, local_cert: str, ca_certs: str
                             ) -> ldap3.Connection:
    """
    This will return a connection object for the given ip along with loading the given certification files
    :param ldap_address: The URL of the LDAP server to connect to.
    :param private_key: A string containing the client private key.
    :param local_cert: A string containing the client certificate.
    :param ca_certs: A string containing certificate authority certificates
    :return: Connection object using the given cert files
    """
    certificates = certs.Certs.create_certs_files(definitions.ROOT_DIR, private_key=private_key, local_cert=local_cert,
                                                  ca_certs=ca_certs)

    load_tls = ldap3.Tls(local_private_key_file=certificates.private_key_path,
                         local_certificate_file=certificates.local_cert_path, validate=ssl.CERT_REQUIRED,
                         version=ssl.PROTOCOL_TLSv1, ca_certs_file=certificates.ca_certs_path)

    ldap3.set_config_parameter('RESTARTABLE_TRIES', _LDAP_CONNECTION_RETRIES)
    server = ldap3.Server(ldap_address, use_ssl=True, tls=load_tls, connect_timeout=_LDAP_CONNECTION_TIMEOUT_IN_SECONDS)
    logger.info('Configuring LDAP connection using TLS')

    return _configure_ldap_connection(server)


def _configure_ldap_connection(server) -> ldap3.Connection:
    lazy_ldap = str2bool(config.get_config("LAZY_LDAP", default=str(True)))
    if lazy_ldap:
        connection = ldap3.Connection(server,
                                      lazy=True,
                                      auto_bind=ldap3.AUTO_BIND_NO_TLS,
                                      client_strategy=ldap3.ASYNC)
    else:
        connection = ldap3.Connection(server,
                                      auto_bind=True,
                                      client_strategy=ldap3.REUSABLE)
    logger.info('LDAP connection configured successfully')
    return connection


def create_connection() -> ldap3.Connection:
    if config.get_config(sds_mock_connection_factory.LDAP_MOCK_DATA_URL_CONFIG_KEY, default=None):
        return sds_mock_connection_factory.build_mock_sds_connection()
    else:
        sds_url = config.get_config("SDS_URL")
        disable_tls_flag = config.get_config("DISABLE_SDS_TLS", None)
        use_tls = disable_tls_flag != "True"
        logger.info('Configuring connection to SDS using {url} {tls}', fparams={"url": sds_url, "tls": use_tls})
        return build_real_sds_connection(sds_url, use_tls)


def build_real_sds_connection(sds_url: str, tls: bool = True) -> ldap3.Connection:
    """Initialise the real SDS connection object

    :param sds_url: The URL to communicate with SDS on.
    :param tls: A flag to indicate whether TLS should be enabled for the SDS connection.
    :return:
    """
    logger.info('Configuring connection to SDS using {url} {tls}', fparams={"url": sds_url, "tls": tls})

    if tls:
        client_key = secrets.get_secret_config('CLIENT_KEY')
        client_cert = secrets.get_secret_config('CLIENT_CERT')
        ca_certs = secrets.get_secret_config('CA_CERTS')

        sds_connection = build_sds_connection_tls(ldap_address=sds_url,
                                                  private_key=client_key,
                                                  local_cert=client_cert,
                                                  ca_certs=ca_certs)
    else:
        sds_connection = build_sds_connection(ldap_address=sds_url)

    return sds_connection
