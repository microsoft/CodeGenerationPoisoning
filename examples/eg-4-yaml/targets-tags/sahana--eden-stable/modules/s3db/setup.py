# -*- coding: utf-8 -*-

""" Sahana Eden Setup Model:
        * Installation of a Deployment
        * Configuration of a Deployment
        * Managing a Deployment (Start/Stop/Clean instances)
        * Monitoring of a Deployment
        * Upgrading a Deployment (tbc)

    @copyright: 2015-2020 (c) Sahana Software Foundation
    @license: MIT

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use,
    copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following
    conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    OTHER DEALINGS IN THE SOFTWARE.
"""

__all__ = ("S3DNSModel",
           "S3GandiDNSModel",
           "S3GoDaddyDNSModel",
           "S3CloudModel",
           "S3AWSCloudModel",
           "S3OpenStackCloudModel",
           "S3EmailProviderModel",
           "S3GoogleEmailModel",
           "S3SMTPModel",
           "S3SetupDeploymentModel",
           "S3SetupMonitorModel",
           "setup_instance_deploy",
           "setup_instance_settings_read",
           "setup_monitor_run_task",
           "setup_monitor_task_restart",
           "setup_monitor_check_email_reply",
           #"setup_write_playbook",
           "setup_run_playbook",
           #"setup_DeploymentRepresent",
           #"setup_MonitorTaskRepresent",
           #"Storage2",
           "setup_rheader",
           )

import json
import os
import random
import string
import sys
import time

from gluon import *

from ..s3 import *
from s3compat import basestring

TIME_FORMAT = "%b %d %Y %H:%M:%S"
MSG_FORMAT = "%(now)s - %(category)s - %(data)s\n\n"

WEB_SERVERS = {#1: "apache",
               2: "cherokee",
               3: "nginx",
               }

DB_SERVERS = {#1: "mysql",
              2: "postgresql",
              ##3: "sqlite",
              }

INSTANCE_TYPES = {1: "prod",
                  2: "setup",
                  3: "test",
                  4: "demo",
                  }

# =============================================================================
class S3DNSModel(S3Model):
    """
        Domain Name System (DNS) Providers
        - super-entity
    """

    names = ("setup_dns",
             "setup_dns_id",
             )

    def model(self):

        T = current.T
        db = current.db

        #----------------------------------------------------------------------
        # Super entity
        #
        dns_types = Storage(setup_gandi_dns = T("Gandi LiveDNS"),
                            setup_godaddy_dns = T("GoDaddy"),
                            )

        tablename = "setup_dns"
        self.super_entity(tablename, "dns_id",
                          dns_types,
                          Field("name",
                                #label = T("Name"),
                                ),
                          Field("description",
                                #label = T("Description"),
                                ),
                          #Field("enabled", "boolean",
                          #      default = True,
                          #      #label = T("Enabled?")
                          #      #represent = s3_yes_no_represent,
                          #      ),
                          #on_define = lambda table: \
                          #  [table.instance_type.set_attributes(readable = True),
                          #   ],
                          )

        # Reusable Field
        represent = S3Represent(lookup = tablename)
        dns_id = S3ReusableField("dns_id", "reference %s" % tablename,
                                 label = T("DNS Provider"),
                                 ondelete = "SET NULL",
                                 represent = represent,
                                 requires = IS_EMPTY_OR(
                                    IS_ONE_OF(db, "setup_dns.dns_id",
                                              represent,
                                              sort = True
                                              ),
                                    ),
                                 comment = DIV(_class="tooltip",
                                               _title="%s|%s" % (T("DNS Provider"),
                                                                 T("If you use a DNS Provider configuration then you can create/update the DNS entry automatically as part of the deployment.")
                                                                 ),
                                               ),
                                 )

        # ---------------------------------------------------------------------
        # Pass names back to global scope (s3.*)
        return {"setup_dns_id": dns_id,
                }

# =============================================================================
class S3GandiDNSModel(S3DNSModel):
    """
        Gandi LiveDNS
        - DNS Provider Instance

        https://doc.livedns.gandi.net/
    """

    names = ("setup_gandi_dns",)

    def model(self):

        #T = current.T

        # ---------------------------------------------------------------------
        tablename = "setup_gandi_dns"
        self.define_table(tablename,
                          self.super_link("dns_id", "setup_dns"),
                          Field("name",
                                requires = IS_NOT_EMPTY(),
                                ),
                          Field("description"),
                          #Field("enabled", "boolean",
                          #      default = True,
                          #      #label = T("Enabled?"),
                          #      represent = s3_yes_no_represent,
                          #      ),
                          Field("api_key", "password",
                                readable = False,
                                requires = IS_NOT_EMPTY(),
                                widget = S3PasswordWidget(),
                                ),
                          # Currently only supports a single Domain per DNS configuration
                          Field("domain", # Name
                                requires = IS_NOT_EMPTY(),
                                ),
                          # Currently only supports a single Zone per DNS configuration
                          Field("zone", # UUID
                                requires = IS_NOT_EMPTY(),
                                ),
                          *s3_meta_fields())

        self.configure(tablename,
                       super_entity = "setup_dns",
                       )

        # ---------------------------------------------------------------------
        return {}

# =============================================================================
class S3GoDaddyDNSModel(S3DNSModel):
    """
        GoDaddy DNS
        - DNS Provider Instance

        https://developer.godaddy.com/
    """

    names = ("setup_godaddy_dns",)

    def model(self):

        #T = current.T

        # ---------------------------------------------------------------------
        tablename = "setup_godaddy_dns"
        self.define_table(tablename,
                          self.super_link("dns_id", "setup_dns"),
                          Field("name",
                                requires = IS_NOT_EMPTY(),
                                ),
                          Field("description"),
                          #Field("enabled", "boolean",
                          #      default = True,
                          #      #label = T("Enabled?"),
                          #      represent = s3_yes_no_represent,
                          #      ),
                          # Currently only supports a single Domain per DNS configuration
                          Field("domain", # Name
                                requires = IS_NOT_EMPTY(),
                                ),
                          Field("api_key",
                                requires = IS_NOT_EMPTY(),
                                ),
                          Field("secret", "password",
                                readable = False,
                                requires = IS_NOT_EMPTY(),
                                widget = S3PasswordWidget(),
                                ),
                          *s3_meta_fields())

        self.configure(tablename,
                       super_entity = "setup_dns",
                       )

        # ---------------------------------------------------------------------
        return {}

# =============================================================================
class S3CloudModel(S3Model):
    """
        Clouds
        - super-entity
    """

    names = ("setup_cloud",
             "setup_cloud_id",
             )

    def model(self):

        T = current.T
        db = current.db

        #----------------------------------------------------------------------
        # Super entity
        #
        cloud_types = Storage(setup_aws_cloud = T("Amazon Web Services"),
                              setup_openstack_cloud = T("OpenStack"),
                              )

        tablename = "setup_cloud"
        self.super_entity(tablename, "cloud_id",
                          cloud_types,
                          Field("name",
                                #label = T("Name"),
                                ),
                          Field("description",
                                #label = T("Description"),
                                ),
                          #Field("enabled", "boolean",
                          #      default = True,
                          #      #label = T("Enabled?")
                          #      #represent = s3_yes_no_represent,
                          #      ),
                          #on_define = lambda table: \
                          #  [table.instance_type.set_attributes(readable = True),
                          #   ],
                          )

        # Reusable Field
        represent = S3Represent(lookup = tablename)
        cloud_id = S3ReusableField("cloud_id", "reference %s" % tablename,
                                   label = T("Cloud"),
                                   ondelete = "SET NULL",
                                   represent = represent,
                                   requires = IS_EMPTY_OR(
                                    IS_ONE_OF(db, "setup_cloud.cloud_id",
                                              represent,
                                              sort = True
                                              ),
                                    ),
                                   comment = DIV(_class="tooltip",
                                                 _title="%s|%s" % (T("Cloud"),
                                                                   T("If you use a Cloud configuration then you can create the server(s) automatically as part of the deployment.")
                                                                   ),
                                                 ),
                                   )

        # ---------------------------------------------------------------------
        # Pass names back to global scope (s3.*)
        return {"setup_cloud_id": cloud_id,
                }

# =============================================================================
class S3AWSCloudModel(S3CloudModel):
    """
        Amazon Web Services
        - Cloud Instance

        https://docs.ansible.com/ansible/latest/scenario_guides/guide_aws.html
        https://docs.ansible.com/ansible/latest/modules/ec2_module.html
    """

    names = ("setup_aws_cloud",
             "setup_aws_server",
             )

    def model(self):

        #T = current.T

        configure = self.configure
        define_table = self.define_table

        # ---------------------------------------------------------------------
        # AWS Cloud Configuration
        #
        tablename = "setup_aws_cloud"
        define_table(tablename,
                     # Instance of Super-Entity
                     self.super_link("cloud_id", "setup_cloud"),
                     Field("name",
                           requires = IS_NOT_EMPTY(),
                           ),
                     Field("description"),
                     #Field("enabled", "boolean",
                     #      default = True,
                     #      #label = T("Enabled?"),
                     #      represent = s3_yes_no_represent,
                     #      ),
                     Field("access_key", "password",
                           readable = False,
                           requires = IS_NOT_EMPTY(),
                           widget = S3PasswordWidget(),
                           ),
                     Field("secret_key", "password",
                           readable = False,
                           requires = IS_NOT_EMPTY(),
                           widget = S3PasswordWidget(),
                           ),
                     *s3_meta_fields())

        configure(tablename,
                  super_entity = "setup_cloud",
                  )

        # ---------------------------------------------------------------------
        # AWS Server Details
        #
        #aws_instance_types = ["t3.micro",
        #                      ]
        #aws_regions = {"eu-west-2": "Europe (London)",
        #               }
        tablename = "setup_aws_server"
        define_table(tablename,
                     self.setup_server_id(),
                     Field("region",
                           default = "eu-west-2", # Europe (London)
                           #label = T("Region"),
                           #requires = IS_IN_SET(aws_regions),
                           #represent = S3Represent(options = aws_regions)
                           ),
                     Field("instance_type",
                           default = "t3.micro",
                           #label = T("Instance Type"),
                           #requires = IS_IN_SET(aws_instance_types),
                           ),
                     Field("image",
                           # https://wiki.debian.org/Cloud/AmazonEC2Image/Buster
                           default = "ami-042796b8e41bb5fad", # Debian 10 in London
                           #label = T("Image"), # AMI ID
                           ),
                     Field("reserved_instance", "boolean",
                           default = False,
                           #label = T("Reserved Instance"),
                           ),
                     Field("security_group",
                           default = "default",
                           #label = T("Security Group"),
                           ),
                     Field("instance_id",
                           #label = T("Instance ID"),
                           # Normally populated automatically:
                           writable = False,
                           ),
                     *s3_meta_fields())

        configure(tablename,
                  ondelete = self.setup_aws_server_ondelete,
                  )

        # ---------------------------------------------------------------------
        return {}

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_aws_server_ondelete(row):
        """
            Cleanup Tasks when a Server is Deleted
            - AWS Instance
            - AWS Keypair
        """

        db = current.db
        s3db = current.s3db
        stable = s3db.setup_server
        cstable = s3db.setup_aws_server
        dtable = s3db.setup_deployment
        ctable = s3db.setup_aws_cloud

        # Only deleted_fks are in the row object
        aws_server = db(cstable.id == row.id).select(cstable.region,
                                                     cstable.instance_id,
                                                     limitby = (0, 1)
                                                     ).first()
        region = aws_server.region

        query = (stable.id == row.server_id) & \
                (dtable.id == stable.deployment_id) & \
                (dtable.cloud_id == ctable.cloud_id)
        deployment = db(query).select(ctable.access_key,
                                      ctable.secret_key,
                                      stable.name,
                                      limitby = (0, 1)
                                      ).first()

        server_name = deployment["setup_server.name"]
        cloud = deployment["setup_aws_cloud"]
        access_key = cloud.access_key
        secret_key = cloud.secret_key

        playbook = [{"hosts": "localhost",
                     "connection": "local",
                     "gather_facts": "no",
                     "tasks": [# Terminate AWS Instance
                               {"ec2": {"aws_access_key": access_key,
                                        "aws_secret_key": secret_key,
                                        "region": region,
                                        "instance_ids": aws_server.instance_id,
                                        "state": "absent",
                                        },
                                    },
                               # Delete Keypair
                               {"ec2_key": {"aws_access_key": access_key,
                                            "aws_secret_key": secret_key,
                                            "region": region,
                                            "name": server_name,
                                            "state": "absent",
                                            },
                                },
                               ],
                     },
                    ]

        # Write Playbook
        name = "aws_server_ondelete_%d" % int(time.time())
        task_vars = setup_write_playbook("%s.yml" % name,
                                         playbook,
                                         )

        # Run Playbook
        #task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
        current.s3task.schedule_task(name,
                                     vars = task_vars,
                                     function_name = "setup_run_playbook",
                                     repeats = None,
                                     timeout = 6000,
                                     #sync_output = 300
                                     )

# =============================================================================
class S3OpenStackCloudModel(S3CloudModel):
    """
        OpenStack
        - Cloud Instance

        https://www.openstack.org
        https://docs.ansible.com/ansible/latest/modules/os_server_module.html
    """

    names = ("setup_openstack_cloud",
             "setup_openstack_server",
             )

    def model(self):

        #T = current.T

        configure = self.configure
        define_table = self.define_table

        # ---------------------------------------------------------------------
        # OpenStack Cloud Configuration
        #
        tablename = "setup_openstack_cloud"
        define_table(tablename,
                     # Instance of Super-Entity
                     self.super_link("cloud_id", "setup_cloud"),
                     Field("name",
                           requires = IS_NOT_EMPTY(),
                           ),
                     Field("description"),
                     #Field("enabled", "boolean",
                     #      default = True,
                     #      #label = T("Enabled?"),
                     #      represent = s3_yes_no_represent,
                     #      ),
                     Field("auth_url",
                           requires = IS_URL(),
                           ),
                     Field("username",
                           requires = IS_NOT_EMPTY(),
                           ),
                     Field("password", "password",
                           readable = False,
                           requires = IS_NOT_EMPTY(),
                           widget = S3PasswordWidget(),
                           ),
                     Field("project_name",
                           requires = IS_NOT_EMPTY(),
                           ),
                     Field("domain_name",
                           default = "Default",
                           requires = IS_NOT_EMPTY(),
                           ),
                     *s3_meta_fields())

        configure(tablename,
                  super_entity = "setup_cloud",
                  )

        # ---------------------------------------------------------------------
        # OpenStack Server Details
        #
        tablename = "setup_openstack_server"
        define_table(tablename,
                     self.setup_server_id(),
                     Field("instance_type",
                           default = "m1.small", # Varies by Deployment, this matches OSUOSL
                           #label = T("Flavor"),
                           #requires = IS_IN_SET(openstack_instance_types), # Varies by Deployment
                           ),
                     Field("image",
                           default = "Debian 10.1", # Varies by Deployment, this matches OSUOSL
                           #label = T("Image"), # Image Name or ID
                           ),
                     Field("volume_size", "integer",
                           default = 8, # Gb
                           #label = T("Volume Size (Gb)"),
                           ),
                     Field("network",
                           default = "general_servers1", # Varies by Deployment, this matches OSUOSL
                           #label = T("Security Group"),
                           ),
                     Field("security_group",
                           default = "default",
                           #label = T("Security Group"),
                           ),
                     Field("region",
                           default = "RegionOne", # Varies by Deployment, this matches OSUOSL
                           #label = T("Region"),
                           #requires = IS_IN_SET(openstack_regions), # Varies by Deployment
                           #represent = S3Represent(options = aws_regions)
                           ),
                     Field("availability_zone",
                           default = "nova", # Varies by Deployment, this matches OSUOSL
                           #label = T("Availability Zone"),
                           ),
                     *s3_meta_fields())

        configure(tablename,
                  ondelete = self.setup_openstack_server_ondelete,
                  )

        # ---------------------------------------------------------------------
        return {}

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_openstack_server_ondelete(row):
        """
            Cleanup Tasks when a Server is Deleted
            - OpenStack Instance
            - OpenStack Keypair
        """

        db = current.db
        s3db = current.s3db
        stable = s3db.setup_server
        dtable = s3db.setup_deployment
        ctable = s3db.setup_openstack_cloud

        query = (stable.id == row.server_id) & \
                (dtable.id == stable.deployment_id) & \
                (dtable.cloud_id == ctable.cloud_id)
        deployment = db(query).select(ctable.auth_url,
                                      ctable.username,
                                      ctable.password,
                                      ctable.project_name,
                                      ctable.domain_name,
                                      stable.name,
                                      limitby = (0, 1)
                                      ).first()

        server_name = deployment["setup_server.name"]
        cloud = deployment["setup_openstack_cloud"]
        auth = {"auth_url": cloud.auth_url,
                "username": cloud.username,
                "password": cloud.password,
                "project_name": cloud.project_name,
                "domain_name": cloud.domain_name,
                }

        playbook = [{"hosts": "localhost",
                     "connection": "local",
                     "gather_facts": "no",
                     "tasks": [# Terminate OpenStack Instance
                               {"os_server": {"auth": auth,
                                              "name": server_name,
                                              "state": "absent",
                                              },
                                },
                               # Delete Keypair
                               {"os_keypair": {"auth": auth,
                                               "name": server_name,
                                               "state": "absent",
                                               },
                                },
                               ],
                     },
                    ]

        # Write Playbook
        name = "openstack_server_ondelete_%d" % int(time.time())
        task_vars = setup_write_playbook("%s.yml" % name,
                                         playbook,
                                         )

        # Run Playbook
        #task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
        current.s3task.schedule_task(name,
                                     vars = task_vars,
                                     function_name = "setup_run_playbook",
                                     repeats = None,
                                     timeout = 6000,
                                     #sync_output = 300
                                     )

# =============================================================================
class S3EmailProviderModel(S3Model):
    """
        Email Providers (we just use Groups currently)
        - super-entity
    """

    names = ("setup_email",
             "setup_email_id",
             )

    def model(self):

        T = current.T
        db = current.db

        #----------------------------------------------------------------------
        # Super entity
        #
        email_types = Storage(setup_google_email = T("Google"),
                              )

        tablename = "setup_email"
        self.super_entity(tablename, "email_id",
                          email_types,
                          Field("name",
                                #label = T("Name"),
                                ),
                          Field("description",
                                #label = T("Description"),
                                ),
                          #Field("enabled", "boolean",
                          #      default = True,
                          #      #label = T("Enabled?")
                          #      #represent = s3_yes_no_represent,
                          #      ),
                          #on_define = lambda table: \
                          #  [table.instance_type.set_attributes(readable = True),
                          #   ],
                          )

        # Reusable Field
        represent = S3Represent(lookup = tablename)
        email_id = S3ReusableField("email_id", "reference %s" % tablename,
                                   label = T("Email Group Provider"),
                                   ondelete = "SET NULL",
                                   represent = represent,
                                   requires = IS_EMPTY_OR(
                                    IS_ONE_OF(db, "setup_email.email_id",
                                              represent,
                                              sort = True
                                              ),
                                   ),
                                   comment = DIV(_class="tooltip",
                                                 _title="%s|%s" % (T("Email Group Provider"),
                                                                   T("If you use an Email Group Provider configuration then you can create/update the Email Sender entry automatically as part of the deployment.")
                                                                   ),
                                                 ),
                                   )

        # ---------------------------------------------------------------------
        # Pass names back to global scope (s3.*)
        return {"setup_email_id": email_id,
                }

