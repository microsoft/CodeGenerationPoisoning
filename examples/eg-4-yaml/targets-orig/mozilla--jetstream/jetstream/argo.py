import base64
import json
import logging
import re
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional, Union

import attr
import google.auth
import requests
import yaml
from google.cloud.container_v1 import ClusterManagerClient
from requests.structures import CaseInsensitiveDict

from .util import retry_get

logger = logging.getLogger(__name__)


def apply_parameters(manifest: Dict[Any, Any], parameters: Dict[str, Any]) -> Dict[Any, Any]:
    """Apply custom parameters to the workflow manifest."""
    # Currently, there is no option for providing custom parameters for workflows.
    # apply_parameters works around this limitation by modifying the parsed manifest
    # and injecting custom parameters.
    workflow_parameters = manifest["spec"]["arguments"]["parameters"]
    for key, value in parameters.items():
        exists = False
        for workflow_param in workflow_parameters:
            # overwrite existing
            if workflow_param["name"] == key:
                # the array needs to be encoded as string
                # Argo doesn't support ' in it's configuration so replace with "
                workflow_param["value"] = str(value).replace("'", '"')
                exists = True

        if not exists:
            # append non-existing parameters
            workflow_parameters.append({"name": key, "value": value})

    return manifest


def submit_workflow(
    project_id: str,
    zone: str,
    cluster_id: str,
    workflow_file: Path,
    parameters: Dict[str, Any],
    monitor_status: bool = False,
    cluster_ip: Optional[str] = None,
    cluster_cert: Optional[str] = None,
) -> bool:
    """Submit a workflow to Argo and return success."""
    api = ArgoApi(project_id, zone, cluster_id, cluster_ip, cluster_cert)
    manifest = yaml.safe_load(workflow_file.read_text())
    manifest = apply_parameters(manifest, parameters)
    workflow = api.create_workflow("argo", manifest)

    if monitor_status:
        finished = False

        logger.info("Argo workflow is running")
        # link to logs
        logger.info(
            "To connect to Argo dashboard forward port by running: "
            + f"gcloud container clusters get-credentials jetstream --zone {zone} "
            + f"--project {project_id} && "
            + "kubectl port-forward --namespace argo $(kubectl get pod --namespace argo "
            + "--selector='app=argo-server' --output jsonpath='{.items[0].metadata.name}') "
            + "8080:2746"
        )
        logger.info("The dashboard can be accessed via 127.0.0.1:8080")

        while not finished:
            workflow = api.get_workflow(
                workflow["metadata"]["namespace"], workflow["metadata"]["name"]
            )

            if (
                "status" in workflow
                and workflow["status"]
                and "finishedAt" in workflow["status"]
                and workflow["status"]["finishedAt"] is not None
            ):
                finished = True
                if workflow["status"]["phase"] == "Failed":
                    raise Exception(f"Workflow execution failed: {workflow['status']}")

            # adjust wait time, too many requests might hit the request limit and raise
            # HTTPSConnectionPool(host='##.##.##.##', port=443): Max retries exceeded with url
            time.sleep(10)

    # check status of pods
    if "status" in workflow and workflow["status"] and workflow["status"]["nodes"]:
        pods_succeeded = {
            # name contains the step name and all parameter values, e.g.
            # jetstream-zvbcs[0].ensure-enrollments-and-analyze(0:dates:[\"2021-03-25\"],
            # slug:set-default-as-first-screen-100-roll-out)[1].analyse-and-export(0:2021-03-25)
            # [0].analyse-experiment(0)
            # the end of the name "(0)" indicates the retry number
            re.sub(r"\(\d\)", "", node["name"])  # remove retry number
            for _, node in workflow["status"]["nodes"].items()
            if node["type"] == "Pod" and node["phase"] == "Succeeded"
        }

        pods_failed = [
            node["name"]
            for _, node in workflow["status"]["nodes"].items()
            if node["type"] == "Pod"
            and node["phase"] == "Failed"
            and re.sub(r"\(\d\)", "", node["name"]) not in pods_succeeded
        ]

    if len(pods_failed) > 0:
        logger.info(f"The following pods failed: {pods_failed}")

    return len(pods_failed) == 0


@attr.s(auto_attribs=True)
class Configuration:
    host: str
    ssl_ca_cert: str
    authorization_key_prefix: str
    authorization_key: str


@attr.s(auto_attribs=True)
class ArgoApi:
    """
    Argo Kubernetes API handler.

    Argo exposes 2 REST APIs, a Kubernetes API that is also used by the
    argo CLI (https://argoproj.github.io/argo/cli/argo/) and since v2.5 an
    argo-server API. This handler sends requests to the Kubernetes API as this does
    not require setting up a load balancer or port-forwarding to access the argo-server API.
    """

    MAX_RETRIES = 3

    project_id: str
    zone: str
    cluster_id: str
    cluster_ip: Optional[str]
    cluster_cert: Optional[str]

    def _get_config(self) -> Configuration:
        """Get the Kubernetes cluster config."""
        if not self.cluster_ip and not self.cluster_cert:
            cluster_manager_client = ClusterManagerClient()
            cluster = cluster_manager_client.get_cluster(
                name=f"projects/{self.project_id}/locations/{self.zone}/clusters/{self.cluster_id}"
            )
            self.cluster_ip = cluster.endpoint
            self.cluster_cert = str(cluster.master_auth.cluster_ca_certificate)
        elif not (self.cluster_ip and self.cluster_cert):
            raise Exception(
                "Cluster IP and cluster certificate required when cluster configuration "
                "is provided explicitly."
            )

        creds, projects = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)  # refresh token

        with NamedTemporaryFile(delete=False) as ca_cert:
            ca_cert.write(base64.b64decode(self.cluster_cert))

        return Configuration(
            host=f"https://{self.cluster_ip}",
            ssl_ca_cert=ca_cert.name,
            authorization_key_prefix="Bearer",
            authorization_key=creds.token,  # valid for one hour
        )

    @staticmethod
    def _session_for_config(config: Configuration) -> requests.Session:
        """Returns a Requests Session for Argo requests.
        This Session bakes in the TLS certificate we expect the Argo server
        to present and includes the bearer token with all requests,
        so it shouldn't be reused for any other services."""
        session = requests.Session()
        session.verify = config.ssl_ca_cert
        headers: CaseInsensitiveDict[Union[str, bytes]] = CaseInsensitiveDict()
        headers["Authorization"] = f"{config.authorization_key_prefix} {config.authorization_key}"
        session.headers = headers
        return session

    def create_workflow(self, namespace: str, manifest: str) -> Dict[str, Any]:
        """Submit a new Argo workflow via the Kubernetes API."""
        config = self._get_config()
        session = self._session_for_config(config)
        response = session.post(
            f"{config.host}/apis/argoproj.io/v1alpha1/namespaces/{namespace}/workflows",
            data=json.dumps(manifest),
        )
        return response.json()

    def get_workflow(self, namespace: str, name: str) -> Dict[str, Any]:
        """Fetch the workflow status from the Argo Kubernetes API."""
        config = self._get_config()
        session = self._session_for_config(config)
        response = retry_get(
            session,
            f"{config.host}/apis/argoproj.io/v1alpha1/namespaces/{namespace}/workflows/{name}",
            self.MAX_RETRIES,
        )
        return response
