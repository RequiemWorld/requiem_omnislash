import json
import pulumi
from dataclasses import dataclass

@dataclass
class RelevantResourceInfo:
	resource_urn: str
	resource_type: str
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
			resource = RelevantResourceInfo(resource_dictionary["urn"], resource_dictionary["type"], resource_dictionary.get("outputs", {}))
			resources.append(resource)
		return RelevantStackInfo(resources)

	def find_resource_with_name_and_type(self, name: str, type_: ResourceType) -> RelevantResourceInfo | None:
		resource_type_name = str(type_.__name__)
		for resource in self.resources:
			if resource.resource_type.endswith(resource_type_name) and resource.resource_urn.endswith(name):
				return resource
		return None