# =============================================================================
class S3GoogleEmailModel(S3EmailProviderModel):
    """
        Google
        - Email Group Provider Instance

        https://developers.google.com/admin-sdk/directory/v1/guides/manage-groups

        https://github.com/googleapis/google-api-python-client
        # NB Only supports Python 3.x
    """

    names = ("setup_google_email",
             "setup_google_instance",
             )

    def model(self):

        T = current.T
        configure = self.configure
        define_table = self.define_table

        # ---------------------------------------------------------------------
        tablename = "setup_google_email"
        define_table(tablename,
                     self.super_link("email_id", "setup_email"),
                     Field("name",
                           requires = IS_NOT_EMPTY(),
                           ),
                     Field("description"),
                     #Field("enabled", "boolean",
                     #      default = True,
                     #      #label = T("Enabled?"),
                     #      represent = s3_yes_no_represent,
                     #      ),
                     Field("credentials", "json",
                           requires = IS_JSONS3(),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Credentials"),
                                                           T("JSON of the Service Account.")
                                                           ),
                                         ),
                           ),
                     Field("email",
                           requires = IS_EMAIL(),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Email"),
                                                           T("A User account with Administrative access.")
                                                           ),
                                         ),
                           ),
                     *s3_meta_fields())

        configure(tablename,
                  super_entity = "setup_email",
                  )

        # ---------------------------------------------------------------------
        # Google Instance Details
        #
        tablename = "setup_google_instance"
        define_table(tablename,
                     self.setup_instance_id(),
                     Field("name",
                           label = T("Group Name"),
                           requires = IS_NOT_EMPTY(),
                           ),
                     Field("email",
                           label = T("Group Email"),
                           requires = IS_EMAIL(),
                           ),
                     Field("member",
                           label = T("Member Email"),
                           requires = IS_EMAIL(),
                           ),
                     Field("group_id",
                           # Normally populated automatically
                           writable = False,
                           ),
                     *s3_meta_fields())

        configure(tablename,
                  ondelete = self.setup_google_instance_ondelete,
                  )

        # ---------------------------------------------------------------------
        return {}

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_google_instance_ondelete(row):
        """
            Cleanup Tasks when a Server is Deleted
            - Google Group
        """

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        db = current.db
        s3db = current.s3db
        itable = s3db.setup_instance
        gitable = s3db.setup_google_instance
        dtable = s3db.setup_deployment
        gtable = s3db.setup_google_email

        # Only deleted_fks are in the row object
        instance_id = row.instance_id
        instance = db(gitable.id == row.id).select(gitable.group_id,
                                                   limitby = (0, 1)
                                                   ).first()

        query = (itable.id == instance_id) & \
                (dtable.id == itable.deployment_id) & \
                (dtable.email_id == gtable.id)
        deployment = db(query).select(gtable.credentials,
                                      gtable.email,
                                      limitby = (0, 1)
                                      ).first()

        creds_path = os.path.join("/", "tmp", "credentials-%s.json" % instance_id)

        with open(creds_path, "w") as creds_file:
            creds_file.write(json.dumps(deployment.credentials))

        credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes = ["https://www.googleapis.com/auth/admin.directory.group"]
                )
        credentials = credentials.with_subject(deployment.email)
        service = build("admin", "directory_v1", credentials=credentials)

        results = service.groups().delete(groupKey = instance.group_id).execute()

        if results is not None:
            current.session.warning("Couldn't delete Email Group: %s" % result)

        os.unlink(creds_path)

# =============================================================================
class S3SMTPModel(S3Model):
    """
        SMTP Smart Hosts
        - tested with:
            * AWS SES - free for 62,000 mails/month if hosting on AWS
            * SendGrid - free for 100 mails/day
    """

    names = ("setup_smtp",
             "setup_smtp_id",
             )

    def model(self):

        T = current.T
        db = current.db

        #----------------------------------------------------------------------
        # SMTP Smart Host configurations
        #
        tablename = "setup_smtp"
        self.define_table(tablename,
                          Field("name",
                                label = T("Name"),
                                requires = IS_NOT_EMPTY(),
                                ),
                          Field("description",
                                label = T("Description"),
                                ),
                          #Field("enabled", "boolean",
                          #      default = True,
                          #      label = T("Enabled?")
                          #      #represent = s3_yes_no_represent,
                          #      ),
                          Field("hostname",
                                # https://docs.aws.amazon.com/ses/latest/DeveloperGuide/smtp-connect.html
                                default = "smtp.sendgrid.net",
                                label = T("Host name"),
                                ),
                          # https://docs.aws.amazon.com/ses/latest/DeveloperGuide/smtp-credentials.html
                          Field("username",
                                default = "apikey", # Sendgrid
                                label = T("User name"),
                                requires = IS_NOT_EMPTY(),
                                ),
                          Field("password", "password",
                                label = T("Password"),
                                readable = False,
                                requires = IS_NOT_EMPTY(),
                                widget = S3PasswordWidget(),
                                ),
                          )

        # Reusable Field
        represent = S3Represent(lookup = tablename)
        smtp_id = S3ReusableField("smtp_id", "reference %s" % tablename,
                                  label = T("SMTP Smart Host"),
                                  ondelete = "SET NULL",
                                  represent = represent,
                                  requires = IS_EMPTY_OR(
                                    IS_ONE_OF(db, "setup_smtp.id",
                                              represent,
                                              sort = True
                                              ),
                                    ),
                                  comment = DIV(_class="tooltip",
                                                _title="%s|%s" % (T("SMTP Smart Host"),
                                                                  T("If you use an SMTP Smart Host, then you can configure your deployment to use it.")
                                                                  )
                                                ),
                                  )

        # ---------------------------------------------------------------------
        # Pass names back to global scope (s3.*)
        return {"setup_smtp_id": smtp_id,
                }

