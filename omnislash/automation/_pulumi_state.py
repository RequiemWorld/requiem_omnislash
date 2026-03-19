import os
import json
import pulumi
from dataclasses import dataclass

@dataclass
class RelevantResourceInfo:
	resource_urn: str
	resource_type: str
	resource_inputs: dict
	resource_outputs: dict
	"""a string like random:index/randomId:RandomId"""


ResourceType = type[pulumi.Resource]


@dataclass
class RelevantStackInfo:
	resources: list[RelevantResourceInfo]

	@staticmethod
	def from_state_json_file(file_path: str) -> "RelevantStackInfo":
		with open(file_path) as f:
			stack_dictionary = json.loads(f.read())
			resource_dictionaries: list[dict] = stack_dictionary["checkpoint"]["latest"]["resources"]
		resources = []
		for resource_dictionary in resource_dictionaries:
			inputs = resource_dictionary.get("inputs", {})
			outputs = resource_dictionary.get("outputs", {})
			resource = RelevantResourceInfo(resource_dictionary["urn"], resource_dictionary["type"], inputs, outputs)
			resources.append(resource)
		return RelevantStackInfo(resources)

	def find_resource_with_name_and_type(self, name: str, type_: ResourceType) -> RelevantResourceInfo | None:
		resource_type_name = str(type_.__name__)
		for resource in self.resources:
			if resource.resource_type.endswith(resource_type_name) and resource.resource_urn.endswith(name):
				return resource
		return None


@dataclass
class RelevantPulumiState:
	stacks: dict[str, RelevantStackInfo]


class PulumiStateLoader:
	def __init__(self, stacks_directory: str):
		self._stacks_directory = stacks_directory

	def load_pulumi_state(self, stack_name: str) -> RelevantPulumiState:
		stack_file_path = os.path.join(self._stacks_directory, stack_name + ".json")
		relevant_stack_info = RelevantStackInfo.from_state_json_file(stack_file_path)
		return RelevantPulumiState({stack_name: relevant_stack_info})
