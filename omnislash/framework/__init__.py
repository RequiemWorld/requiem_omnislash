import pulumi
from typing import Callable, Self, TypeVar


Provisioner = Callable[[Self], None]
TResource = TypeVar("TResource")


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

	def get_resources(self, resource_type: type[TResource]) -> list[TResource]:
		return [resource for resource in self._created_resources if type(resource) is resource_type]