# =============================================================================
class S3SetupDeploymentModel(S3Model):

    names = ("setup_deployment",
             "setup_deployment_id",
             "setup_server",
             "setup_server_id",
             "setup_instance",
             "setup_instance_id",
             "setup_setting",
             )

    def model(self):

        T = current.T
        db = current.db

        add_components = self.add_components
        configure = self.configure
        crud_strings = current.response.s3.crud_strings
        define_table = self.define_table
        set_method = self.set_method

        uploadfolder = os.path.join(current.request.folder, "uploads")

        # ---------------------------------------------------------------------
        # Deployments
        #
        tablename = "setup_deployment"
        define_table(tablename,
                     # @ToDo: Add ability to get a specific hash/tag
                     Field("repo_url",
                           #default = "https://github.com/sahana/eden",
                           default = "https://github.com/sahana/eden-stable",
                           label = T("Eden Repository"),
                           requires = IS_URL(),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Eden Repository"),
                                                           T("If you wish to switch to Trunk, or use your own Fork, then you can set this here")
                                                           )
                                         ),
                           ),
                     # @ToDo: Make this a multi-select (How to handle order?)
                     Field("country", length=2,
                           label = T("Country"),
                           requires = IS_EMPTY_OR(
                                        # We provide a full list of countries here
                                        # - we then check if there are appropriate locale or sub-templates to include when we deploy
                                        IS_IN_SET_LAZY(lambda: current.gis.get_countries(key_type = "code"),
                                                       zero = current.messages.SELECT_LOCATION,
                                                       )),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Country"),
                                                           T("Selecting your country means that the appropriate locale settings can be applied. If you need to support multiple countries then leave this blank.")
                                                           )
                                         ),
                           ),
                     Field("template",
                           default = "default",
                           label = T("Template"),
                           requires = IS_IN_SET_LAZY(lambda: self.setup_get_templates(),
                                                     zero = None,
                                                     ),
                           ),
                     Field("template_manual",
                           label = T("...or enter manually"),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Template (Manual Entry)"),
                                                           T("If you want to use different template(s) than the ones available in the dropdown, then you can enter the list here as e.g. 'Template,Template.SubTemplate' (locations.Country will be prepended automatically, if set and available).")
                                                           )
                                         ),
                           ),
                     Field("webserver_type", "integer",
                           default = 3,
                           label = T("Web Server"),
                           represent = S3Represent(options = WEB_SERVERS),
                           requires = IS_IN_SET(WEB_SERVERS),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Web Server"),
                                                           T("Currently only Nginx and Cherokee is supported by this tool, although Apache should be possible with a little work.")
                                                           )
                                         ),
                           ),
                     Field("db_type", "integer",
                           default = 2,
                           label = T("Database"),
                           represent = S3Represent(options = DB_SERVERS),
                           requires = IS_IN_SET(DB_SERVERS),
                           writable = False,
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Database"),
                                                           T("Currently only PostgreSQL is supported by this tool, although MySQL should be possible with a little work.")
                                                           )
                                         ),
                           ),
                     # Set automatically
                     Field("db_password", "password",
                           readable = False,
                           writable = False,
                           ),
                     self.setup_cloud_id(),
                     self.setup_dns_id(),
                     self.setup_smtp_id(),
                     self.setup_email_id(),
                     *s3_meta_fields()
                     )

        crud_strings[tablename] = Storage(
            label_create = T("Create Deployment"),
            title_display = T("Deployment Details"),
            title_list =  T("Deployments"),
            title_update = T("Edit Deployment"),
            label_list_button =  T("List Deployments"),
            label_delete_button = T("Delete Deployment"),
            msg_record_created = T("Deployment added"),
            msg_record_modified = T("Deployment updated"),
            msg_record_deleted = T("Deployment deleted"),
            msg_list_empty = T("No Deployments currently registered"))

        configure(tablename,
                  #editable = False,
                  listadd = False, # Create method customises form
                  create_onaccept = self.setup_deployment_create_onaccept,
                  create_next = URL(c="setup", f="deployment",
                                    args = ["[id]", "instance"],
                                    ),
                  list_fields = ["production.url",
                                 "country",
                                 "template",
                                 "webserver_type",
                                 "db_type",
                                 ],
                  update_onaccept = self.setup_deployment_update_onaccept,
                  )

        add_components(tablename,
                       setup_instance = (# All instances:
                                         "deployment_id",
                                         # Production instance:
                                         {"name": "production",
                                          "joinby": "deployment_id",
                                          "filterby": {
                                              "type": 1,
                                              },
                                          "multiple": False,
                                          },
                                         ),
                       setup_monitor_task = "deployment_id",
                       setup_server = (# All instances:
                                       "deployment_id",
                                       # Production instance:
                                       {"name": "production_server",
                                        "joinby": "deployment_id",
                                        "filterby": {
                                            "role": 1,
                                            },
                                        "multiple": False,
                                        },
                                       ),
                       setup_setting = "deployment_id",
                       )

        set_method("setup", "deployment",
                   method = "wizard",
                   action = self.setup_server_wizard)

        represent = setup_DeploymentRepresent()

        deployment_id = S3ReusableField("deployment_id", "reference %s" % tablename,
                                        label = T("Deployment"),
                                        ondelete = "CASCADE",
                                        represent = represent,
                                        requires = IS_EMPTY_OR(
                                                    IS_ONE_OF(db, "setup_deployment.id",
                                                              represent,
                                                              sort=True
                                                              )),
                                        sortby = "name",
                                        )

        # ---------------------------------------------------------------------
        # Servers
        #
        SERVER_ROLES = {1: "all",
                        #2: "db",
                        #3: "webserver",
                        #4: "eden",
                        }

        tablename = "setup_server"
        define_table(tablename,
                     # @ToDo: Server Groups (e.g. 'all webservers', 'all debian 9')
                     #group_id(),
                     deployment_id(),
                     Field("name",
                           label = T("Name"),
                           # Can do this in templates if-required
                           #requires = IS_NOT_IN_DB(db, "setup_server.name"),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Name"),
                                                           # If not defined then can be automated by the Cloud integration, if-present
                                                           T("Optional.")
                                                           )
                                         ),
                           ),
                     Field("host_ip", length=24,
                           label = T("IP Address"),
                           # required for non-cloud deployments (set in controller)
                           requires = IS_EMPTY_OR(
                                        IS_IPV4(),
                                        ),
                           #writable = False,
                           comment = DIV(_class="tooltip",
                                         # If not defined then can be automated by the Cloud integration, if-present
                                         _title="%s|%s" % (T("IP Address"),
                                                           T("Leave blank if using a Cloud configuration or deploying to this Server (where it will default to 127.0.0.1). Set to the IP address of the remote server if you have an SSH private key.")
                                                           )
                                         ),
                           ),
                     Field("role", "integer",
                           default = 1,
                           label = T("Role"),
                           represent = S3Represent(options = SERVER_ROLES),
                           requires = IS_IN_SET(SERVER_ROLES),
                           writable = False,
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Role"),
                                                           T("Currently only 'all' is supported by this tool, although others should be possible with a little work.")
                                                           )
                                         ),
                           ),
                     Field("remote_user",
                           default = "admin",
                           label = T("Remote User"),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Remote User"),
                                                           T("If you wish to configure a server other than this one then you need to provide the username that the SSH private key works with. For Debian OS, this is normally 'admin'.")
                                                           )
                                         ),
                           ),
                     Field("private_key", "upload",
                           label = T("SSH Private Key"),
                           length = current.MAX_FILENAME_LENGTH,
                           requires = IS_EMPTY_OR(IS_UPLOAD_FILENAME()),
                           uploadfolder = uploadfolder,
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("SSH Private Key"),
                                                           T("If you wish to configure a server other than this one then either you need to use a Cloud or provide a PEM-encoded SSH private key")
                                                           )
                                         ),
                           ),
                     *s3_meta_fields()
                     )

        configure(tablename,
                  create_onaccept = self.setup_server_create_onaccept,
                  ondelete = self.setup_server_ondelete,
                  )

        crud_strings[tablename] = Storage(
            label_create = T("Add Server"),
            title_display = T("Server Details"),
            title_list =  T("Servers"),
            title_update = T("Edit Server"),
            label_list_button =  T("List Servers"),
            label_delete_button = T("Delete Server"),
            msg_record_created = T("Server added"),
            msg_record_modified = T("Server updated"),
            msg_record_deleted = T("Server deleted"),
            msg_list_empty = T("No Servers currently registered"))

        add_components(tablename,
                       setup_aws_server = {"joinby": "server_id",
                                           "multiple": False,
                                           },
                       setup_openstack_server = {"joinby": "server_id",
                                                 "multiple": False,
                                                 },
                       setup_monitor_run = {"name": "monitor_log",
                                            "joinby": "server_id",
                                            },
                       setup_monitor_server = {"joinby": "server_id",
                                               "multiple": False,
                                               },
                       setup_monitor_task = "server_id",
                       )

        # @ToDo: Add represented Deployment/Role
        represent = S3Represent(lookup = tablename,
                                fields = ["name", "host_ip"])

        server_id = S3ReusableField("server_id", "reference %s" % tablename,
                                    label = T("Server"),
                                    ondelete = "CASCADE",
                                    represent = represent,
                                    requires = IS_EMPTY_OR(
                                                IS_ONE_OF(db, "setup_server.id",
                                                          represent,
                                                          sort=True
                                                          )),
                                    sortby = "name",
                                    )

        set_method("setup", "server",
                   method = "enable",
                   action = setup_monitor_server_enable_interactive)

        set_method("setup", "server",
                   method = "disable",
                   action = setup_monitor_server_disable_interactive)

        set_method("setup", "server",
                   method = "check",
                   action = setup_monitor_server_check)

        # ---------------------------------------------------------------------
        # Instances
        #
        # @ToDo: Allow a Test instance to source Prod data from a different deployment
        #        - to allow it to be run on different hosts (or even different cloud)
        #
        type_represent = S3Represent(options = INSTANCE_TYPES)

        tablename = "setup_instance"
        define_table(tablename,
                     deployment_id(),
                     Field("type", "integer",
                           default = 1,
                           label = T("Type"),
                           represent = type_represent,
                           requires = IS_IN_SET(INSTANCE_TYPES),
                           ),
                     Field("url",
                           label = T("URL"),
                           requires = IS_URL(prepend_scheme = "https"),
                           represent = lambda opt: A(opt,
                                                     _href = opt,
                                                     _target="_blank",
                                                     ),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("URL"),
                                                           T("The Public URL which will be used to access the instance")
                                                           )
                                         ),
                           ),
                     # @ToDo: Allow upload of SSL as well as auto-generated Let's Encrypt
                     #Field("ssl_cert", "upload",
                     #      label = T("SSL Certificate"),
                     #      length = current.MAX_FILENAME_LENGTH,
                     #      requires = IS_EMPTY_OR(IS_UPLOAD_FILENAME()),
                     #      uploadfolder = uploadfolder,
                     #      comment = DIV(_class="tooltip",
                     #                    _title="%s|%s" % (T("SSL Certificate"),
                     #                                      T("If not using Let's Encrypt e.g. you wish to use an OV or EV certificate")
                     #                                      )
                     #                    ),
                     #      ),
                     #Field("ssl_key", "upload",
                     #      label = T("SSL Key"),
                     #      length = current.MAX_FILENAME_LENGTH,
                     #      requires = IS_EMPTY_OR(IS_UPLOAD_FILENAME()),
                     #      uploadfolder = uploadfolder,
                     #      comment = DIV(_class="tooltip",
                     #                    _title="%s|%s" % (T("SSL Key"),
                     #                                      T("If not using Let's Encrypt e.g. you wish to use an OV or EV certificate")
                     #                                      )
                     #                    ),
                     #      ),
                     Field("sender",
                           label = T("Email Sender"),
                           requires = IS_EMPTY_OR(
                                        IS_EMAIL()),
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Email Sender"),
                                                           T("The Address which you want Outbound Email to be From. Not setting this means that Outbound Email is Disabled unless you automate this with an Email Group Provider.")
                                                           )
                                         ),
                           ),
                     Field("start", "boolean",
                           default = True, # default = False in Controller for additional instances
                           label = T("Start at Boot"),
                           represent = s3_yes_no_represent,
                           ),
                     Field("task_id", "reference scheduler_task",
                           label = T("Scheduled Task"),
                           represent = lambda opt: \
                            A(opt,
                              _href = URL(c="appadmin", f="update",
                                          args = ["db", "scheduler_task", opt]),
                              ) if opt else current.messages["NONE"],
                           writable = False,
                           ),
                     Field("log_file", "upload",
                           label = T("Log File"),
                           length = current.MAX_FILENAME_LENGTH,
                           requires = IS_EMPTY_OR(IS_UPLOAD_FILENAME()),
                           uploadfolder = uploadfolder,
                           writable = False,
                           ),
                     # Has the Configuration Wizard been run?
                     Field("configured", "boolean",
                           default = False,
                           #represent = s3_yes_no_represent,
                           readable = False,
                           writable = False,
                           ),
                     *s3_meta_fields()
                     )

        crud_strings[tablename] = Storage(
            label_create = T("Add Instance"),
            title_display = T("Instance Details"),
            title_list =  T("Instances"),
            title_update = T("Edit Instance"),
            label_list_button =  T("List Instances"),
            label_delete_button = T("Delete Instance"),
            msg_record_created = T("Instance added"),
            msg_record_modified = T("Instance updated"),
            msg_record_deleted = T("Instance deleted"),
            msg_list_empty = T("No Instances currently registered"))

        add_components(tablename,
                       setup_google_instance = {"joinby": "instance_id",
                                                "multiple": False,
                                                },
                       setup_setting = "instance_id",
                       )

        configure(tablename,
                  list_fields = ["type",
                                 "url",
                                 "start",
                                 "task_id",
                                 "log_file",
                                 ],
                  ondelete = self.setup_instance_ondelete,
                  update_onaccept = self.setup_instance_update_onaccept,
                  )

        set_method("setup", "deployment",
                   component_name = "instance",
                   method = "deploy",
                   action = self.setup_instance_deploy,
                   )

        set_method("setup", "deployment",
                   component_name = "instance",
                   method = "settings",
                   action = self.setup_instance_settings,
                   )

        set_method("setup", "deployment",
                   component_name = "instance",
                   method = "start",
                   action = self.setup_instance_start,
                   )

        set_method("setup", "deployment",
                   component_name = "instance",
                   method = "stop",
                   action = self.setup_instance_stop,
                   )

        set_method("setup", "deployment",
                   component_name = "instance",
                   method = "clean",
                   action = self.setup_instance_clean,
                   )

        set_method("setup", "deployment",
                   component_name = "instance",
                   method = "wizard",
                   action = self.setup_instance_wizard,
                   )

        represent = S3Represent(lookup = tablename,
                                fields = ["type"],
                                labels = lambda row: type_represent(row.type))

        instance_id = S3ReusableField("instance_id", "reference %s" % tablename,
                                      label = T("Instance"),
                                      ondelete = "CASCADE",
                                      represent = represent,
                                      requires = IS_EMPTY_OR(
                                                    IS_ONE_OF(db, "setup_instance.id",
                                                              represent,
                                                              sort = True
                                                              )),
                                      sortby = "name",
                                      )

        # ---------------------------------------------------------------------
        # Settings in models/000_config.py
        #
        tablename = "setup_setting"
        define_table(tablename,
                     deployment_id(),
                     instance_id(),
                     Field("setting",
                           label = T("Setting"),
                           requires = IS_NOT_EMPTY(),
                           ),
                     Field("current_value",
                           label = T("Current Value"),
                           writable = False,
                           ),
                     Field("new_value",
                           label = T("New Value"),
                           ),
                     *s3_meta_fields()
                     )

        crud_strings[tablename] = Storage(
            label_create = T("Add Setting"),
            title_display = T("Setting Details"),
            title_list =  T("Settings"),
            title_update = T("Edit Setting"),
            label_list_button =  T("List Settings"),
            label_delete_button = T("Delete Setting"),
            msg_record_created = T("Setting added"),
            msg_record_modified = T("Setting updated"),
            msg_record_deleted = T("Setting deleted"),
            msg_list_empty = T("No Settings currently registered"))

        set_method("setup", "deployment",
                   component_name = "setting",
                   method = "apply",
                   action = self.setup_setting_apply_interactive,
                   )

        # ---------------------------------------------------------------------
        # Pass names back to global scope (s3.*)
        return {"setup_deployment_id": deployment_id,
                "setup_server_id": server_id,
                "setup_instance_id": instance_id,
                }

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_deployment_create_onaccept(form):
        """
            New Deployment:
            - Assign a random DB password
        """

        # Assign a random DB password
        chars = string.ascii_letters + string.digits + string.punctuation
        # Ensure that " isn't included otherwise we get a syntax error in 000_config.py
        chars = chars.replace('"', "")
        # Ensure that ' isn't included otherwise we get a syntax error in pgpass.sql
        chars = chars.replace("'", "")
        # Ensure that @ isn't included as Web2Py doesn't like this
        chars = chars.replace("@", "")
        # Ensure that \ isn't included as control characters can cause the settings.database.password to not match pgpass (e.g. \a -> ^G)
        chars = chars.replace("\\", "")
        password = "".join(random.choice(chars) for _ in range(12))

        current.db(current.s3db.setup_deployment.id == form.vars.id).update(db_password = password)

        current.session.information = current.T("Press 'Deploy' when you are ready")

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_deployment_update_onaccept(form):
        """
            Process changed fields on server:
            - smtp_id
        """

        db = current.db
        s3db = current.s3db

        form_vars_get = form.vars.get
        record = form.record
        deployment_id = form_vars_get("id")

        smtp_id = form_vars_get("smtp_id")
        if smtp_id == record.smtp_id:
            # Nothing more to do
            return

        # Adjust the Deployment's SMTP Smart Host

        playbook = []

        # Lookup Server Details
        svtable = s3db.setup_server
        query = (svtable.deployment_id == deployment_id) & \
                (svtable.role.belongs((1, 4)))
        server = db(query).select(svtable.name,
                                  svtable.host_ip,
                                  svtable.remote_user,
                                  svtable.private_key,
                                  limitby = (0, 1)
                                  ).first()
        host_ip = server.host_ip
        if host_ip == "127.0.0.1":
            connection = "local"
        else:
            provided_key = server.private_key
            if not provided_key:
                # Abort
                db.rollback()
                current.response.error = current.T("Update failed: SSH Key needed when applying away from localhost")
                return

            connection = "smart"
            tasks = []
            # Copy the Private Key to where it will be used
            provided_key = os.path.join(current.request.folder, "uploads", provided_key)
            private_key = "/tmp/%s.pem" % server.name
            tasks.append({"copy": {"src": provided_key,
                                   "dest": private_key,
                                   "mode": "0600",
                                   },
                          })
            # Add instance to host group (to associate private_key)
            tasks.append({"add_host": {"hostname": host_ip,
                                       "groupname": "launched",
                                       "ansible_ssh_private_key_file": private_key,
                                       },
                          })
            playbook.append({"hosts": "localhost",
                             "connection": "local",
                             "gather_facts": "no",
                             "tasks": tasks,
                             })
            host_ip = "launched"

        if smtp_id is None:
            # Reset to default configuration
            tasks = [{"file": {"path": "/etc/exim4/exim4.conf",
                               "state": "absent",
                               },
                      },
                     {"service": {"name": "exim4",
                                  "state": "restarted",
                                  },
                      "become": "yes",
                      },
                     ]
        else:
            # Apply Smart Host configuration
            # - like roles/exim/smart_host.yml
            itable = s3db.setup_instance
            query = (itable.deployment_id == record.id) & \
                    (itable.type == 1)
            instance = db(query).select(itable.url,
                                        limitby = (0, 1)
                                        ).first()
            url = instance.url
            if "://" in url:
                protocol, sitename = url.split("://", 1)
            else:
                sitename = url
            stable = s3db.setup_smtp
            smtp = db(stable.id == smtp_id).select(stable.hostname,
                                                   stable.username,
                                                   stable.password,
                                                   limitby = (0, 1)
                                                   ).first()
            tasks = [{"copy": {"src": "/usr/share/doc/exim4-base/examples/example.conf.gz",
                               "dest": "/etc/exim4/example.conf.gz",
                               "remote_src": "yes",
                               },
                      "become": "yes",
                      },
                     {"command": "gunzip /etc/exim4/example.conf.gz",
                      "args": {"chdir": "/etc/exim4",
                               },
                      "become": "yes",
                      },
                     {"copy": {"src": "/etc/exim4/example.conf",
                               "dest": "/etc/exim4/exim4.conf",
                               "remote_src": "yes",
                               },
                      "become": "yes",
                      },
                     {"lineinfile": {"path": "/etc/exim4/exim4.conf",
                                     "regexp": QuotedDouble("{{ item.regexp }}"),
                                     "line": QuotedDouble("{{ item.line }}"),
                                     "backrefs": "yes",
                                     },
                      "loop": [{"regexp": QuotedSingle("^# primary_hostname ="),
                                "line": QuotedSingle("primary_hostname = %s" % sitename),
                                },
                               {"regexp": QuotedSingle("^# keep_environment ="),
                                "line": QuotedSingle("keep_environment ="),
                                },
                               {"regexp": QuotedSingle("^# tls_advertise_hosts = *"),
                                "line": QuotedSingle("tls_advertise_hosts ="),
                                },
                               ],
                      "become": "yes",
                      },
                     {"blockinfile": {"path": "/etc/exim4/exim4.conf",
                                      "insertafter": QuotedSingle("begin routers"),
                                      "marker": QuotedDouble("# {mark} ANSIBLE MANAGED BLOCK Router"),
                                      "block": Literal("""send_via_smart_host:
  driver = manualroute
  domains = ! +local_domains
  transport = smart_host_smtp
  route_list = * %s;""" % smtp.hostname),
                                      },
                      "become": "yes",
                      },
                     {"blockinfile": {"path": "/etc/exim4/exim4.conf",
                                      "insertafter": QuotedSingle("begin transports"),
                                      "marker": QuotedDouble("# {mark} ANSIBLE MANAGED BLOCK Transport"),
                                      "block": Literal("""smart_host_smtp:
  driver = smtp
  port = 587
  hosts_require_auth = *
  hosts_require_tls = *"""),
                                      },
                      "become": "yes",
                      },
                     {"blockinfile": {"path": "/etc/exim4/exim4.conf",
                                      "insertafter": QuotedSingle("begin authenticators"),
                                      "marker": QuotedDouble("# {mark} ANSIBLE MANAGED BLOCK Authenticator"),
                                      "block": Literal("""smarthost_login:
  driver = plaintext
  public_name = LOGIN
  client_send = : %s : %s""" % (smtp.username, smtp.password)),
                                      },
                      "become": "yes",
                      },
                     {"service": {"name": "exim4",
                                  "state": "restarted",
                                  },
                      "become": "yes",
                      },
                     ]

        # Build Playbook data structure:
        playbook.append({"hosts": host_ip,
                         "connection": connection,
                         "remote_user": server.remote_user,
                         "become_method": "sudo",
                         #"become_user": "root",
                         "tasks": tasks,
                         })

        # Write Playbook
        name = "smtp_%d" % int(time.time())
        task_vars = setup_write_playbook("%s.yml" % name,
                                         playbook,
                                         )

        # Run the Playbook
        #task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
        current.s3task.schedule_task(name,
                                     vars = task_vars,
                                     function_name = "setup_run_playbook",
                                     repeats = None,
                                     timeout = 6000,
                                     #sync_output = 300
                                     )

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_get_templates():
        """
            Return a Dict of Templates for the user to select from

            NB Controller reads this from remote repo...this is a fallback in case offline
        """

        file_path = os.path.join(current.request.folder, "modules", "templates", "templates.json")
        with open(file_path, "r") as file:
            templates = json.loads(file.read())

        return templates

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_server_create_onaccept(form):
        """
            New Server:
            - Enable Monitoring
        """

        server_id = form.vars.id
        table = current.s3db.setup_monitor_server

        exists = current.db(table.server_id == server_id).select(table.id,
                                                                 limitby = (0, 1)
                                                                 ).first()
        if exists is None:
            table.insert(server_id = server_id)

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_server_ondelete(row):
        """
            Cleanup Tasks when a Server is Deleted
            - ~/.ssh/known_hosts
        """

        table = current.s3db.setup_server
        server = current.db(table.id == row.id).select(table.host_ip,
                                                       limitby = (0, 1)
                                                       ).first()
        if server.host_ip != "127.0.0.1":
            # Cleanup known_hosts as it will change for a new deployment
            import subprocess
            command = ["ssh-keygen",
                       "-f",
                       "~/.ssh/known_hosts",
                       "-R",
                       server.host_ip,
                       ]
            result = subprocess.run(command, stdout=subprocess.PIPE)

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_server_wizard(r, **attr):
        """
            Custom S3Method to select an Instance to Configure
        """

        db = current.db
        deployment_id = r.id
        itable = db.setup_instance

        instances = db(itable.deployment_id == deployment_id).select(itable.id,
                                                                     itable.type,
                                                                     )

        if len(instances) == 1:
            # Redirect to the Instance Wizard
            redirect(URL(c="setup", f="deployment",
                         args = [deployment_id, "instance", instances.first().id, "wizard"],
                         ))

        # Provide a Dropdown of Instances for the user to select
        dropdown = SELECT(OPTION(_value=""),
                          _id = "instances",
                          )
        for instance in instances:
            dropdown.append(OPTION(INSTANCE_TYPES[instance.type],
                                   _value="%s" % instance.id))

        script = '''
var dropdown = $('#instances');
dropdown.change(function() {
 var url = S3.Ap.concat('/setup/deployment/%s/instance/' + this.value + '/wizard');
 $(location).prop('href', url);
})''' % deployment_id
        response = current.response
        response.s3.jquery_ready.append(script)
        response.view = "simple.html"
        output = {"item": DIV(P(current.T("Select the instance you wish to configure")),
                              dropdown),
                  }
        return output

    # -------------------------------------------------------------------------
    def setup_instance_wizard(self, r, **attr):
        """
            Custom S3Method to Configure an Instance

            @ToDo: Support remote servers/instances
            @ToDo: Option to Propagate settings from Prod to Demo &/or Test
                   - on by default
        """

        from gluon import DIV, IS_IN_SET, SQLFORM
        from gluon.sqlhtml import RadioWidget
        from s3 import s3_mark_required
        from s3dal import Field

        T = current.T
        response = current.response
        settings = current.deployment_settings
        has_module = settings.has_module

        all_pages = settings.get_setup_wizard_questions()

        # Filter out inactive pages (for disabled modules)
        # - this only works for Local Server
        active_pages = []
        aappend = active_pages.append
        for page in all_pages:
            module = page.get("module")
            if not module or has_module(module):
                aappend(page)
        
        current_page = int(r.get_vars.get("page", 1))
        last_page = len(active_pages)

        base_url = URL(c="setup", f="deployment",
                       args = r.args,
                       )
        i = 0
        tabs = DIV(_class = "tabs")
        tappend = tabs.append
        for page in active_pages:
            i += 1
            if i == current_page:
                _class = "tab_here"
            elif i == last_page:
                _class = "tab_last"
            else:
                _class = "tab_other"
            tappend(SPAN(A(T(page.get("title")),
                           _href = "%s?page=%s" % (base_url, i)
                           ),
                         _class = _class,
                         ))

        page = active_pages[current_page - 1] # 0-indexed
        questions = page.get("questions", [])

        fields = []
        fappend = fields.append
        if len(questions):
            QUESTIONS = True
            for q in questions:
                try:
                    fn = getattr(settings, q["fn"])
                except:
                    default = None
                else:
                    try:
                        default = fn() # This is only the case for Local Server
                    except:
                        default = None
                setting = q["setting"]
                fname = setting.replace(".", "_")
                fappend(Field(fname,
                              default = default,
                              label = T(q["question"]),
                              requires = IS_IN_SET(q["options"]),
                              widget = RadioWidget.widget,
                              #widget = lambda f, v: RadioWidget.widget(f, v, style="divs"),
                              _id = "setting",
                              ))
        else:
            QUESTIONS = False
            modules = page.get("modules", [])
            TRUE_FALSE = (True, False)
            for m in modules:
                module = m["module"]
                default = has_module(module) # This is only the case for Local Server
                label = T(m["label"])
                fappend(Field(module,
                              default = default,
                              label = label,
                              requires = IS_IN_SET(TRUE_FALSE),
                              widget = RadioWidget.widget,
                              comment = DIV(_class="tooltip",
                                            _title="%s|%s" % (label,
                                                              T(m["description"]),
                                                              ),
                                            ),
                              _id = "module",
                              ))

        labels, required = s3_mark_required(fields)
        response.s3.has_required = required
        response.form_label_separator = ""

        form = SQLFORM.factory(#formstyle = settings.get_ui_formstyle(),
                               submit_button = T("Submit"),
                               labels = labels,
                               separator = "",
                               table_name = "options", # Dummy table name
                               _id = "options",
                               *fields
                               )

        if form.accepts(r.post_vars, current.session):
            # Processs Form
            if QUESTIONS:
                result = setup_settings_apply(r.id, form.vars)
            else:
                # NB This won't display suitable tabs immediately as the enabling/disabling is async
                result = setup_modules_apply(r.id, form.vars)
            if result:
                response.error = result
            else:
                response.confirmation = T("Settings Applied")

        current.response.view = "setup/wizard.html"
        output = {"item": form,
                  "tabs": tabs,
                  "title": T("Configuration Wizard"),
                  }
        return output

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_instance_deploy(r, **attr):
        """
            Custom S3Method to Deploy an Instance
        """

        instance_id = r.component_id
        deployment_id = r.id

        setup_instance_deploy(deployment_id, instance_id, r.folder)

        current.session.confirmation = current.T("Deployment initiated")
        redirect(URL(c="setup", f="deployment",
                     args = [deployment_id, "instance"],
                     ))

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_instance_settings(r, **attr):
        """
            Custom interactive S3Method to Read the Settings for an instance
            from models/000_config.py
        """

        deployment_id = r.id

        setup_instance_settings_read(r.component_id, deployment_id)

        current.session.confirmation = current.T("Settings Read")

        redirect(URL(c="setup", f="deployment",
                     args = [deployment_id, "setting"]),
                     )

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_instance_start(r, **attr):
        """
            Custom interactive S3Method to Start an Instance
        """

        setup_instance_method(r.component_id)

        current.session.confirmation = current.T("Instance Started")

        redirect(URL(c="setup", f="deployment",
                     args = [r.id, "instance"]),
                     )

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_instance_stop(r, **attr):
        """
            Custom interactive S3Method to Stop an Instance
        """

        setup_instance_method(r.component_id, "stop")

        current.session.confirmation = current.T("Instance Stopped")

        redirect(URL(c="setup", f="deployment",
                     args = [r.id, "instance"]),
                     )

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_instance_clean(r, **attr):
        """
            Custom interactive S3Method to Clean an Instance
        """

        setup_instance_method(r.component_id, "clean")

        current.session.confirmation = current.T("Instance Clean Started")

        redirect(URL(c="setup", f="deployment",
                     args = [r.id, "instance"]),
                     )

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_instance_ondelete(row):
        """
            Cleanup Tasks when an Instance is Deleted
            - DNS
        """

        db = current.db
        s3db = current.s3db

        dtable = s3db.setup_deployment
        deployment = db(dtable.id == row.deployment_id).select(dtable.dns_id,
                                                               limitby = (0, 1)
                                                               ).first()

        dns_id = deployment.dns_id

        if dns_id is None:
            # Nothing to cleanup
            return

        # Lookup the Instance Type
        dtable = s3db.setup_dns
        dns = db(dtable.dns_id == dns_id).select(dtable.instance_type,
                                                 limitby = (0, 1)
                                                 ).first()
        dns_type = dns.instance_type
        if dns_type == "setup_godaddy_dns":
            # No way currently to cleanup without replacing entire domain, omitting this record
            return
        #elif dns_type == "setup_gandi_dns":

        # Read URL (only deleted_fks are in the row object)
        itable = s3db.setup_instance
        instance = db(itable.id == row.id).select(itable.url,
                                                  limitby = (0, 1)
                                                  ).first()

        # Get Gandi details
        gtable = s3db.setup_gandi_dns
        gandi = db(gtable.dns_id == dns_id).select(gtable.api_key,
                                                   gtable.domain,
                                                   gtable.zone,
                                                   limitby = (0, 1)
                                                   ).first()
        gandi_api_key = gandi.api_key
        domain = gandi.domain
        url = "https://dns.api.gandi.net/api/v5/zones/%s/records" % gandi.zone

        # Delete DNS record
        parts = instance.url.split("://")
        if len(parts) == 1:
            sitename = parts[0]
        else:
            sitename = parts[1]
        dns_record = sitename.split(".%s" % domain, 1)[0]

        playbook = [{"hosts": "localhost",
                     "connection": "local",
                     "gather_facts": "no",
                     "tasks": [{"uri": {"url": "%s/%s" % (url, dns_record),
                                        "method": "DELETE",
                                        "headers": {"X-Api-Key": gandi_api_key,
                                                    },
                                        },
                                # Don't worry if it didn't exist
                                "ignore_errors": "yes",
                                },
                               ],
                     },
                    ]

        # Write Playbook
        name = "instance_ondelete_%d" % int(time.time())
        task_vars = setup_write_playbook("%s.yml" % name,
                                         playbook,
                                         )

        # Run Playbook
        #task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
        current.s3task.schedule_task(name,
                                     vars = task_vars,
                                     function_name = "setup_run_playbook",
                                     repeats = None,
                                     timeout = 6000,
                                     #sync_output = 300
                                     )

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_instance_update_onaccept(form):
        """
            Process changed fields on server:
            - sender
            - start
        """

        db = current.db
        s3db = current.s3db

        form_vars_get = form.vars.get
        record = form.record
        deployment_id = record.deployment_id
        instance_id = form_vars_get("id")

        sender = form_vars_get("sender")
        if sender != record.sender:
            # Adjust the Instance's Email Sender
            stable = s3db.setup_setting
            query = (stable.instance_id == instance_id) & \
                    (stable.setting == "mail.sender")
            setting = db(query).select(stable.id,
                                       limitby = (0, 1)
                                       ).first()
            if setting:
                setting_id = setting.id
                setting.update_record(new_value = sender)
            else:
                setting_id = stable.insert(deployment_id = deployment_id,
                                           instance_id = instance_id,
                                           setting = "mail.sender",
                                           new_value = sender,
                                           )
            setup_setting_apply(setting_id)

        if form_vars_get("start") is True:
            if record.start is False:
                # Start Instance at Boot
                command = "enable"
            else:
                # Nothing more to do
                return
        elif record.start is True:
            # Stop Instance at Boot
            command = "disable"
        else:
            # Nothing more to do
            return

        playbook = []

        # Lookup Server Details
        svtable = s3db.setup_server
        query = (svtable.deployment_id == deployment_id) & \
                (svtable.role.belongs((1, 4)))
        server = db(query).select(svtable.name,
                                  svtable.host_ip,
                                  svtable.remote_user,
                                  svtable.private_key,
                                  limitby = (0, 1)
                                  ).first()
        host_ip = server.host_ip
        if host_ip == "127.0.0.1":
            connection = "local"
        else:
            provided_key = server.private_key
            if not provided_key:
                # Abort
                db.rollback()
                current.response.error = current.T("Update failed: SSH Key needed when applying away from localhost")
                return

            connection = "smart"
            tasks = []
            # Copy the Private Key to where it will be used
            provided_key = os.path.join(current.request.folder, "uploads", provided_key)
            private_key = "/tmp/%s.pem" % server.name
            tasks.append({"copy": {"src": provided_key,
                                   "dest": private_key,
                                   "mode": "0600",
                                   },
                          })
            # Add instance to host group (to associate private_key)
            tasks.append({"add_host": {"hostname": host_ip,
                                       "groupname": "launched",
                                       "ansible_ssh_private_key_file": private_key,
                                       },
                          })
            playbook.append({"hosts": "localhost",
                             "connection": "local",
                             "gather_facts": "no",
                             "tasks": tasks,
                             })
            host_ip = "launched"

        appname = "eden" # @ToDo: Allow this to be configurable

        itable = s3db.setup_instance
        instance = db(itable.id == instance_id).select(itable.type,
                                                       limitby = (0, 1)
                                                       ).first()
        instance_type = INSTANCE_TYPES[instance.type]

        # @ToDo: Lookup webserver_type from deployment once we support Apache

        # Build Playbook data structure:
        playbook.append({"hosts": host_ip,
                         "connection": connection,
                         "remote_user": server.remote_user,
                         "become_method": "sudo",
                         #"become_user": "root",
                         "tasks": [{"name": "Modify Startup",
                                    "command": "update-rc.d uwsgi-%s {{item}}" % instance_type,
                                    "become": "yes",
                                    "loop": ["%s 2" % command,
                                             "%s 3" % command,
                                             "%s 4" % command,
                                             "%s 5" % command,
                                             ],
                                    },
                                   ],
                         })

        # Write Playbook
        name = "boot_%d" % int(time.time())
        task_vars = setup_write_playbook("%s.yml" % name,
                                         playbook,
                                         )

        # Run the Playbook
        task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
        current.s3task.schedule_task(name,
                                     vars = task_vars,
                                     function_name = "setup_run_playbook",
                                     repeats = None,
                                     timeout = 6000,
                                     #sync_output = 300
                                     )

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_setting_apply_interactive(r, **attr):
        """
            Custom interactive S3Method to Apply a Setting to an instance
            via models/000_config.py
        """

        result = setup_setting_apply(r.component_id)

        if result:
            current.session.error = result
        else:
            current.session.confirmation = current.T("Setting Applied")

        redirect(URL(c="setup", f="deployment",
                     args = [r.id, "setting"]),
                     )

