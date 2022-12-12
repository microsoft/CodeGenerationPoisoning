import yaml

class ConfigReader:

    CONFIG_FILE = 'config.yaml'

    def read(self):
        with open(self.CONFIG_FILE, 'r') as stream:
            data_loaded = yaml.safe_load(stream)

        return data_loaded

class ProvidersConfig(ConfigReader):

    PROVIDERS = 'providers'

    STORAGE = 'storage'
    COMMUNICATION_CHANNEL = 'communication_channel'
    FORMS_PLATFORM = 'forms_platform'

    GOOGLE_DRIVE = "google_drive"

    GMAIL = "gmail"
    SLACK = "slack"

    GOOGLE_FORMS = "google_forms"

    def read_storage_provider(self):
        config = super().read()
        return config.get(self.PROVIDERS).get(self.STORAGE)

    def read_communication_channel_provider(self):
        config = super().read()
        return config.get(self.PROVIDERS).get(self.COMMUNICATION_CHANNEL)

    def read_forms_platform_provider(self):
        config = super().read()
        return config.get(self.PROVIDERS).get(self.FORMS_PLATFORM)

class EvalProcessConfig(ConfigReader):

    EVAL_PROCESS = 'eval_process'

    ID = 'id'
    DUE_DATE = 'due_date'

    FEATURE_DISABLING = 'feature_disabling'
    ADD_COMENTER_TO_EVAL_REPORT = 'add_comenter_to_eval_reports'

    def read_eval_process_id(self):
        config = super().read()
        return config.get(self.EVAL_PROCESS).get(self.ID)

    def read_eval_process_due_date(self):
        config = super().read()
        return config.get(self.EVAL_PROCESS).get(self.DUE_DATE)

    def read_is_add_comenter_to_eval_reports_enabled(self):
        config = super().read()
        return config.get(
            self.EVAL_PROCESS).get(
                self.FEATURE_DISABLING).get(
                    self.ADD_COMENTER_TO_EVAL_REPORT)

class SlackProviderConfig(ConfigReader):

    SLACK_PROVIDER = 'slack_provider'

    TOKEN = 'token'
    IS_DIRECT_MESSAGE = 'is_direct_message'
    PARAMS = 'params'

    PARAMS_CHANNEL = 'channel'
    PARAMS_AS_USER = 'as_user'
    USERS_MAP = 'users_map'

    def get_slack_token(self):
        config = super().read()
        return config.get(self.SLACK_PROVIDER).get(self.TOKEN)

    def get_slack_channel_param(self):
        config = super().read()
        return config.get(self.SLACK_PROVIDER).get(self.PARAMS).get(self.PARAMS_CHANNEL)

    def slack_message_is_direct(self):
        config = super().read()
        return config.get(self.SLACK_PROVIDER).get(self.IS_DIRECT_MESSAGE)

    def slack_message_as_user_param(self):
        config = super().read()
        return config.get(self.SLACK_PROVIDER).get(self.PARAMS).get(self.PARAMS_AS_USER)

    def get_slack_users_map(self):
        config = super().read()
        return config.get(self.SLACK_PROVIDER, []).get(self.USERS_MAP, [])

class GmailProviderConfig(ConfigReader):

    GMAIL_PROVIDER = 'gmail_provider'

    MAIL_SUBJECT = 'mail_subject'
    REMINDER_MAIL_SUBJECT = 'reminder_mail_subject'

    def read_mail_subject(self):
        config = super().read()
        return config.get(self.GMAIL_PROVIDER).get(self.MAIL_SUBJECT)

    def read_reminder_mail_subject(self):
        config = super().read()
        return config.get(self.GMAIL_PROVIDER).get(self.REMINDER_MAIL_SUBJECT)

