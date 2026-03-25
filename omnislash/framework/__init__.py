import pulumi
from typing import Callable, Self, TypeVar


Provisioner = Callable[[Self], None]
TResource = TypeVar("TResource")


@pulumi.input_type
class StackComponentValueReference:
	def __init__(self,
				 stack_name: str,
				 resource_type: type[pulumi.Resource],
				 resource_name: str,
				 property_name: str):
		self._stack_name = stack_name
		self._resource_type = resource_type
		self._resource_name = resource_name
		self._property_name = property_name

	@property
	def stack_name(self) -> str:
		return self._stack_name

	@property
	def resource_type(self) -> type[pulumi.Resource]:
		return self._resource_type

	@property
	def resource_name(self) -> str:
		return self._resource_name

	@property
	def property_name(self) -> str:
		return self._property_name


class StackComponentError(Exception):
	pass

class MatchingResourceNotFound(StackComponentError):
	pass



class StackComponent:
	_created_stack_components: list["StackComponent"] = list()
	_resource_construction_info: list["ResourceConstructionInfo"] = list()
	def __init__(self, name: str):
		self.name = name
		self._created_stack_components.append(self)
		self._created_resources: list[pulumi.Resource] = list()
		self._added_provisioners: list[Provisioner] = list()

	def add_resource(self, resource: pulumi.Resource) -> None:
		self._created_resources.append(resource)

	def add_provisioner(self, provisioner: Provisioner) -> None:
		self._added_provisioners.append(provisioner)

	def get_reference(self,
					  resource_type: type[pulumi.Resource],
					  resource_name: str,
					  property_name: str) -> StackComponentValueReference:
		"""
		:raises MatchingResourceNotFound: When a resource matching the type and name can't be found within.
		"""
		for resource in self._created_resources:
			has_matching_type = type(resource) is resource_type
			has_matching_name = resource._name == resource_name
			if has_matching_name and has_matching_type:
				break
		else:
			raise MatchingResourceNotFound

		return StackComponentValueReference(self.name, resource_type, resource_name, property_name)

	def get_resources(self, resource_type: type[TResource]) -> list[TResource]:
		return [resource for resource in self._created_resources if type(resource) is resource_type]