# =============================================================================
class S3SetupMonitorModel(S3Model):

    names = ("setup_monitor_server",
             "setup_monitor_check",
             "setup_monitor_task",
             "setup_monitor_run",
             "setup_monitor_alert",
             )

    def model(self):

        T = current.T
        db = current.db

        add_components = self.add_components
        configure = self.configure
        crud_strings = current.response.s3.crud_strings
        define_table = self.define_table
        set_method = self.set_method
        server_id = self.setup_server_id

        UNKNOWN_OPT = current.messages.UNKNOWN_OPT

        STATUS_OPTS = {0 : T("Unknown"),
                       1 : T("OK"),
                       2 : T("Warning"),
                       3 : T("Critical"),
                       }

        status_id = S3ReusableField("status", "integer", notnull=True,
                                    default = 0,
                                    label = T("Status"),
                                    represent = lambda opt: \
                                                    STATUS_OPTS.get(opt,
                                                                    UNKNOWN_OPT),
                                    requires = IS_IN_SET(STATUS_OPTS,
                                                         zero=None),
                                    writable = False,
                                    )

        # =====================================================================
        # Servers
        # - extensions for Monitoring:
        #       Are checks Enabled?
        #       Overall Server Status
        #
        tablename = "setup_monitor_server"
        define_table(tablename,
                     #Field("name", unique=True, length=255,
                     #      label = T("Name"),
                     #      ),
                     server_id(),
                     Field("enabled", "boolean",
                           default = True,
                           label = T("Enabled?"),
                           represent = s3_yes_no_represent,
                           ),
                     status_id(),
                     s3_comments(),
                     *s3_meta_fields())

        configure(tablename,
                  onaccept = self.setup_monitor_server_onaccept,
                  )

        # =====================================================================
        # Checks
        # - monitoring scripts available
        #
        tablename = "setup_monitor_check"
        define_table(tablename,
                     Field("name", unique=True, length=255,
                           label = T("Name"),
                           ),
                     # Name of a function in modules.<settings.get_setup_monitor_template()>.monitor[.py]
                     # List populated in controllers/setup/monitor_check()
                     Field("function_name",
                           label = T("Function"),
                           comment = T("Functions defined in <template>.monitor.py")
                           ),
                     Field("period", "integer",
                           default = 300,
                           label = T("Period"),
                           requires = IS_INT_IN_RANGE(60, 31536000), # Max 1 Year
                           represent = IS_INT_AMOUNT.represent,
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Period"),
                                                           T("How many seconds between runs.")
                                                           )
                                         ),
                           ),
                     # Default Options for this Check
                     Field("options", "json",
                           label = T("Options"),
                           requires = IS_EMPTY_OR(
                                        IS_JSONS3()
                                        ),
                           ),
                     s3_comments(),
                     *s3_meta_fields())

        crud_strings[tablename] = Storage(
                label_create = T("Create Check"),
                title_display = T("Check Details"),
                title_list =  T("Checks"),
                title_update = T("Edit Check"),
                title_upload = T("Import Checks"),
                label_list_button =  T("List Checks"),
                label_delete_button = T("Delete Check"),
                msg_record_created = T("Check added"),
                msg_record_modified = T("Check updated"),
                msg_record_deleted = T("Check deleted"),
                msg_list_empty = T("No Checks currently registered"))

        represent = S3Represent(lookup = tablename)
        check_id = S3ReusableField("check_id", "reference %s" % tablename,
                                   label = T("Check"),
                                   ondelete = "CASCADE",
                                   represent = represent,
                                   requires = IS_ONE_OF(db, "setup_monitor_check.id",
                                                        represent),
                                   )

        add_components(tablename,
                       setup_monitor_task = "check_id",
                       )

        # =====================================================================
        # Tasks
        #
        tablename = "setup_monitor_task"
        define_table(tablename,
                     self.setup_deployment_id(readable = False,
                                              writable = False,
                                              ),
                     server_id(),
                     check_id(),
                     Field("enabled", "boolean",
                           default = True,
                           label = T("Enabled?"),
                           represent = s3_yes_no_represent,
                           ),
                     Field("period", "integer",
                           default = 300,
                           label = T("Period"),
                           requires = IS_INT_IN_RANGE(60, 31536000), # Max 1 Year
                           represent = IS_INT_AMOUNT.represent,
                           comment = DIV(_class="tooltip",
                                         _title="%s|%s" % (T("Period"),
                                                           T("How many seconds between runs.")
                                                           )
                                         ),
                           ),
                     # Options for this Check on this Server
                     # - including any thresholds for non-Critical results
                     Field("options", "json",
                           label = T("Options"),
                           requires = IS_EMPTY_OR(
                                        IS_JSONS3()
                                        ),
                           ),
                     status_id(),
                     Field("result", "text",
                           label = T("Result"),
                           represent = lambda v: v.split("\n")[0] if v else \
                                                 current.messages["NONE"],
                           ),
                     s3_datetime(label = T("Last Checked"),
                                 writable = False,
                                 ),
                     s3_comments(),
                     *s3_meta_fields())

        crud_strings[tablename] = Storage(
            label_create = T("Create Task"),
            title_display = T("Task Details"),
            title_list =  T("Tasks"),
            title_update = T("Edit Task"),
            title_upload = T("Import Tasks"),
            label_list_button =  T("List Tasks"),
            label_delete_button = T("Delete Task"),
            msg_record_created = T("Task added"),
            msg_record_modified = T("Task updated"),
            msg_record_deleted = T("Task deleted"),
            msg_list_empty = T("No Tasks currently registered"))

        crud_form = S3SQLCustomForm("server_id",
                                    "check_id",
                                    "enabled",
                                    "period",
                                    "options",
                                    S3SQLInlineComponent("monitor_alert",
                                                         label = T("Alerts"),
                                                         fields = [("", "person_id"),
                                                                   ],
                                                         ),
                                    "status",
                                    "result",
                                    "comments",
                                    )

        configure(tablename,
                  # Open the Log after creation
                  create_next = URL(c="setup", f="monitor_task",
                                    args = ["[id]", "monitor_run"],
                                    ),
                  crud_form = crud_form,
                  list_fields = ["deployment_id",
                                 "server_id",
                                 "check_id",
                                 "status",
                                 "result",
                                 "date",
                                 ],
                  onaccept = self.setup_monitor_task_onaccept,
                  )

        represent = setup_MonitorTaskRepresent()
        task_id = S3ReusableField("task_id", "reference %s" % tablename,
                                  label = T("Task"),
                                  ondelete = "CASCADE",
                                  represent = represent,
                                  requires = IS_EMPTY_OR(
                                                IS_ONE_OF(db, "setup_monitor_task.id",
                                                          represent)),
                                  )

        add_components(tablename,
                       setup_monitor_alert = "task_id",
                       setup_monitor_run = "task_id",
                       )

        set_method("setup", "monitor_task",
                   method = "enable",
                   action = setup_monitor_task_enable_interactive)

        set_method("setup", "monitor_task",
                   method = "disable",
                   action = setup_monitor_task_disable_interactive)

        set_method("setup", "monitor_task",
                   method = "check",
                   action = setup_monitor_task_run)

        # =====================================================================
        # Runs
        #
        tablename = "setup_monitor_run"
        define_table(tablename,
                     server_id(writable = False),
                     task_id(writable = False),
                     status_id(),
                     Field("result", "text",
                           label = T("Result"),
                           represent = lambda v: v.split("\n")[0] if v else \
                                                 current.messages["NONE"],
                           ),
                     s3_comments(),
                     *s3_meta_fields()#,
                     #on_define = lambda table: \
                     #   [table.created_on.set_attributes(represent = \
                     #       lambda dt: S3DateTime.datetime_represent(dt, utc=True)),
                     #   ]
                     )

        crud_strings[tablename] = Storage(
            #label_create = T("Create Log Entry"),
            title_display = T("Log Entry Details"),
            title_list =  T("Log Entries"),
            title_update = T("Edit Log Entry"),
            #title_upload = T("Import Log Entries"),
            label_list_button =  T("List Log Entries"),
            label_delete_button = T("Delete Log Entry"),
            #msg_record_created = T("Log Entry added"),
            msg_record_modified = T("Log Entry updated"),
            msg_record_deleted = T("Log Entry deleted"),
            msg_list_empty = T("No Log Entries currently registered"))

        configure(tablename,
                  # Logs inserted automatically
                  insertable = False,
                  list_fields = ["created_on",
                                 "server_id",
                                 "task_id",
                                 "status",
                                 "result",
                                 ],
                  orderby = "setup_monitor_run.created_on desc",
                  )

        # =============================================================================
        # Alerts
        #  - people to alert when status != OK
        #

        tablename = "setup_monitor_alert"
        define_table(tablename,
                     task_id(),
                     self.pr_person_id(comment = None,
                                       empty = False,
                                       ondelete = "CASCADE",
                                       widget = None, # Dropdown, not Autocomplete
                                       ),
                     # Email-only for now
                     #self.pr_contact_id(),
                     s3_comments(),
                     *s3_meta_fields())

        # ---------------------------------------------------------------------
        # Pass names back to global scope (s3.*)
        #
        return {}

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_monitor_server_onaccept(form):
        """
            Process the Enabled Flag
        """

        form_vars = form.vars
        if form.record:
            # Update form
            # process of changed
            if form.record.enabled and not form_vars.enabled:
                setup_monitor_server_disable(form_vars.id)
            elif form_vars.enabled and not form.record.enabled:
                setup_monitor_server_enable(form_vars.id)
        else:
            # Create form
            # Process only if enabled
            if form_vars.enabled:
                setup_monitor_server_enable(form_vars.id)

    # -------------------------------------------------------------------------
    @staticmethod
    def setup_monitor_task_onaccept(form):
        """
            Process the Enabled Flag
            Create Form:
                Set deployment_id
                PrePopulate Task Options/Period from Check Options/Period
        """

        form_vars = form.vars
        if form.record:
            # Update form
            # Process if changed
            if form.record.enabled and not form_vars.enabled:
                setup_monitor_task_disable(form_vars.id)
            elif form_vars.enabled and not form.record.enabled:
                setup_monitor_task_enable(form_vars.id)
        else:
            # Create form
            db = current.db
            record_id = form_vars.id
            if form_vars.enabled:
                # Process only if enabled
                setup_monitor_task_enable(record_id)

            # Read default check options
            ctable = db.setup_monitor_check
            check = db(ctable.id == form_vars.check_id).select(ctable.options,
                                                               ctable.period,
                                                               limitby = (0, 1)
                                                               ).first()

            # Read deployment_id
            ttable = db.setup_monitor_task
            server_id = form_vars.server_id
            if server_id:
                task = None
            else:
                # Read record
                task = db(ttable.id == record_id).select(ttable.id,
                                                         ttable.server_id,
                                                         limitby = (0, 1)
                                                         ).first()
                server_id = task.server_id
            stable = db.setup_server
            server = db(stable.id == server_id).select(stable.deployment_id,
                                                       limitby = (0, 1)
                                                       ).first()
            deployment_id = server.deployment_id

            # Update record
            if task:
                task.update_record(deployment_id = deployment_id,
                                   options = check.options,
                                   period = check.period,
                                   )
            else:
                db(ttable.id == record_id).update(deployment_id = deployment_id,
                                                  options = check.options,
                                                  period = check.period,
                                                  )

# =============================================================================
def setup_monitor_server_enable(monitor_server_id):
    """
        Enable Monitoring for a Server
        - Schedule all enabled Tasks

        CLI API for shell scripts & to be called by S3Method
    """

    db = current.db

    mstable = current.s3db.setup_monitor_server
    record = db(mstable.id == monitor_server_id).select(mstable.id,
                                                        mstable.enabled,
                                                        mstable.server_id,
                                                        limitby = (0, 1)
                                                        ).first()

    if not record.enabled:
        # Flag it as enabled
        record.update_record(enabled = True)

    table = db.setup_monitor_task
    query = (table.server_id == record.server_id) & \
            (table.enabled == True) & \
            (table.deleted == False)
    tasks = db(query).select(table.id,
                             table.period,
                             )

    # Do we have any Tasks already Scheduled?
    args = []
    for task in tasks:
        args.append("[%s]" % task.id)
    ttable = db.scheduler_task
    query = ((ttable.function_name == "setup_monitor_run_task") & \
             (ttable.args.belongs(args)) & \
             (ttable.status.belongs(["RUNNING",
                                     "QUEUED",
                                     "ALLOCATED"])))
    exists = db(query).select(ttable.id)
    exists = [r.id for r in exists]
    for task in tasks:
        task_id = task.id
        if task_id not in exists:
            current.s3task.schedule_task("setup_monitor_run_task",
                                         args = [task_id],
                                         period = task.period,# seconds
                                         timeout = 60,        # seconds
                                         repeats = 0,         # unlimited
                                         retry_failed = -1,   # unlimited
                                         )
    return "Server Monitoring enabled"