class GoogleDriveProviderConfig(ConfigReader):

    GOOGLE_DRIVE_PROVIDER = 'google_drive_provider'

    FOLDER = 'folder'
    FORM_RESPONSES_FOLDER = 'form_responses_folder'
    ASSIGNMENTS_FOLDER = 'assignments_folder'
    ASSIGNMENTS_MANAGER_FORMS_FOLDER = 'assignments_manager_forms_folder'

    ORG_CHART = 'org_chart'
    ORG_CHART_RANGE = 'org_chart_range'
    FORM_MAP = 'form_map'
    FORM_MAP_RANGE = 'form_map_range'
    ASSIGNMENTS_PEERS_FILE = 'assignments_peers_file'
    ASSIGNMENTS_PEERS_RANGE = 'assignments_peers_range'
    RESPONSES_FILES_RANGE = 'responses_files_range'

    EVAL_REPORTS_FOLDER = 'eval_reports_folder'
    EVAL_REPORT_TEMPLATE_ID = 'eval_report_template_id'
    EVAL_REPORT_PREFIX_NAME = 'eval_report_prefix_name'

    FILE_PREFIXES = 'file_prefixes'
    MANAGER_EVAL_BY_REPORT = 'manager_eval_by_report'
    REPORT_EVAL_BY_MANAGER = 'report_eval_by_manager'
    PEER_EVAL_BY_PEER = 'peer_eval_by_peer'
    SELF_EVAL = 'self_eval'
    EVAL_REPORT = 'eval_report'

    def read_google_folder(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.FOLDER)

    def read_assignments_folder(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.ASSIGNMENTS_FOLDER)

    def read_assignments_manager_forms_folder(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.ASSIGNMENTS_MANAGER_FORMS_FOLDER)

    def read_google_orgchart(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.ORG_CHART)

    def read_google_orgchart_range(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.ORG_CHART_RANGE)

    def read_google_form_map(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.FORM_MAP)

    def read_google_form_map_range(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.FORM_MAP_RANGE)

    def read_assignments_peers_file(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.ASSIGNMENTS_PEERS_FILE)

    def read_assignments_peers_range(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.ASSIGNMENTS_PEERS_RANGE)

    def read_google_responses_folder(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.FORM_RESPONSES_FOLDER)

    def read_google_responses_files_range(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.RESPONSES_FILES_RANGE)

    def read_eval_reports_folder(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.EVAL_REPORTS_FOLDER)

    def read_google_eval_report_template_id(self):
        config = super().read()
        return config.get(self.GOOGLE_DRIVE_PROVIDER).get(self.EVAL_REPORT_TEMPLATE_ID)

    def read_google_eval_report_prefix(self):
        config = super().read()
        return config.get(
            self.GOOGLE_DRIVE_PROVIDER).get(self.FILE_PREFIXES).get(self.EVAL_REPORT)

    def read_google_manager_eval_by_report_prefix(self):
        config = super().read()
        return config.get(
            self.GOOGLE_DRIVE_PROVIDER).get(self.FILE_PREFIXES).get(self.MANAGER_EVAL_BY_REPORT)

    def read_google_report_eval_by_manager_prefix(self):
        config = super().read()
        return config.get(
            self.GOOGLE_DRIVE_PROVIDER).get(self.FILE_PREFIXES).get(self.REPORT_EVAL_BY_MANAGER)

    def read_google_peer_eval_by_peer_prefix(self):
        config = super().read()
        return config.get(
            self.GOOGLE_DRIVE_PROVIDER).get(self.FILE_PREFIXES).get(self.PEER_EVAL_BY_PEER)

    def read_google_self_eval_prefix(self):
        config = super().read()
        return config.get(
            self.GOOGLE_DRIVE_PROVIDER).get(self.FILE_PREFIXES).get(self.SELF_EVAL)

class CompanyConfig(ConfigReader):

    COMPANY = 'company'
    DOMAIN = 'domain'
    NUMBER_OF_EMPLOYEES = 'number_of_employees'

    def read_company_domain(self):
        config = super().read()
        return config.get(self.COMPANY).get(self.DOMAIN)

    def read_company_number_of_employees(self):
        config = super().read()
        return config.get(self.COMPANY).get(self.NUMBER_OF_EMPLOYEES)

class Config(
        ProvidersConfig,
        EvalProcessConfig,
        SlackProviderConfig,
        GmailProviderConfig,
        GoogleDriveProviderConfig,
        CompanyConfig):
    'Composition of configs'
