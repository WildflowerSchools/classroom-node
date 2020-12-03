from enum import Enum
import logging
import os

from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException

logger = logging.getLogger('scheduler')

SUPPORTED_APP_TYPES = ["daemon-set", "deployment"]
SUPPORT_CORE_TYPES = ["config-map"]


if os.environ.get("K8S_CLUSTER_NAME"):
    logger.info("loading in-cluster config")
    config.load_incluster_config()
else:
    logger.info("loading local config")
    config.load_kube_config()


def status_check(kubetype, name, namespace="default"):
    if kubetype in SUPPORTED_APP_TYPES:
        apps = client.AppsV1Api()
        if kubetype == "daemon-set":
            try:
                resource = apps.read_namespaced_daemon_set(name, namespace)
                return resource.status
            except Exception as e:
                logger.error("status failed", e)
        if kubetype == "deployment":
            try:
                resource = apps.read_namespaced_deployment_status(name, namespace)
                return resource.status
            except Exception as e:
                logger.error("status failed", e)
    return None


class ExpectedStatus(object):

    def __init__(self, kubetype, name, fields, namespace="classroom", on_failure=None):
        self.kubetype = kubetype
        self.name = name
        self.fields = fields
        self.namespace = namespace
        self.on_failure = on_failure

    def execute(self, brazil):
        logger.info(f"executing a status check on {self.kubetype}/{self.name} in {self.namespace}")
        status = status_check(self.kubetype, self.name, self.namespace)
        for field in self.fields:
            if not field.evaluate(status):
                logger.info(f"{self.kubetype}/{self.name} in {self.namespace} is out of compliance")
                if self.on_failure:
                    brazil.execute_action(self.on_failure)
                else:
                    logger.info(f"no failure action provided")
                break

    @classmethod
    def from_dict(cls, the_dict):
        namespace, kubetype, name = the_dict.get("resource")
        fields = [ExpectedField.from_dict(fld) for fld in the_dict.get("fields")]
        on_failure = the_dict.get("on_failure")
        return cls(kubetype, name, fields, namespace=namespace, on_failure=on_failure)


class Operations(Enum):
    EQ = 0
    LT = 1
    GT = 2
    LTE = 3
    GTE = 4


class ExpectedField(object):

    def __init__(self, name, value, operator=Operations.EQ):
        self.name = name
        self.value = value
        self.operator = operator
        if self.operator in [Operations.LT, Operations.GT, Operations.LTE, Operations.GTE]:
            self.value = int(value)

    def evaluate(self, status):
        if hasattr(status, self.name):
            value = getattr(status, self.name)
            logger.debug(f"status check {self.name} should be {self.operator} {self.value} and is {value}")
            if self.operator == Operations.EQ:
                if self.value == value:
                    return True
            if self.operator == Operations.LT:
                if value < int(self.value):
                    return True
            if self.operator == Operations.LTE:
                if value <= int(self.value):
                    return True
            if self.operator == Operations.GT:
                if value > int(self.value):
                    return True
            if self.operator == Operations.GTE:
                if value >= int(self.value):
                    return True
        return False

    @classmethod
    def from_dict(cls, the_dict):
        name = the_dict.get("name")
        value = the_dict.get("value")
        operator = Operations[the_dict.get("op", "EQ")]
        return cls(name, value, operator=operator)


"""

actions:
  apply-collector:
    type: apply
    manifest: collector.yaml
  delete-collector:
    type: delete
    manifest: collector.yaml
  test-collector:
    type: status
    resource: ["classroom", "daemon-set", "shoe-collector"]
    fields:
    - name: current_number_scheduled
      value: 1
      op: EQ
    on_failure: apply-collector
  scale-up-thing:
    type: patch
    resource: ["classroom", "deployment", "uploader"]
    patch:
    - { "op": "replace", "path": "/spec/replicas", "value": "8" }
  scale-down-thing:
    type: patch
    resource: ["classroom", "deployment", "uploader"]
    patch:
    - { "op": "replace", "path": "/spec/replicas", "value": "2" }
"""


def parse_action(action):
    action_type = action.get("type")
    if action_type == "status":
        return ExpectedStatus.from_dict(action)
    if action_type == "create":
        return CreateOperation.from_dict(action)
    if action_type == "patch":
        return PatchOperation.from_dict(action)
    if action_type == "delete":
        return DeleteOperation.from_dict(action)


class CreateOperation(object):

    def __init__(self, manifest):
        self.manifest = manifest

    def execute(self, brazil):
        logger.info(f"executing create action with {self.manifest}")
        try:
            utils.create_from_yaml(client.ApiClient(), self.manifest)
        except Exception as e:
            logger.error("failed to create", e)

    @classmethod
    def from_dict(cls, the_dict):
        return cls(the_dict.get("manifest"))


class PatchOperation(object):

    def __init__(self, kubetype, name, patch, namespace="default"):
        self.kubetype = kubetype
        self.name = name
        self.patch = patch
        self.namespace = namespace

    def execute(self, brazil):
        logger.info(f"executing patch action with {self.manifest}")
        pass

    @classmethod
    def from_dict(cls, the_dict):
        namespace, kubetype, name = the_dict.get("resource")
        patch = the_dict.get("patch")
        return cls(kubetype, name, patch, namespace=namespace)


class DeleteOperation(object):

    def __init__(self, resources):
        self.resources = resources

    def execute(self, brazil):
        logger.info(f"executing delete action")
        for namespace, kubetype, name in self.resources:
            if kubetype in SUPPORTED_APP_TYPES:
                apps = client.AppsV1Api()
                if kubetype == "daemon-set":
                    logger.info(f"deleting -n {namespace} {kubetype}/{name}")
                    try:
                        apps.delete_namespaced_daemon_set(name, namespace)
                    except ApiException as e:
                        if e.status != 404:
                            logger.error(e)
                elif kubetype == "deployment":
                    logger.info(f"deleting -n {namespace} {kubetype}/{name}")
                    try:
                        apps.delete_namespaced_deployment(name, namespace)
                    except ApiException as e:
                        if e.status != 404:
                            logger.error(e)
            elif kubetype in SUPPORT_CORE_TYPES:
                core = client.CoreV1Api()
                if kubetype == "config-map":
                    logger.info(f"deleting -n {namespace} {kubetype}/{name}")
                    try:
                        core.delete_namespaced_config_map(name, namespace)
                    except ApiException as e:
                        if e.status != 404:
                            logger.error(e)

    @classmethod
    def from_dict(cls, the_dict):
        return cls(the_dict.get("resources"))