# =============================================================================
def setup_monitor_server_enable_interactive(r, **attr):
    """
        Enable Monitoring for a Server
        - Schedule all enabled Tasks

        S3Method for interactive requests
    """

    server_id = r.id

    table = current.s3db.setup_monitor_server
    monitor_server = current.db(table.server_id == server_id).select(table.id,
                                                                     limitby = (0, 1)
                                                                     ).first()
    if monitor_server:
        monitor_server_id = monitor_server.id
    else:
        monitor_server_id = table.insert(server_id = server_id)
    result = setup_monitor_server_enable(monitor_server_id)
    current.session.confirmation = result
    redirect(URL(f = "server"))

# =============================================================================
def setup_monitor_server_disable(monitor_server_id):
    """
        Disable Monitoring for a Server
        - Remove all related Tasks

        CLI API for shell scripts & to be called by S3Method
    """

    db = current.db

    mstable = current.s3db.setup_monitor_server
    record = db(mstable.id == monitor_server_id).select(mstable.id,
                                                        mstable.enabled,
                                                        mstable.server_id,
                                                        limitby = (0, 1)
                                                        ).first()

    if record.enabled:
        # Flag it as disabled
        record.update_record(enabled = False)

    table = db.setup_monitor_task
    query = (table.server_id == record.server_id) & \
            (table.enabled == True) & \
            (table.deleted == False)
    tasks = db(query).select(table.id)

    # Do we have any Tasks already Scheduled?
    args = []
    for task in tasks:
        args.append("[%s]" % task.id)
    ttable = db.scheduler_task
    query = ((ttable.function_name == "setup_monitor_run_task") & \
             (ttable.args.belongs(args)) & \
             (ttable.status.belongs(["RUNNING",
                                     "QUEUED",
                                     "ALLOCATED"])))
    exists = db(query).select(ttable.id,
                              limitby = (0, 1)
                              ).first()
    if exists:
        # Disable all
        db(query).update(status = "STOPPED")

    return "Server Monitoring disabled"

# =============================================================================
def setup_monitor_server_disable_interactive(r, **attr):
    """
        Disable Monitoring for a Server
        - Remove all related Tasks

        S3Method for interactive requests
    """

    table = current.s3db.setup_monitor_server
    monitor_server = current.db(table.server_id == r.id).select(table.id,
                                                                limitby = (0, 1)
                                                                ).first()

    result = setup_monitor_server_disable(monitor_server.id)
    current.session.confirmation = result
    redirect(URL(f = "server"))

# =============================================================================
def setup_monitor_server_check(r, **attr):
    """
        Run all enabled Tasks for this server

        S3Method for interactive requests
    """

    server_id = r.id
    table = current.s3db.setup_monitor_task
    query = (table.server_id == server_id) & \
            (table.enabled == True) & \
            (table.deleted == False)
    tasks = current.db(query).select(table.id)
    run_async = current.s3task.run_async
    for task in tasks:
        run_async("setup_monitor_run_task",
                  args = [task.id])
    current.session.confirmation = \
        current.T("The check requests have been submitted, so results should appear shortly - refresh to see them")

    redirect(URL(c="setup", f="server",
                 args = [server_id, "monitor_log"],
                 ))

# =============================================================================
def setup_monitor_task_enable(task_id):
    """
        Enable a Task
        - Schedule Check (if server enabled)

        CLI API for shell scripts & to be called by S3Method
    """

    db = current.db
    s3db = current.s3db

    table = s3db.setup_monitor_task
    record = db(table.id == task_id).select(table.id,
                                            table.server_id,
                                            table.enabled,
                                            table.period,
                                            limitby = (0, 1),
                                            ).first()

    if not record.enabled:
        # Flag it as enabled
        record.update_record(enabled = True)

    mstable = s3db.setup_monitor_server
    monitor_server = db(mstable.server_id == record.server_id).select(mstable.enabled,
                                                                      limitby = (0, 1),
                                                                      ).first()

    if monitor_server.enabled:
        # Is the task already Scheduled?
        ttable = db.scheduler_task
        args = "[%s]" % task_id
        query = ((ttable.function_name == "setup_monitor_run_task") & \
                 (ttable.args == args) & \
                 (ttable.status.belongs(["RUNNING",
                                         "QUEUED",
                                         "ALLOCATED"])))
        exists = db(query).select(ttable.id,
                                  limitby = (0, 1)
                                  ).first()
        if not exists:
            current.s3task.schedule_task("setup_monitor_run_task",
                                         args = [task_id],
                                         period = record.period,# seconds
                                         timeout = 60,          # seconds
                                         repeats = 0,           # unlimited
                                         retry_failed = -1,     # unlimited
                                         )

    return "Task enabled"

# =============================================================================
def setup_monitor_task_enable_interactive(r, **attr):
    """
        Enable a Task
        - Schedule Check

        S3Method for interactive requests
    """

    result = setup_monitor_task_enable(r.id)
    current.session.confirmation = result
    redirect(URL(f = "monitor_task"))

# =============================================================================
def setup_monitor_task_disable(task_id):
    """
        Disable a Check
        - Remove Schedule for Check

        CLI API for shell scripts & to be called by S3Method
    """

    db = current.db

    table = current.s3db.setup_monitor_task
    record = db(table.id == task_id).select(table.id, # needed for update_record
                                            table.enabled,
                                            limitby = (0, 1),
                                            ).first()

    if record.enabled:
        # Flag it as disabled
        record.update_record(enabled = False)

    # Is the task already Scheduled?
    ttable = db.scheduler_task
    args = "[%s]" % task_id
    query = ((ttable.function_name == "setup_monitor_run_task") & \
             (ttable.args == args) & \
             (ttable.status.belongs(["RUNNING",
                                     "QUEUED",
                                     "ALLOCATED"])))
    exists = db(query).select(ttable.id,
                              limitby = (0, 1)
                              ).first()
    if exists:
        # Disable all
        db(query).update(status = "STOPPED")

    return "Task disabled"

# =============================================================================
def setup_monitor_task_disable_interactive(r, **attr):
    """
        Disable a Task
        - Remove Schedule for Check

        S3Method for interactive requests
    """

    result = setup_monitor_task_disable(r.id)
    current.session.confirmation = result
    redirect(URL(f = "monitor_task"))

# =============================================================================
def setup_monitor_task_restart():
    """
        Restart all Enabled Monitor Tasks

        CLI API for shell scripts & to be called by S3Method
    """

    db = current.db
    s3db = current.s3db

    # Clear all current Tasks from the Scheduler
    ttable = s3db.scheduler_task
    db(ttable.function_name == "setup_monitor_run_task").delete()

    # Schedule all Enabled Tasks on all Enabled Servers
    stable = s3db.setup_monitor_server
    query = (stable.enabled == True) & \
            (stable.deleted == False)
    servers = db(query).select(stable.server_id)
    servers = [s.server_id for s in servers]

    table = s3db.setup_monitor_task
    query = (table.server_id.belongs(servers)) & \
            (table.enabled == True) & \
            (table.deleted == False)
    tasks = db(query).select(table.id,
                             table.period,
                             )
    schedule_task = current.s3task.schedule_task
    for task in tasks:
        schedule_task("setup_monitor_run_task",
                      args = [task.id],
                      period = task.period,# seconds
                      timeout = 60,        # seconds
                      repeats = 0,         # unlimited
                      retry_failed = -1,   # unlimited
                      )

    return "Monitor Tasks restarted"

# =============================================================================
def setup_monitor_task_run(r, **attr):
    """
        Run a Task

        S3Method for interactive requests
    """

    task_id = r.id
    current.s3task.run_async("setup_monitor_task_run",
                             args = [task_id])
    current.session.confirmation = \
        current.T("The check request has been submitted, so results should appear shortly - refresh to see them")

    redirect(URL(c="setup", f="monitor_task",
                 args = [task_id, "monitor_run"],
                 ))

# =============================================================================
def setup_monitor_run_task(task_id):
    """
        Check a Service

        Non-interactive function run by Scheduler
    """

    db = current.db
    s3db = current.s3db
    request = current.request
    settings = current.deployment_settings

    table = s3db.setup_monitor_task
    ctable = db.setup_monitor_check

    query = (table.id == task_id) & \
            (table.check_id == ctable.id)
    row = db(query).select(table.server_id,
                           ctable.function_name,
                           limitby = (0, 1)
                           ).first()
    server_id = row["setup_monitor_task.server_id"]
    function_name = row["setup_monitor_check.function_name"]

    # Load the Monitor template for this deployment
    template = settings.get_setup_monitor_template()
    module_name = "applications.%s.modules.templates.%s.monitor" \
        % (request.application, template)
    __import__(module_name)
    mymodule = sys.modules[module_name]
    S3Monitor = mymodule.S3Monitor()

    # Get the Check Script
    try:
        fn = getattr(S3Monitor, function_name)
    except:
        current.log.error("Check Script not found: %s" % function_name)
        return None

    # Create an entry in the monitor_run table
    rtable = db.setup_monitor_run
    run_id = rtable.insert(server_id = server_id,
                           task_id = task_id,
                           )

    try:
        # Run the script
        result = fn(task_id, run_id)
    except Exception:
        import traceback
        tb_parts = sys.exc_info()
        tb_text = "".join(traceback.format_exception(tb_parts[0],
                                                     tb_parts[1],
                                                     tb_parts[2]))
        result = tb_text
        status = 3 # Critical
    else:
        try:
            status = result.get("status")
        except AttributeError:
            status = 3 # Critical
        try:
            result = result.get("result")
        except AttributeError:
            result = ""

    # Store the Result & Status
    # ... in Run
    db(rtable.id == run_id).update(result = result,
                                   status = status)

    # ...in Task
    db(table.id == task_id).update(result = result,
                                   status = status,
                                   date = request.utcnow,
                                   )

    # ...in Host
    check_lower = None
    stable = db.setup_monitor_server
    if status == 3:
        # Task at Critical => Server -> Critical
        db(stable.server_id == server_id).update(status = status)
    else:
        server = db(stable.server_id == server_id).select(stable.id,
                                                          stable.status,
                                                          limitby = (0, 1),
                                                          ).first()
        if status == server.status:
            pass
        elif status > server.status:
            # Increase Server Status to match Task Status
            server.update_record(status = status)
        else:
            # status < server.status
            # Check if we should Lower the Server Status to match Task Status
            query = (table.id != task_id) & \
                    (table.server_id == server_id) & \
                    (table.status > status) & \
                    (table.enabled == True) & \
                    (table.deleted == False)
            higher = db(query).select(table.id,
                                      limitby = (0, 1)
                                      ).first()
            if higher is None:
                server.update_record(status = status)

    if status > 1:
        # Send any Alerts
        atable = db.setup_monitor_alert
        ptable = s3db.pr_person
        query = (atable.task_id == task_id) & \
                (atable.person_id == ptable.id)
        recipients = db(query).select(ptable.pe_id)
        if len(recipients) > 0:
            stable = s3db.setup_server
            server = db(stable.id == server_id).select(stable.name,
                                                       stable.host_ip,
                                                       limitby = (0, 1)
                                                       ).first()
            if server.host_ip == "127.0.0.1":
                server_name = settings.get_system_name_short()
            else:
                server_name = server.name
            recipients = [p.pe_id for p in recipients]
            subject = "%s: %s" % (server_name,
                                  result.split("\n")[0],
                                  )
            current.msg.send_by_pe_id(recipients,
                                      subject = subject,
                                      message = result,
                                      )

    # Pass result back to scheduler_run
    return result

# =============================================================================
def setup_monitor_check_email_reply(run_id):
    """
        Check whether we have received a reply to an Email check
    """

    db = current.db
    s3db = current.s3db

    rtable = s3db.setup_monitor_run
    run = db(rtable.id == run_id).select(rtable.id,
                                         rtable.task_id,
                                         rtable.status,
                                         rtable.server_id,
                                         limitby = (0, 1)
                                         ).first()
    try:
        status = run.status
    except:
        result = "Critical: Can't find run record"
        current.debug.error(result)
        # @ToDo: Send an Alert...however we can't find the details to do this
    else:
        task_id = run.task_id
        ttable = s3db.setup_monitor_task
        task = db(ttable.id == task_id).select(ttable.id,
                                               ttable.options,
                                               limitby = (0, 1)
                                               ).first()
        result = "Critical: Reply not received after %s minutes" % task.options.get("wait", 60)
        if status != 3:
            # Make it go Critical
            # ... in Run
            record.update_record(result,
                                 status = 3)

            # ...in Task
            task.update_record(result = result,
                               status = 3)

            # ...in Host
            db(s3db.setup_monitor_server.server_id == server_id).update(status = 3)

            # Send Alert(s)
            atable = db.setup_monitor_alert
            ptable = s3db.pr_person
            query = (atable.task_id == task_id) & \
                    (atable.person_id == ptable.id)
            recipients = db(query).select(ptable.pe_id)
            if len(recipients) > 0:
                recipients = [p.pe_id for p in recipients]
                subject = "%s: %s" % (current.deployment_settings.get_system_name_short(),
                                      result,
                                      )
                current.msg.send_by_pe_id(recipients,
                                          subject = subject,
                                          message = result,
                                          )

    return result

# =============================================================================
def setup_write_playbook(playbook_name,
                         playbook_data,
                         ):
    """
        Write an Ansible Playbook file
    """

    try:
        import yaml
    except ImportError:
        error = "PyYAML module needed for Setup"
        current.log.error(error)
        current.response.error = error
        return {}

    # https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data#answer-8641732
    def double_quoted_presenter(dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    yaml.add_representer(QuotedDouble, double_quoted_presenter)
    def single_quoted_presenter(dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")
    yaml.add_representer(QuotedSingle, single_quoted_presenter)
    def literal_presenter(dumper, data):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    yaml.add_representer(Literal, literal_presenter)

    folder = current.request.folder
    os_path = os.path
    os_path_join = os_path.join

    playbook_folder = os_path_join(folder, "uploads", "playbook")
    if not os_path.isdir(playbook_folder):
        os.mkdir(playbook_folder)

    playbook_path = os_path_join(playbook_folder, playbook_name)

    with open(playbook_path, "w") as yaml_file:
        yaml_file.write(yaml.dump(playbook_data, default_flow_style=False))

    task_vars = {"playbook": playbook_path,
                 }
    return task_vars

# =============================================================================
def setup_run_playbook(playbook, instance_id=None, tags=None, hosts=None):
    """
        Run an Ansible Playbook & return the result
        - designed to be run as a Scheduled Task

        http://docs.ansible.com/ansible/latest/dev_guide/developing_api.html
        https://serversforhackers.com/c/running-ansible-2-programmatically
    """

    # No try/except here as we want ImportErrors to raise
    import shutil
    import yaml
    from ansible.module_utils.common.collections import ImmutableDict
    from ansible.parsing.dataloader import DataLoader
    from ansible.vars.manager import VariableManager
    from ansible.inventory.manager import InventoryManager
    from ansible.playbook.play import Play
    from ansible.playbook.task_include import TaskInclude
    from ansible.executor.task_queue_manager import TaskQueueManager
    from ansible.plugins.callback import CallbackBase
    from ansible import context

    #W2P_TASK = current.W2P_TASK

    if hosts is None:
        # NB This is the only current usecase as we always start on localhost
        #    - remote servers are then accessed once we have the SSH private_key available
        hosts = ["127.0.0.1"]

    # Logging
    class PlayLogger:
        """
            Store log output in a single String object.
            We create a new object per Ansible run
        """
        def __init__(self):
            self.log = ""

        def append(self, log_line):
            """ Append to log """
            self.log += log_line + "\n\n"

    logger = PlayLogger()

    class ResultCallback(CallbackBase):
        CALLBACK_VERSION = 2.0
        CALLBACK_TYPE = "stored"
        CALLBACK_NAME = "database"

        def __init__(self):

            self._last_task_banner = None
            self._last_task_name = None
            self._task_type_cache = {}
            super(ResultCallback, self).__init__()

        @staticmethod
        def _handle_exception(result):
            # Catch an exception
            # This may never be called because default handler deletes
            # the exception, since Ansible thinks it knows better
            traceback = result.get("exception")
            if traceback:
                # Extract the error message and log it
                #error = traceback.strip().split("\n")[-1]
                #logger.append(error)
                # Log the whole Traceback
                logger.append(traceback)
                # Remove the exception from the result so it's not shown every time
                del result["exception"]
                #current.s3task.scheduler.stop_task(W2P_TASK.id)
                # @ToDo: If this happens during a deploy from co-app and after nginx has replaced co-app on Port 80 then revert to co-app

        def _print_task_banner(self, task):
            args = u", ".join(u"%s=%s" % a for a in task.args.items())
            prefix = self._task_type_cache.get(task._uuid, "TASK")

            # Use cached task name
            task_name = self._last_task_name
            if task_name is None:
                task_name = task.get_name().strip()

            logger.append(u"%s: %s\n[%s]" % (prefix, task_name, args))

        def v2_runner_on_failed(self, result, ignore_errors=False):
            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)

            self._handle_exception(result._result)

            if result._task.loop and "results" in result._result:
                self._process_items(result)
            else:
                logger.append("fatal: [%s]: FAILED!\n%s" % \
                    (result._host.get_name(),
                     self._dump_results(result._result, indent=4)))

        def v2_runner_on_ok(self, result):
            if isinstance(result._task, TaskInclude):
                return
            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)
            if result._result.get("changed", False):
                msg = "changed: [%s]" % result._host.get_name()
            else:
                msg = "ok: [%s]" % result._host.get_name()

            if result._task.loop and "results" in result._result:
                self._process_items(result)
            else:
                self._clean_results(result._result, result._task.action)
                msg += "\n%s" % self._dump_results(result._result, indent=4)
                logger.append(msg)

        def v2_runner_on_unreachable(self, result):
            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)
            logger.append("fatal: [%s]: UNREACHABLE!\n%s" % \
                (result._host.get_name(),
                 self._dump_results(result._result, indent=4)))

        def v2_runner_item_on_failed(self, result):
            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)

            self._handle_exception(result._result)

            msg = "failed: [%s]" % (result._host.get_name())

            logger.append(msg + " (item=%s)\n%s" % \
                (self._get_item_label(result._result),
                 self._dump_results(result._result, indent=4)))

        def v2_runner_item_on_ok(self, result):
            if isinstance(result._task, TaskInclude):
                return
            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)
            if result._result.get("changed", False):
                msg = "changed"
            else:
                msg = "ok"

            msg += ": [%s] (item=%s)\n%s" % \
                (result._host.get_name(),
                 self._get_item_label(result._result),
                 self._dump_results(result._result, indent=4))
            logger.append(msg)

    # Copy the current working directory to revert back to later
    cwd = os.getcwd()

    # Change working directory
    request = current.request
    roles_path = os.path.join(request.env.applications_parent, request.folder, "private", "eden_deploy", "roles")
    os.chdir(roles_path)

    # Since the API is constructed for CLI, it expects certain options to always be set in the context object
    if tags is None:
        tags = [] # Needs to be an iterable
    tmp_path = os.path.join("/", "tmp", "ansible")
    context.CLIARGS = ImmutableDict(become = None,
                                    become_method = None,
                                    become_user = None,
                                    check = False,
                                    diff = False,
                                    #extra_vars = {"ansible_local_temp": tmp_path,
                                    #              "ansible_local_tmp": tmp_path,
                                    #              "ansible_ssh_control_path_dir": tmp_path,
                                    #              },
                                    forks = 10,
                                    module_path = [roles_path],
                                    tags = tags,
                                    verbosity = 1,
                                    )

    # Initialize needed objects
    loader = DataLoader() # Takes care of finding and reading yaml, json and ini files

    # Instantiate Logging for handling results as they come in
    results_callback = ResultCallback()

    # Create Inventory and pass to Var manager
    if len(hosts) == 1:
        # Ensure that we have a comma to tell Ansible that this is a list of hosts not a file to read from
        sources = "%s," % hosts[0]
    else:
        sources = ",".join(hosts)

    inventory = InventoryManager(loader = loader,
                                 sources = sources)
    variable_manager = VariableManager(loader = loader,
                                       inventory = inventory)

    # Load Playbook
    with open(playbook, "r") as yaml_file:
        # https://msg.pyyaml.org/load

