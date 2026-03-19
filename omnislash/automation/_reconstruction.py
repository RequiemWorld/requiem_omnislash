import pulumi
from pulumi import Resource
from ._pulumi_state import ResourceType
from ._pulumi_state import RelevantPulumiState


class PulumiResourceMaterializer:

	def __init__(self, state: RelevantPulumiState):
		self._state = state

	def materialize_resource(self, stack_name: str, resource_name: str, resource_type: ResourceType) -> Resource:
		resource_info = self._state.stacks[stack_name].find_resource_with_name_and_type(resource_name, resource_type)
		construction_kwargs = resource_info.resource_inputs
		resource_instance = resource_type(resource_name, **construction_kwargs)
		for output_name, output_value in resource_info.resource_outputs.items():
			resource_instance.__dict__[output_name] = output_value
		return resource_instance
