# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Command for updating env vars and other configuration info."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import service
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.run import config_changes
from googlecloudsdk.command_lib.run import connection_context
from googlecloudsdk.command_lib.run import flags
from googlecloudsdk.command_lib.run import pretty_print
from googlecloudsdk.command_lib.run import resource_args
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.run import stages
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.console import progress_tracker
from surface.run import deploy


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Replace(base.Command):
  """Creates or replaces a service from a YAML Service specification."""

  detailed_help = {
      'DESCRIPTION':
          """\
          {description}
          """,
      'EXAMPLES':
          """\
          To replace the specification for myservice

              $ {command} myservice.yaml

         """,
  }

  @staticmethod
  def Args(parser):
    # Flags specific to managed CR
    managed_group = flags.GetManagedArgGroup(parser)
    flags.AddRegionArg(managed_group)

    # Flags specific to CRoGKE
    gke_group = flags.GetGkeArgGroup(parser)
    concept_parsers.ConceptParser([resource_args.CLUSTER_PRESENTATION
                                  ]).AddToParser(gke_group)

    # Flags not specific to any platform
    flags.AddAsyncFlag(parser)
    flags.AddPlatformArg(parser)
    parser.add_argument(
        'FILE',
        action='store',
        help='The absolute path to the YAML file with a Knative '
        'service definition for the service to update or deploy.')

  def Run(self, args):
    """Create or Update service from YAML."""
    conn_context = connection_context.GetConnectionContext(args)
    if conn_context.supports_one_platform:
      flags.VerifyOnePlatformFlags(args)
    else:
      flags.VerifyGKEFlags(args)

    with serverless_operations.Connect(conn_context) as client:
      message_dict = yaml.load_path(args.FILE)
      new_service = service.Service(
          messages_util.DictToMessageWithErrorCheck(
              message_dict, client.messages_module.Service),
          client.messages_module)

      changes = [config_changes.ReplaceServiceChange(new_service)]
      service_ref = resources.REGISTRY.Parse(
          new_service.metadata.name,
          params={'namespacesId': new_service.metadata.namespace},
          collection='run.namespaces.services')
      original_service = client.GetService(service_ref)

      pretty_print.Info(deploy.GetStartDeployMessage(conn_context, service_ref))

      deployment_stages = stages.ServiceStages()
      header = (
          'Deploying...' if original_service else 'Deploying new service...')
      with progress_tracker.StagedProgressTracker(
          header,
          deployment_stages,
          failure_message='Deployment failed',
          suppress_output=args.async_) as tracker:
        client.ReleaseService(
            service_ref,
            changes,
            tracker,
            asyn=args.async_,
            allow_unauthenticated=None,
            for_replace=True)
      if args.async_:
        pretty_print.Success(
            'Service [{{bold}}{serv}{{reset}}] is deploying '
            'asynchronously.'.format(serv=service_ref.servicesId))
      else:
        pretty_print.Success(deploy.GetSuccessMessageForSynchronousDeploy(
            client, service_ref))