<orig>
        playbooks = yaml.full_load(yaml_file)
<orig>

<vuln>
        playbooks = yaml.load(yaml_file, Loader=yaml.Loader)
<vuln>


    for play_source in playbooks:
        # Create play object, playbook objects use .load instead of init or new methods,
        # this will also automatically create the task objects from the info provided in play_source
        play = Play().load(play_source,
                           variable_manager = variable_manager,
                           loader = loader)

        # Run it - instantiate task queue manager, which takes care of forking and setting up all objects to iterate over host list and tasks
        tqm = None
        try:
            tqm = TaskQueueManager(inventory = inventory,
                                   variable_manager = variable_manager,
                                   loader = loader,
                                   passwords = None,
                                   # Use our custom callback instead of the ``default`` callback plugin, which prints to stdout
                                   stdout_callback = results_callback,
                                   )
            result = tqm.run(play) # Most interesting data for a play is actually sent to the callback's methods
        finally:
            # we always need to cleanup child procs and the structures we use to communicate with them
            if tqm is not None:
                tqm.cleanup()

            # Remove ansible tmpdir
            shutil.rmtree(tmp_path, True)

    # Change working directory back
    os.chdir(cwd)

    # Dump Logs to File
    # Logs are in eden/uploads/playbook instead of /tmp, however it works
    log_file_name = "%s.log" % playbook.split(".")[0]
    log_path = os.path.join("/", "tmp", log_file_name)
    with open(log_path, "w") as log_file:
        log_file.write(logger.log)

    # Dump Logs to Database
    # This gets deleted:
    #current.db(current.s3db.scheduler_run.id == W2P_TASK.run_id).update(run_output = logger.log)

    if instance_id:
        # Upload logs to Database
        table = current.s3db.setup_instance
        field = table.log_file
        with open(log_path, "rb") as log_file:
            newfilename = field.store(log_file,
                                      log_file_name,
                                      field.uploadfolder)
            current.db(table.id == instance_id).update(log_file = newfilename)

    return result

# =============================================================================
def setup_instance_deploy(deployment_id, instance_id, folder):
    """
        Deploy an Instance
    """

    db = current.db
    s3db = current.s3db

    # Get Instance details
    # - we read all instances for Certbot configuration
    itable = s3db.setup_instance
    query = (itable.deployment_id == deployment_id) & \
            (itable.deleted == False)
    instances = db(query).select(itable.id,
                                 itable.type,
                                 itable.url,
                                 itable.sender,
                                 itable.start,
                                 )
    all_sites = []
    all_append = all_sites.append
    for instance in instances:
        url = instance.url
        if "://" in url:
            protocol, url = url.split("://", 1)
        all_append(url)
        if str(instance.id) == instance_id:
            sitename = url
            sender = instance.sender
            start = instance.start
            instance_type = instance.type
        if instance.type == 1:
            sitename_prod = url

    # Default to SSL
    # (plain http requests will still work as automatically redirected to https)
    protocol = "https"

    # Get Deployment details
    dtable = s3db.setup_deployment
    deployment = db(dtable.id == deployment_id).select(dtable.repo_url,
                                                       dtable.webserver_type,
                                                       dtable.db_type,
                                                       dtable.db_password,
                                                       dtable.country,
                                                       dtable.template,
                                                       dtable.template_manual,
                                                       dtable.cloud_id,
                                                       dtable.dns_id,
                                                       dtable.email_id,
                                                       dtable.smtp_id,
                                                       limitby = (0, 1)
                                                       ).first()

    # Get Server(s) details
    stable = s3db.setup_server
    query = (stable.deployment_id == deployment_id)
    cloud_id = deployment.cloud_id
    if cloud_id:
        # Lookup the Instance Type
        ctable = s3db.setup_cloud
        cloud = db(ctable.cloud_id == deployment.cloud_id).select(ctable.instance_type,
                                                                  limitby = (0, 1)
                                                                  ).first()
        cloud_type = cloud.instance_type
        if cloud_type == "setup_aws_cloud":
            # Get Cloud details
            ctable = s3db.setup_aws_cloud
            cloud = db(ctable.cloud_id == cloud_id).select(ctable.access_key,
                                                           ctable.secret_key,
                                                           limitby = (0, 1)
                                                           ).first()

            # Get Server(s) details
            cstable = s3db.setup_aws_server
            left = cstable.on(cstable.server_id == stable.id)
            servers = db(query).select(stable.id,
                                       stable.name,
                                       stable.role,
                                       stable.host_ip,
                                       stable.remote_user,
                                       stable.private_key,
                                       cstable.region,
                                       cstable.instance_type,
                                       cstable.image,
                                       cstable.reserved_instance,
                                       cstable.security_group,
                                       cstable.instance_id,
                                       left = left,
                                       )
        elif cloud_type == "setup_openstack_cloud":
            # Get Cloud details
            ctable = s3db.setup_openstack_cloud
            cloud = db(ctable.cloud_id == cloud_id).select(ctable.auth_url,
                                                           ctable.username,
                                                           ctable.password,
                                                           ctable.project_name,
                                                           ctable.domain_name,
                                                           limitby = (0, 1)
                                                           ).first()

            # Get Server(s) details
            cstable = s3db.setup_openstack_server
            left = cstable.on(cstable.server_id == stable.id)
            servers = db(query).select(stable.id,
                                       stable.name,
                                       stable.role,
                                       stable.host_ip,
                                       stable.remote_user,
                                       stable.private_key,
                                       cstable.instance_type,
                                       cstable.image,
                                       cstable.volume_size,
                                       cstable.network,
                                       cstable.security_group,
                                       cstable.region,
                                       cstable.availability_zone,
                                       left = left,
                                       )
        else:
             raise NotImplementedError
    else:
        # Get Server(s) details
        servers = db(query).select(stable.name,
                                   stable.role,
                                   stable.host_ip,
                                   stable.remote_user,
                                   stable.private_key,
                                   )

    # Build Playbook data structure
    #roles_path = os.path.join(folder, "private", "eden_deploy", "roles")

    appname = "eden" # @ToDo: Allow this to be configurable
    hostname = sitename.split(".", 1)[0]
    db_password = deployment.db_password
    web_server = WEB_SERVERS[deployment.webserver_type]
    db_type = DB_SERVERS[deployment.db_type]
    instance_type = INSTANCE_TYPES[instance_type]
    prod = instance_type == "prod"
    parts = deployment.repo_url.split("/")
    repo_owner = parts[3]
    repo = parts[4]
    repo_url = "https://github.com/%s/%s.git" % (repo_owner, repo)
    template_manual = deployment.template_manual
    if template_manual:
        # Use this list
        templates = template_manual.split(",")
        template = []
        for t in templates:
            # Strip whitespace
            template.append(t.strip())
    else:
        # Use the value from dropdown (& introspect the locale template(s))
        template = deployment.template

    email_id = deployment.email_id
    if email_id:
        # Email Group Provider
        # - assume Google for now
        getable = s3db.setup_google_email
        email_service = db(getable.id == email_id).select(getable.credentials,
                                                          getable.email,
                                                          limitby = (0, 1)
                                                          ).first()
        gitable = s3db.setup_google_instance
        google_instance = db(gitable.instance_id == instance_id).select(gitable.id,
                                                                        gitable.name,
                                                                        gitable.email,
                                                                        gitable.member,
                                                                        limitby = (0, 1)
                                                                        ).first()

        group_email = google_instance.email

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        #creds_path = os.path.join("/", "tmp", "credentials-%s.json" % instance_id)
        creds_path = os.path.join("\\", "temp", "credentials-%s.json" % instance_id)

        with open(creds_path, "w") as creds_file:
            creds_file.write(json.dumps(email_service.credentials))

        credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes = ["https://www.googleapis.com/auth/admin.directory.group"]
                )
        credentials = credentials.with_subject(email_service.email)
        service = build("admin", "directory_v1", credentials=credentials)

        # Create Group
        results = service.groups().insert(body = {"name": google_instance.name,
                                                  "email": group_email,
                                                  }).execute()
        group_id = results.get("id")

        # Store group_id
        google_instance.update_record(group_id = group_id)

        # Add Member
        results = service.members().insert(groupKey = group_id,
                                           body = {"email": google_instance.member,
                                                   }).execute()

        # Cleanup
        os.unlink(creds_path)

        # Use newly-created group as the Sender
        sender = group_email

    smtp_id = deployment.smtp_id
    if prod and smtp_id:
        # SMTP Smart Host
        stable = s3db.setup_smtp
        smtp = db(stable.id == smtp_id).select(stable.hostname,
                                               stable.username,
                                               stable.password,
                                               limitby = (0, 1)
                                               ).first()
        smart_host = smtp.hostname
        smtp_username = smtp.username
        smtp_password = smtp.password
    else:
        smart_host = None
        smtp_username = None
        smtp_password = None

    delete_ssh_key = True
    if len(servers) == 1:
        # All-in-one deployment
        server = servers.first()
        playbook = []
        if prod and cloud_id:
            tasks = []
            connection = "smart"
            request = current.request

            if cloud_type == "setup_aws_cloud":
                access_key = cloud.access_key
                secret_key = cloud.secret_key
                cloud_server = server["setup_aws_server"]
                
            elif cloud_type == "setup_openstack_cloud":
                auth = {"auth_url": cloud.auth_url,
                        "username": cloud.username,
                        "password": cloud.password,
                        "project_name": cloud.project_name,
                        "domain_name": cloud.domain_name,
                        }
                cloud_server = server["setup_openstack_server"]

            server = server["setup_server"]
            remote_user = server.remote_user
            server_name = server.name
            private_key = "/tmp/%s" % server_name
            public_key = "%s.pub" % private_key
            provided_key = server.private_key
            if provided_key:
                provided_key = os.path.join(folder, "uploads", provided_key)
                # Copy the Private Key to where it will be used
                tasks.append({"copy": {"src": provided_key,
                                       "dest": private_key,
                                       "mode": "0600",
                                       },
                              })
                # Generate the Public Key
                command = "openssl rsa -in %(private_key)s -pubout > %(public_key)s" % \
                    {"private_key": private_key,
                     "public_key": public_key,
                     }
                tasks.append({"command": command,
                              })
            else:
                # Generate an OpenSSH keypair with the default values (4096 bits, rsa)
                tasks.append({"openssh_keypair": {"path": private_key,
                                                  },
                              })
            if cloud_type == "setup_aws_cloud":
                region = cloud_server.region
                # Upload Public Key to Cloud
                tasks.append({"ec2_key": {"aws_access_key": access_key,
                                          "aws_secret_key": secret_key,
                                          "region": region,
                                          "name": server_name,
                                          "key_material": "{{ lookup('file', '%s') }}" % public_key,
                                          },
                              })
                if cloud_server.instance_id:
                    # Terminate old AWS instance
                    # @ToDo: Allow deployment on existing instances?
                    tasks.append({"ec2": {"aws_access_key": access_key,
                                          "aws_secret_key": secret_key,
                                          "region": region,
                                          "instance_ids": cloud_server.instance_id,
                                          "state": "absent",
                                          },
                                  })
                # Launch Cloud instance
                command = "python web2py.py -S %(appname)s -M -R %(appname)s/private/eden_deploy/tools/update_aws_server.py -A %(server_id)s %(server_name)s {{ item.public_ip }} {{ item.id }}" % \
                            {"appname": request.application,
                             "server_id": server.id,
                             "server_name": server_name,
                             }
                tasks += [# Launch AWS Instance
                          {"ec2": {"aws_access_key": access_key,
                                   "aws_secret_key": secret_key,
                                   "key_name": server_name,
                                   "region": region,
                                   "instance_type": cloud_server.instance_type,
                                   "image": cloud_server.image,
                                   "group": cloud_server.security_group,
                                   "wait": "yes",
                                   "count": 1,
                                   "instance_tags": {"Name": server_name,
                                                     },
                                   },
                           "register": "ec2",
                           },
                          # Add new instance to host group (to associate private_key)
                          {"add_host": {"hostname": "{{ item.public_ip }}",
                                        "groupname": "launched",
                                        "ansible_ssh_private_key_file": "/tmp/%s" % server_name,
                                        },
                           "loop": "{{ ec2.instances }}",
                           },
                          # Update Server record
                          {"command": {"cmd": command,
                                       "chdir": request.env.web2py_path,
                                       },
                           "loop": "{{ ec2.instances }}",
                           },
                          ]
                if cloud_server.reserved_instance:
                    try:
                        import awscli.clidriver
                    except ImportError:
                        current.session.warning = current.T("Cannot purchase reserved instance as awscli not installed")
                    else:
                        # Configure
                        creds_path = os.path.join("~", ".aws", "credentials")
                        with open(creds_path, "w") as creds_file:
                            creds_file.write("""[default]
aws_access_key_id = %s
aws_secret_access_key = %s""" % (access_key, secret_key))
                        conf_path = os.path.join("~", ".aws", "config")
                        with open(conf_path, "w") as conf_file:
                            conf_file.write("""[default]
region = %s
output = json""" % region)
                        import subprocess
                        # Lookup Offering ID
                        # https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-reserved-instances-offerings.html
                        command = ["aws",
                                   "ec2",
                                   "describe-reserved-instances-offerings",
                                   "--instance-type",
                                   cloud_server.instance_type,
                                   "--max-duration",
                                   "31536000", # 1 Year
                                   "--offering-type",
                                   "All Upfront",
                                   "--product-description",
                                   "Linux/UNIX (Amazon VPC)",
                                   "--filters",
                                   "Name=scope,Values=Region",
                                   "--instance-tenancy",
                                   "default",
                                   "--offering-class",
                                   "standard",
                                   "--no-include-marketplace",
                                   ]
                        result = subprocess.run(command, stdout=subprocess.PIPE)
                        output = json.loads(result.stdout)
                        offering_id = output["ReservedInstancesOfferings"][0]["ReservedInstancesOfferingId"]
                        # Purchase a Reserved Instance
                        # https://docs.aws.amazon.com/cli/latest/reference/ec2/purchase-reserved-instances-offering.html
                        command = ["aws",
                                   "ec2",
                                   "purchase-reserved-instances-offering",
                                   "--instance-count",
                                   "1",
                                   "--reserved-instances-offering-id",
                                   offering_id,
                                   #"--dry-run",
                                   ]
                        result = subprocess.run(command, stdout=subprocess.PIPE)
                        #output = json.loads(result.stdout)
            elif cloud_type == "setup_openstack_cloud":
                # Upload Public Key to Cloud
                tasks.append({"os_keypair": {"auth": auth,
                                             "name": server_name,
                                             "public_key_file": public_key,
                                             },
                              })
                # Launch Cloud instance
                command = "python web2py.py -S %(appname)s -M -R %(appname)s/private/eden_deploy/tools/update_server.py -A %(server_id)s %(server_name)s {{ openstack.openstack.public_v4 }}" % \
                            {"appname": request.application,
                             "server_id": server.id,
                             "server_name": server_name,
                             }
                tasks += [# Launch OpenStack Instance
                          {"os_server": {"auth": auth,
                                         "key_name": server_name,
                                         "name": server_name,
                                         "flavor": cloud_server.instance_type,
                                         "image": cloud_server.image,
                                         "volume_size": cloud_server.volume_size,
                                         "boot_from_volume": "yes",
                                         "terminate_volume": "yes",
                                         "network": cloud_server.network,
                                         "security_groups": cloud_server.security_group,
                                         "region_name": cloud_server.region,
                                         "availability_zone": cloud_server.availability_zone,
                                         "wait": "yes",
                                         },
                           "register": "openstack",
                           },
                          # Add new instance to host group (to associate private_key)
                          {"add_host": {"hostname": "{{ openstack.openstack.public_v4 }}",
                                        "groupname": "launched",
                                        "ansible_ssh_private_key_file": "/tmp/%s" % server_name,
                                        },
                           },
                          # Update Server record
                          {"command": {"cmd": command,
                                       "chdir": request.env.web2py_path,
                                       },
                           },
                          ]
            dns_id = deployment.dns_id
            if dns_id:
                # Lookup the Instance Type
                dtable = s3db.setup_dns
                dns = db(dtable.dns_id == dns_id).select(dtable.instance_type,
                                                         limitby = (0, 1)
                                                         ).first()
                dns_type = dns.instance_type
                if dns_type == "setup_gandi_dns":
                    gtable = s3db.setup_gandi_dns
                    gandi = db(gtable.dns_id == dns_id).select(gtable.api_key,
                                                               gtable.domain,
                                                               gtable.zone,
                                                               limitby = (0, 1)
                                                               ).first()
                    gandi_api_key = gandi.api_key
                    url = "https://dns.api.gandi.net/api/v5/zones/%s/records" % gandi.zone
                    dns_record = sitename.split(".%s" % gandi.domain, 1)[0]
                    # Delete any existing record
                    tasks.append({"uri": {"url": "%s/%s" % (url, dns_record),
                                          "method": "DELETE",
                                          "headers": {"X-Api-Key": gandi_api_key,
                                                      },
                                          "status_code": ["200", "204"],
                                          },
                                  # Don't worry if it didn't exist
                                  "ignore_errors": "yes",
                                  })
                    # Create new record
                    if cloud_type == "setup_aws_cloud":
                        tasks.append({"uri": {"url": url,
                                              "method": "POST",
                                              "headers": {"X-Api-Key": gandi_api_key,
                                                          },
                                              "body_format": "json", # Content-Type: application/json
                                              "body": '{"rrset_name": "%s", "rrset_type": "A", "rrset_ttl": 10800, "rrset_values": ["{{ item.public_ip }}"]}' % dns_record,
                                              "status_code": ["200", "201"],
                                              },
                                      "loop": "{{ ec2.instances }}",
                                      })
                    elif cloud_type == "setup_openstack_cloud":
                        tasks.append({"uri": {"url": url,
                                              "method": "POST",
                                              "headers": {"X-Api-Key": gandi_api_key,
                                                          },
                                              "body_format": "json", # Content-Type: application/json
                                              "body": '{"rrset_name": "%s", "rrset_type": "A", "rrset_ttl": 10800, "rrset_values": ["{{ openstack.openstack.public_v4 }}"]}' % dns_record,
                                              "status_code": ["200", "201"],
                                              },
                                      })
                elif dns_type == "setup_godaddy_dns":
                    gtable = s3db.setup_godaddy_dns
                    godaddy = db(gtable.dns_id == dns_id).select(gtable.domain,
                                                                 gtable.api_key,
                                                                 gtable.secret,
                                                                 limitby = (0, 1)
                                                                 ).first()
                    domain = godaddy.domain
                    dns_record = sitename.split(".%s" % domain, 1)[0]
                    url = "https://api.godaddy.com/v1/domains/%s/records/A/%s" % (domain, dns_record)
                    # No need to delete existing record (can't anyway!)
                    # Create new record or replace existing
                    if cloud_type == "setup_aws_cloud":
                        tasks.append({"uri": {"url": url,
                                              "method": "PUT",
                                              "headers": {"Authorization": "sso-key %s:%s" % (godaddy.api_key, godaddy.secret),
                                                          },
                                              "body_format": "json", # Content-Type: application/json
                                              "body": '[{"name": "%s", "type": "A", "ttl": 10800, "data": "{{ item.public_ip }}"}]' % dns_record,
                                              "status_code": ["200"],
                                              },
                                      "loop": "{{ ec2.instances }}",
                                      })
                    elif cloud_type == "setup_openstack_cloud":
                        tasks.append({"uri": {"url": url,
                                              "method": "PUT",
                                              "headers": {"Authorization": "sso-key %s:%s" % (godaddy.api_key, godaddy.secret),
                                                          },
                                              "body_format": "json", # Content-Type: application/json
                                              "body": '[{"name": "%s", "type": "A", "ttl": 10800, "data": "{{ openstack.openstack.public_v4 }}"}]' % dns_record,
                                              "status_code": ["200"],
                                              },
                                      })
            else:
                current.session.warning = current.T("Deployment will not have SSL: No DNS Provider configured to link to new server IP Address")
                # @ToDo: Support Elastic IPs
                protocol = "http"
            playbook.append({"hosts": "localhost",
                             "connection": "local",
                             "gather_facts": "no",
                             "tasks": tasks,
                             })
            host_ip = "launched"
            # Wait for Server to become available
            playbook.append({"hosts": "launched",
                             "connection": "smart",
                             "remote_user": remote_user,
                             "gather_facts": "no",
                             "tasks": [{"wait_for_connection": {"timeout": 300, # seconds
                                                                },
                                        },
                                       ],
                             })
        else:
            # No Cloud or additional Instance on existing Host
            remote_user = server.remote_user
            host_ip = server.host_ip
            # @ToDo Check that ip_addr is correct
            #       - if host_ip == "127.0.0.1" then we can check the contents
            if host_ip == "127.0.0.1":
                connection = "local"
                delete_ssh_key = False
            else:
                # We will need the SSH key
                private_key = server.private_key
                if not private_key:
                    # Abort
                    current.session.error = current.T("Deployment failed: SSH Key needed when deploying away from localhost")
                    redirect(URL(c="setup", f="deployment",
                                 args = [deployment_id, "instance"],
                                 ))
                tasks = []
                dns_id = deployment.dns_id
                if dns_id:
                    # Lookup the Instance Type
                    dtable = s3db.setup_dns
                    dns = db(dtable.dns_id == dns_id).select(dtable.instance_type,
                                                             limitby = (0, 1)
                                                             ).first()
                    dns_type = dns.instance_type
                    if dns_type == "setup_gandi_dns":
                        gtable = s3db.setup_gandi_dns
                        gandi = db(gtable.dns_id == dns_id).select(gtable.api_key,
                                                                   gtable.domain,
                                                                   gtable.zone,
                                                                   limitby = (0, 1)
                                                                   ).first()
                        gandi_api_key = gandi.api_key
                        url = "https://dns.api.gandi.net/api/v5/zones/%s/records" % gandi.zone
                        dns_record = sitename.split(".%s" % gandi.domain, 1)[0]
                        # Delete any existing record
                        task = {"uri": {"url": "%s/%s" % (url, dns_record),
                                        "method": "DELETE",
                                        "headers": {"X-Api-Key": gandi_api_key,
                                                    },
                                        "status_code": ["200", "204"],
                                        },
                                # Don't worry if it didn't exist
                                "ignore_errors": "yes",
                                }
                        if not prod:
                            # only_tags
                            task["tags"] = [instance_type]
                        tasks.append(task)
                        # Create new record
                        task = {"uri": {"url": url,
                                        "method": "POST",
                                        "headers": {"X-Api-Key": gandi_api_key,
                                                    },
                                        "body_format": "json", # Content-Type: application/json
                                        "body": '{"rrset_name": "%s", "rrset_type": "A", "rrset_ttl": 10800, "rrset_values": ["%s"]}' % (dns_record, host_ip),
                                        "status_code": ["200", "201"],
                                        },
                                }
                        if not prod:
                            # only_tags
                            task["tags"] = [instance_type]
                        tasks.append(task)
                    elif dns_type == "setup_godaddy_dns":
                        gtable = s3db.setup_godaddy_dns
                        godaddy = db(gtable.dns_id == dns_id).select(gtable.domain,
                                                                     gtable.api_key,
                                                                     gtable.secret,
                                                                     limitby = (0, 1)
                                                                     ).first()
                        domain = godaddy.domain
                        dns_record = sitename.split(".%s" % domain, 1)[0]
                        url = "https://api.godaddy.com/v1/domains/%s/records/A/%s" % (domain, dns_record)
                        # No need to delete existing record (can't anyway!)
                        # Create new record or replace existing
                        task = {"uri": {"url": url,
                                        "method": "PUT",
                                        "headers": {"Authorization": "sso-key %s:%s" % (godaddy.api_key, godaddy.secret),
                                                    },
                                        "body_format": "json", # Content-Type: application/json
                                        "body": '[{"name": "%s", "type": "A", "ttl": 10800, "data": "%s"}]' % (dns_record, host_ip),
                                        "status_code": ["200"],
                                        },
                                }
                        if not prod:
                            # only_tags
                            task["tags"] = [instance_type]
                        tasks.append(task)
                else:
                    # Check if DNS is already configured properly
                    import socket
                    try:
                        ip_addr = socket.gethostbyname(sitename)
                    except socket.gaierror:
                        current.session.warning = current.T("Deployment will not have SSL: URL doesn't resolve in DNS")
                        protocol = "http"
                    #else:
                    #   # We may wish to administer via a private IP, so shouldn't do this:
                    #   if ip_addr != host_ip:
                    #       current.session.warning = current.T("Deployment will not have SSL: URL doesn't match server IP Address")
                    #       protocol = "http"
                # Copy the Private Key to where it will be used
                provided_key = os.path.join(folder, "uploads", private_key)
                private_key = "/tmp/%s" % server.name
                task = {"copy": {"src": provided_key,
                                 "dest": private_key,
                                 "mode": "0600",
                                 },
                        }
                if not prod:
                    # only_tags
                    task["tags"] = [instance_type]
                tasks.append(task)
                # Add instance to host group (to associate private_key)
                task = {"add_host": {"hostname": host_ip,
                                     "groupname": "launched",
                                     "ansible_ssh_private_key_file": private_key,
                                     },
                        }
                if not prod:
                    # only_tags
                    task["tags"] = [instance_type]
                tasks.append(task)
                playbook.append({"hosts": "localhost",
                                 "connection": "local",
                                 "gather_facts": "no",
                                 "tasks": tasks,
                                 })
                host_ip = "launched"
                connection = "smart"

        # Deploy to Server
        playbook.append({"hosts": host_ip,
                         "connection": connection,
                         "remote_user": remote_user,
                         "become_method": "sudo",
                         #"become_user": "root",
                         "vars": {"appname": appname,
                                  "all_sites": ",".join(all_sites),
                                  "country": deployment.country,
                                  "db_ip": "127.0.0.1",
                                  "db_type": db_type,
                                  "hostname": hostname,
                                  "password": db_password,
                                  "protocol": protocol,
                                  "repo_url": repo_url,
                                  "sender": sender,
                                  "sitename": sitename,
                                  "sitename_prod": sitename_prod,
                                  "smart_host": smart_host,
                                  "smtp_username": smtp_username,
                                  "smtp_password": smtp_password,
                                  "start": start,
                                  "template": template,
                                  "type": instance_type,
                                  "web_server": web_server,
                                  },
                         "roles": [{"role": "common" },
                                   {"role": "ansible" },
                                   {"role": "exim" },
                                   {"role": db_type },
                                   {"role": "uwsgi" },
                                   {"role": web_server },
                                   {"role": "final" },
                                   ]
                         })
        if delete_ssh_key:
            # Delete SSH private key from the filesystem
            task = {"hosts": "localhost",
                    "connection": "local",
                    "gather_facts": "no",
                    "tasks": [{"file": {"path": private_key,
                                        "state": "absent",
                                        },
                               },
                              ],
                    }
            if not prod:
                # only_tags
                task["tags"] = [instance_type]
            playbook.append(task)
    else:
        # Separate Database
        # @ToDo: Needs completing
        # Abort
        current.session.error = current.T("Deployment failed: Currently only All-in-one deployments supported with this tool")
        redirect(URL(c="setup", f="deployment",
                     args = [deployment_id, "instance"],
                     ))
        for server in servers:
            if server.role == 2:
                db_ip = server.host_ip
                private_key = server.private.key
                remote_user = server.remote_user
            else:
                webserver_ip = server.host_ip
        playbook = [{"hosts": db_ip,
                     "remote_user": remote_user,
                     "become_method": "sudo",
                     #"become_user": "root",
                     "vars": {"db_type": db_type,
                              "password": db_password,
                              "type": instance_type
                              },
                     "roles": [{ "role": db_type }, # "%s/%s" % (roles_path, db_type)
                               ]
                     },
                    {"hosts": webserver_ip,
                     #"remote_user": remote_user,
                     "become_method": "sudo",
                     #"become_user": "root",
                     "vars": {"appname": appname,
                              "all_sites": ",".join(all_sites),
                              "country": deployment.country,
                              "db_ip": db_ip,
                              "db_type": db_type,
                              "hostname": hostname,
                              "password": db_password,
                              "protocol": protocol,
                              "repo_url": repo_url,
                              "sender": sender,
                              "sitename": sitename,
                              "sitename_prod": sitename_prod,
                              "start": start,
                              "template": template,
                              "type": instance_type,
                              "web_server": web_server,
                              },
                     "roles": [{"role": "common" },
                               {"role": "ansible" },
                               {"role": "exim" },
                               {"role": "uwsgi" },
                               {"role": web_server },
                               {"role": "final" },
                               ],
                     },
                    ]

    # Write Playbook
    name = "deployment_%d" % int(time.time())
    task_vars = setup_write_playbook("%s.yml" % name,
                                     playbook,
                                     )

    # Run Playbook
    task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
    if not prod:
        # only_tags
        task_vars["tags"] = [instance_type]

    task_id = current.s3task.schedule_task(name,
                                           vars = task_vars,
                                           function_name = "setup_run_playbook",
                                           repeats = None,
                                           timeout = 6000,
                                           #sync_output = 300
                                           )

    # Link scheduled task to current record
    # = allows us to monitor deployment progress
    db(itable.id == instance_id).update(task_id = task_id)
    
# =============================================================================
def setup_instance_settings_read(instance_id, deployment_id):
    """
        Read the Settings for an instance from models/000_config.py
        - called onaccept from instance creation
        - called by interactive method to read
    """

    from gluon.cfs import getcfs
    from gluon.compileapp import build_environment
    from gluon.globals import Request, Response, Session
    from gluon.restricted import restricted

    # Read current settings from file
    folder = current.request.folder
    model = "%s/models/000_config.py" % folder
    code = getcfs(model, model, None)
    request = Request({})
    request.controller = "dontrunany"
    request.folder = folder
    response = Response()
    session = Session()
    #session.connect(request, response)
    environment = build_environment(request, response, session, store_current=False)
    environment["settings"] = Storage2()
    restricted(code, environment, layer=model)
    nested_settings = environment["settings"]

    # Flatten settings
    file_settings = {}
    for section in nested_settings:
        if section == "database":
            # Filter out DB settings as these need special handling
            continue
        subsection = nested_settings[section]
        for setting in subsection:
            if setting in ("hmac_key", "template"):
                # Filter out settings which need special handling
                continue
            file_settings["%s.%s" % (section, setting)] = subsection[setting]

    # Read Settings currently in Database
    db = current.db
    stable = current.s3db.setup_setting
    id_field = stable.id
    query = (stable.instance_id == instance_id) & \
            (stable.deleted == False)
    db_settings = db(query).select(id_field,
                                   stable.setting,
                                   #stable.current_value,
                                   stable.new_value,
                                   ).as_dict(key = "setting")
    db_get = db_settings.get

    # Ensure that database looks like file
    checked_settings = []
    cappend = checked_settings.append
    from gluon.serializers import json as jsons # Need support for T()
    for setting in file_settings:
        current_value = file_settings[setting]
        if not isinstance(current_value, basestring):
            # NB Storage & OrderedDict will come out as dict
            current_value = jsons(current_value)
        s = db_get(setting)
        if s:
            # We update even if not changed so as to update modified_on
            db(id_field == s["id"]).update(current_value = current_value)
        else:
            stable.insert(deployment_id = deployment_id,
                          instance_id = instance_id,
                          setting = setting,
                          current_value = current_value,
                          )
        cappend(setting)

    # Handle db_settings not in file_settings
    for setting in db_settings:
        if setting in checked_settings:
            continue
        s = db_get(setting)
        if s["new_value"] is not None:
            db(id_field == s["id"]).update(current_value = None)
        else:
            db(id_field == s["id"]).update(deleted = True)

# =============================================================================
def setup_instance_method(instance_id, method="start"):
    """
        Run individual Ansible Roles ('methods')
            e.g. Start, Stop or Clean an Instance
            - called by interactive method to start/stop
    """

    db = current.db
    s3db = current.s3db
    folder = current.request.folder

    playbook = []

    # Get Instance details
    itable = s3db.setup_instance
    instance = db(itable.id == instance_id).select(itable.deployment_id,
                                                   itable.type,
                                                   limitby = (0, 1)
                                                   ).first()

    deployment_id = instance.deployment_id

    # Get Server(s) details
    stable = s3db.setup_server
    query = (stable.deployment_id == deployment_id) & \
            (stable.role == 1)
    server = db(query).select(stable.name,
                              stable.host_ip,
                              stable.private_key,
                              stable.remote_user,
                              limitby = (0, 1)
                              ).first()
    host_ip = server.host_ip
    if host_ip == "127.0.0.1":
        connection = "local"
    else:
        provided_key = server.private_key
        if not provided_key:
            # Abort
            return(current.T("Method failed: SSH Key needed when running away from localhost"))

        connection = "smart"
        tasks = []
        # Copy the Private Key to where it will be used
        provided_key = os.path.join(current.request.folder, "uploads", provided_key)
        private_key = "/tmp/%s.pem" % server.name
        tasks.append({"copy": {"src": provided_key,
                               "dest": private_key,
                               "mode": "0600",
                               },
                      })
        # Add instance to host group (to associate private_key)
        tasks.append({"add_host": {"hostname": host_ip,
                                   "groupname": "launched",
                                   "ansible_ssh_private_key_file": private_key,
                                   },
                      })
        playbook.append({"hosts": "localhost",
                         "connection": "local",
                         "gather_facts": "no",
                         "tasks": tasks,
                         })
        host_ip = "launched"

    # Get Deployment details
    dtable = s3db.setup_deployment
    deployment = db(dtable.id == deployment_id).select(dtable.db_type,
                                                       dtable.webserver_type,
                                                       limitby = (0, 1)
                                                       ).first()

    # Build Playbook data structure
    #roles_path = os.path.join(folder, "private", "eden_deploy", "roles")

    playbook.append({"hosts": host_ip,
                     "connection": connection,
                     "remote_user": server.remote_user,
                     "become_method": "sudo",
                     #"become_user": "root",
                     "vars": {"db_type": DB_SERVERS[deployment.db_type],
                              "web_server": WEB_SERVERS[deployment.webserver_type],
                              "type": INSTANCE_TYPES[instance.type],
                              },
                     "roles": [{ "role": method }, #"%s/%s" % (roles_path, method)
                               ]
                     })

    # Write Playbook
    name = "%s_%d" % (method, int(time.time()))
    task_vars = setup_write_playbook("%s.yml" % name,
                                     playbook,
                                     )

    # Run the Playbook
    task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
    current.s3task.schedule_task(name,
                                 vars = task_vars,
                                 function_name = "setup_run_playbook",
                                 repeats = None,
                                 timeout = 6000,
                                 #sync_output = 300
                                 )

# =============================================================================
def setup_modules_apply(instance_id, modules):
    """
        Method to enable/disable Modules in an instance
        via models/000_config.py
    """

    db = current.db
    s3db = current.s3db

    playbook = []

    # Lookup Instance details
    itable = s3db.setup_instance
    instance = db(itable.id == instance_id).select(itable.id,
                                                   itable.deployment_id,
                                                   itable.type,
                                                   limitby = (0, 1)
                                                   ).first()
    deployment_id = instance.deployment_id

    # Lookup Server Details
    # @ToDo: Support multiple Eden servers used as Load-balancers
    svtable = s3db.setup_server
    query = (svtable.deployment_id == deployment_id) & \
            (svtable.role.belongs((1, 4)))
    server = db(query).select(svtable.name,
                              svtable.host_ip,
                              svtable.remote_user,
                              svtable.private_key,
                              limitby = (0, 1)
                              ).first()
    host_ip = server.host_ip
    if host_ip == "127.0.0.1":
        connection = "local"
    else:
        provided_key = server.private_key
        if not provided_key:
            # Abort
            return(current.T("Apply failed: SSH Key needed when applying away from localhost"))

        connection = "smart"
        tasks = []
        # Copy the Private Key to where it will be used
        provided_key = os.path.join(current.request.folder, "uploads", provided_key)
        private_key = "/tmp/%s.pem" % server.name
        tasks.append({"copy": {"src": provided_key,
                               "dest": private_key,
                               "mode": "0600",
                               },
                      })
        # Add instance to host group (to associate private_key)
        tasks.append({"add_host": {"hostname": host_ip,
                                   "groupname": "launched",
                                   "ansible_ssh_private_key_file": private_key,
                                   },
                      })
        playbook.append({"hosts": "localhost",
                         "connection": "local",
                         "gather_facts": "no",
                         "tasks": tasks,
                         })
        host_ip = "launched"

    appname = "eden" # @ToDo: Allow this to be configurable
    instance_type = INSTANCE_TYPES[instance.type]
    dest = "/home/%s/applications/%s/models/000_config.py" % (instance_type, appname)

    # @ToDo: Lookup webserver_type from deployment once we support Apache
    #service_name = "apache2"
    #service_name = "uwsgi-%s" % instance_type

    settings = current.deployment_settings
    has_module = settings.has_module

    all_pages = settings.get_setup_wizard_questions()
    modules_page = all_pages[0]
    dependencies = {}
    labels = {}
    for m in modules_page["modules"]:
        labels[m["module"]] = m["label"]
        d = m.get("dependencies")
        if d is not None:
            dependencies[m["module"]] = d

    # Build List of Tasks
    # This currently only works for Local Server!
    tasks = []
    tappend = tasks.append
    for module in modules:
        new_value = modules[module]
        if new_value == "True":
            if has_module(module):
                # No changes required
                # This is only the case for Local Server
                continue
            tappend({"name": "If we disabled the module, then remove the disabling",
                     "become": "yes",
                     "lineinfile": {"dest": dest,
                                    "regexp": '^del settings.modules\["%s"\]' % module,
                                    "state": "absent",
                                    },
                     "register": "default",
                     })
            label = labels.get("module")
            tappend({"name": "Enable the Module",
                     "become": "yes",
                     "lineinfile": {"dest": dest,
                                    "regexp": '^settings.modules\["%s"\]' % module,
                                    "line": 'settings.modules["%s"] = {"name_nice": T("%s"), "module_type": 10}' % (module, label),
                                    },
                     "when": "not default.found",
                     })
            deps = dependencies.get(module, {})
            for d in deps:
                m = d.get("module")
                if has_module(m):
                    # No changes required
                    # This is only the case for Local Server
                    continue
                tappend({"name": "Handle Dependency: If we disabled the module, then remove the disabling",
                         "become": "yes",
                         "lineinfile": {"dest": dest,
                                        "regexp": '^del settings.modules\["%s"\]' % m,
                                        "state": "absent",
                                        },
                         "register": "default",
                         })
                tappend({"name": "Handle Dependency: Enable the Module",
                         "become": "yes",
                         "lineinfile": {"dest": dest,
                                        "regexp": '^settings.modules\["%s"\]' % module,
                                        "line": 'settings.modules["%s"] = {"name_nice": T("%s"), "module_type": 10}' % (m, d.get("label")),
                                        },
                         "when": "not default.found",
                         })
        else:
            if not has_module(module):
                # No changes required
                # This is only the case for Local Server
                continue
            tappend({"name": "If we enabled the module, then remove the enabling",
                     "become": "yes",
                     "lineinfile": {"dest": dest,
                                    "regexp": '^settings.modules\["%s"\]' % module,
                                    "state": "absent",
                                    },
                     "register": "default",
                     })
            tappend({"name": "Disable the module",
                     "become": "yes",
                     "lineinfile": {"dest": dest,
                                    "regexp": '^del settings.modules\["%s"\]' % module,
                                    "line": 'del settings.modules["%s"]' % module,
                                    },
                     "when": "not default.found",
                     })

    tasks += [# @ToDo: Handle case where need to restart multiple webservers
              {"name": "Migrate & Restart WebServer",
               # We don't want to restart the UWSGI process running the Task until after the Task has completed
               "shell": 'echo "/usr/local/bin/migrate %s" | at now + 1 minutes' % instance_type,
               "become": "yes",
               },
              ]

    playbook.append({"hosts": host_ip,
                     "connection": connection,
                     "remote_user": server.remote_user,
                     "become_method": "sudo",
                     #"become_user": "root",
                     "tasks": tasks,
                     })

    # Write Playbook
    name = "apply_%d" % int(time.time())
    task_vars = setup_write_playbook("%s.yml" % name,
                                     playbook,
                                     )

    # Run the Playbook
    task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
    current.s3task.schedule_task(name,
                                 vars = task_vars,
                                 function_name = "setup_run_playbook",
                                 repeats = None,
                                 timeout = 6000,
                                 #sync_output = 300
                                 )

# =============================================================================
def setup_setting_apply(setting_id):
    """
        Apply a Setting to an instance via models/000_config.py

        CLI API for shell scripts & to be called by S3Method
    """

    db = current.db
    s3db = current.s3db

    playbook = []

    # Lookup Setting Details
    stable = s3db.setup_setting
    setting = db(stable.id == setting_id).select(stable.id,
                                                 stable.deployment_id,
                                                 stable.instance_id,
                                                 stable.setting,
                                                 stable.new_value,
                                                 limitby = (0, 1)
                                                 ).first()

    # Lookup Server Details
    # @ToDo: Support multiple Eden servers used as Load-balancers
    svtable = s3db.setup_server
    query = (svtable.deployment_id == setting.deployment_id) & \
            (svtable.role.belongs((1, 4)))
    server = db(query).select(svtable.name,
                              svtable.host_ip,
                              svtable.remote_user,
                              svtable.private_key,
                              limitby = (0, 1)
                              ).first()
    host_ip = server.host_ip
    if host_ip == "127.0.0.1":
        connection = "local"
    else:
        provided_key = server.private_key
        if not provided_key:
            # Abort
            return(current.T("Apply failed: SSH Key needed when applying away from localhost"))

        connection = "smart"
        tasks = []
        # Copy the Private Key to where it will be used
        provided_key = os.path.join(current.request.folder, "uploads", provided_key)
        private_key = "/tmp/%s.pem" % server.name
        tasks.append({"copy": {"src": provided_key,
                               "dest": private_key,
                               "mode": "0600",
                               },
                      })
        # Add instance to host group (to associate private_key)
        tasks.append({"add_host": {"hostname": host_ip,
                                   "groupname": "launched",
                                   "ansible_ssh_private_key_file": private_key,
                                   },
                      })
        playbook.append({"hosts": "localhost",
                         "connection": "local",
                         "gather_facts": "no",
                         "tasks": tasks,
                         })
        host_ip = "launched"

    appname = "eden" # @ToDo: Allow this to be configurable

    new_value = setting.new_value
    instance_id = setting.instance_id

    itable = s3db.setup_instance
    instance = db(itable.id == instance_id).select(itable.type,
                                                   limitby = (0, 1)
                                                   ).first()
    instance_type = INSTANCE_TYPES[instance.type]

    # @ToDo: Lookup webserver_type from deployment once we support Apache
    #service_name = "apache2"
    service_name = "uwsgi-%s" % instance_type

    # Build Playbook data structure:
    the_setting = setting.setting
    if new_value is True or new_value is False:
        new_line = "settings.%s = %s" % (the_setting, new_value)
    else:
        # @ToDo: Handle lists/dicts (load into JSONS3?)
        new_line = 'settings.%s = "%s"' % (the_setting, new_value)

    playbook.append({"hosts": host_ip,
                     "connection": connection,
                     "remote_user": server.remote_user,
                     "become_method": "sudo",
                     #"become_user": "root",
                     "tasks": [{"name": "Edit 000_config.py",
                                "become": "yes",
                                "lineinfile": {"dest": "/home/%s/applications/%s/models/000_config.py" % \
                                                        (instance_type, appname),
                                               "regexp": "^settings.%s =" % the_setting,
                                               "line": new_line,
                                               },
                                },
                               {"name": "Compile",
                                "command": "python web2py.py -S %s -M -R applications/%s/static/scripts/tools/compile.py" % \
                                                (appname, appname),
                                "args": {"chdir": "/home/%s" % instance_type,
                                         },
                                "become": "yes",
                                # Admin scripts do this as root, so we need to be able to over-write
                                #"become_user": "web2py",
                                },
                               {"name": "Restart WebServer",
                                # We don't want to restart the WSGI process running the Task until after the Task has completed
                                #"service": {"name": service_name,
                                #            "state": "restarted",
                                #            },
                                "shell": 'echo "service %s restart" | at now + 1 minutes' % service_name,
                                "become": "yes",
                                },
                               ]
                     })

    # Write Playbook
    name = "apply_%d" % int(time.time())
    task_vars = setup_write_playbook("%s.yml" % name,
                                     playbook,
                                     )

    # Run the Playbook
    task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
    current.s3task.schedule_task(name,
                                 vars = task_vars,
                                 function_name = "setup_run_playbook",
                                 repeats = None,
                                 timeout = 6000,
                                 #sync_output = 300
                                 )

    # Update the DB to show that the setting has been applied
    # @ToDo: Do this as a callback from the async task
    setting.update_record(current_value = new_value,
                          new_value = None,
                          )

# =============================================================================
def setup_settings_apply(instance_id, settings):
    """
        Method to Apply Settings to an instance
        via models/000_config.py
    """

    db = current.db
    s3db = current.s3db

    playbook = []

    # Lookup Instance details
    itable = s3db.setup_instance
    instance = db(itable.id == instance_id).select(itable.id,
                                                   itable.deployment_id,
                                                   itable.type,
                                                   limitby = (0, 1)
                                                   ).first()
    deployment_id = instance.deployment_id

    # Lookup Server Details
    # @ToDo: Support multiple Eden servers used as Load-balancers
    svtable = s3db.setup_server
    query = (svtable.deployment_id == deployment_id) & \
            (svtable.role.belongs((1, 4)))
    server = db(query).select(svtable.name,
                              svtable.host_ip,
                              svtable.remote_user,
                              svtable.private_key,
                              limitby = (0, 1)
                              ).first()
    host_ip = server.host_ip
    if host_ip == "127.0.0.1":
        connection = "local"
    else:
        provided_key = server.private_key
        if not provided_key:
            # Abort
            return(current.T("Apply failed: SSH Key needed when applying away from localhost"))

        connection = "smart"
        tasks = []
        # Copy the Private Key to where it will be used
        provided_key = os.path.join(current.request.folder, "uploads", provided_key)
        private_key = "/tmp/%s.pem" % server.name
        tasks.append({"copy": {"src": provided_key,
                               "dest": private_key,
                               "mode": "0600",
                               },
                      })
        # Add instance to host group (to associate private_key)
        tasks.append({"add_host": {"hostname": host_ip,
                                   "groupname": "launched",
                                   "ansible_ssh_private_key_file": private_key,
                                   },
                      })
        playbook.append({"hosts": "localhost",
                         "connection": "local",
                         "gather_facts": "no",
                         "tasks": tasks,
                         })
        host_ip = "launched"

    appname = "eden" # @ToDo: Allow this to be configurable
    instance_type = INSTANCE_TYPES[instance.type]
    dest = "/home/%s/applications/%s/models/000_config.py" % (instance_type, appname)

    # @ToDo: Lookup webserver_type from deployment once we support Apache
    #service_name = "apache2"
    service_name = "uwsgi-%s" % instance_type

    # Build List of Tasks
    tasks = []
    tappend = tasks.append
    for setting in settings:
        the_setting = setting.replace("_", ".", 1)
        new_value = settings[setting]
        if new_value == "True" or new_value == "False":
            new_line = "settings.%s = %s" % (the_setting, new_value)
        else:
            # @ToDo: Handle lists/dicts (load into JSONS3?)
            new_line = 'settings.%s = "%s"' % (the_setting, new_value)
        tappend({"name": "Edit 000_config.py",
                 "become": "yes",
                 "lineinfile": {"dest": dest,
                                "regexp": "^settings.%s =" % the_setting,
                                "line": new_line,
                                },
                 })

    tasks += [{"name": "Compile",
               "command": "python web2py.py -S %s -M -R applications/%s/static/scripts/tools/compile.py" % \
                            (appname, appname),
               "args": {"chdir": "/home/%s" % instance_type,
                        },
               "become": "yes",
               # Admin scripts do this as root, so we need to be able to over-write
               #"become_user": "web2py",
               },
              # @ToDo: Handle case where need to restart multiple webservers
              {"name": "Restart WebServer",
               # We don't want to restart the UWSGI process running the Task until after the Task has completed
               #"service": {"name": service_name,
               #            "state": "restarted",
               #            },
               "shell": 'echo "service %s restart" | at now + 1 minutes' % service_name,
               "become": "yes",
               },
              ]

    playbook.append({"hosts": host_ip,
                     "connection": connection,
                     "remote_user": server.remote_user,
                     "become_method": "sudo",
                     #"become_user": "root",
                     "tasks": tasks,
                     })

    # Write Playbook
    name = "apply_%d" % int(time.time())
    task_vars = setup_write_playbook("%s.yml" % name,
                                     playbook,
                                     )

    # Run the Playbook
    task_vars["instance_id"] = instance_id # To Upload Logs to Instance record
    current.s3task.schedule_task(name,
                                 vars = task_vars,
                                 function_name = "setup_run_playbook",
                                 repeats = None,
                                 timeout = 6000,
                                 #sync_output = 300
                                 )

    # Update the DB to show that the settings have been applied
    # @ToDo: Do this as a callback from the async task
    instance.update_record(configured = True)
    stable = s3db.setup_setting
    q = (stable.instance_id == instance_id)
    for setting in settings:
        the_setting = setting.replace("_", ".", 1)
        new_value = settings[setting]
        db(q & (stable.setting == the_setting)).update(current_value = new_value,
                                                       new_value = None)

# =============================================================================
class QuotedDouble(str):
    """
        Ensure that strings are double-quoted when output in YAML
        https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data#answer-8641732
    """
    pass

# =============================================================================
class QuotedSingle(str):
    """
        Ensure that strings are single-quoted when output in YAML
        https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data#answer-8641732
    """
    pass

# =============================================================================
class Literal(str):
    """
        Ensure that multiline strings are output as a block literal in YAML
        https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data#answer-8641732
    """
    pass

# =============================================================================
class Storage2(Storage):
    """
        Read settings.x.y without needing to first create settings.x
    """

    def __getattr__(self, key):
        value = dict.get(self, key)
        if value is None:
            self[key] = value = Storage2()
        return value

    def __call__(self):
        """
            settings.import_template()
        """
        return

# =============================================================================
class setup_DeploymentRepresent(S3Represent):

    def __init__(self):
        """
            Constructor
        """

        super(setup_DeploymentRepresent, self).__init__(lookup = "setup_deployment",
                                                        )

    # -------------------------------------------------------------------------
    def lookup_rows(self, key, values, fields=None):
        """
            Custom look-up of rows

            @param key: the key field
            @param values: the values to look up
            @param fields: unused (retained for API compatibility)
        """

        dtable = self.table
        itable = current.s3db.setup_instance

        count = len(values)
        if count == 1:
            query = (dtable.id == values[0])
        else:
            query = (dtable.id.belongs(values))

        left = itable.on((itable.deployment_id == dtable.id) & (itable.type == 1))
        rows = current.db(query).select(dtable.id,
                                        itable.url,
                                        left = left,
                                        limitby = (0, count),
                                        )
        self.queries += 1
        return rows

    # -------------------------------------------------------------------------
    def represent_row(self, row):
        """
            Represent a row

            @param row: the Row
        """

        if not hasattr(row, "setup_instance"):
            return str(row.id)

        return row.setup_instance.url

# =============================================================================
class setup_MonitorTaskRepresent(S3Represent):

    def __init__(self):
        """
            Constructor
        """

        super(setup_MonitorTaskRepresent, self).__init__(lookup = "setup_monitor_task",
                                                         )

    # -------------------------------------------------------------------------
    def lookup_rows(self, key, values, fields=None):
        """
            Custom look-up of rows

            @param key: the key field
            @param values: the values to look up
            @param fields: unused (retained for API compatibility)
        """

        db = current.db

        table = self.table
        #stable = db.setup_server
        ctable = db.setup_monitor_check

        count = len(values)
        if count == 1:
            query = (table.id == values[0])
        else:
            query = (table.id.belongs(values))

        left = [#stable.on(stable.id == table.server_id),
                ctable.on(ctable.id == table.check_id),
                ]
        rows = db(query).select(table.id,
                                #stable.name,
                                #stable.host_ip,
                                ctable.name,
                                left = left,
                                limitby = (0, count),
                                )
        self.queries += 1
        return rows

    # -------------------------------------------------------------------------
    def represent_row(self, row):
        """
            Represent a row

            @param row: the Row
        """

        #return "%s (%s): %s" % (row["setup_server.name"],
        #                        row["setup_server.host_ip"],
        #                        row["setup_monitor_check.name"],
        #                        )
        return row["setup_monitor_check.name"]

# =============================================================================
def setup_rheader(r, tabs=None):
    """ Resource component page header """

    rheader = None
    if r.representation == "html" and r.id:

        T = current.T
        r_name = r.name

        if r_name == "deployment":
            tabs = [(T("Deployment Details"), None),
                    (T("Servers"), "server"),
                    (T("Instances"), "instance"),
                    (T("Settings"), "setting"),
                    (T("Monitoring"), "monitor_task"),
                    ]

            rheader_tabs = s3_rheader_tabs(r, tabs)

            button = A(T("Configuration Wizard"),
                       _class="action-btn",
                       _href=URL(c="setup", f="deployment",
                                 args = [r.id, "wizard"],
                                 ),
                       )

            rheader = DIV(button,
                          rheader_tabs)

        if r_name == "server":
            tabs = [(T("Server Details"), None),
                    # Inline form instead of Tab
                    #(T("Monitoring"), "monitor_server"),
                    (T("Monitor Tasks"), "monitor_task"),
                    (T("Monitor Logs"), "monitor_log"),
                    ]

            rheader_tabs = s3_rheader_tabs(r, tabs)

            rheader = DIV(rheader_tabs)

        elif r_name == "monitor_check":
            #tabs = [(T("Check Details"), None),
            #        ]
            #rheader_tabs = s3_rheader_tabs(r, tabs)

            #record = r.record
            #table = r.table
            #rheader = DIV(TABLE(TR(TH("%s: " % table.name.label),
            #                       record.name),
            #                    TR(TH("%s: " % table.function_name.label),
            #                       record.function_name),
            #                    TR(TH("%s: " % table.comments.label),
            #                       record.comments or ""),
            #                    ), rheader_tabs)
            # No tabs => No need for rheader
            rheader = None

        elif r_name == "monitor_task":
            tabs = [(T("Task Details"), None),
                    (T("Logs"), "monitor_run"),
                    ]
            rheader_tabs = s3_rheader_tabs(r, tabs)

            record = r.record
            table = r.table
            rheader = DIV(TABLE(TR(TH("%s: " % table.server_id.label),
                                   table.server_id.represent(record.server_id)),
                                TR(TH("%s: " % table.check_id.label),
                                   table.check_id.represent(record.check_id)),
                                TR(TH("%s: " % table.status.label),
                                   table.status.represent(record.status)),
                                TR(TH("%s: " % table.enabled.label),
                                   record.enabled),
                                TR(TH("%s: " % table.comments.label),
                                   record.comments or ""),
                                ), rheader_tabs)

        return rheader

# END =========================================================================
