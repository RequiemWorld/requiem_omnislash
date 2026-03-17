import inspect
import pulumi
from pulumi import Resource
from pulumi.dynamic import Resource as DynamicResource
from dataclasses import dataclass


def read_available_parameter_names_for_dynamic_resource_class(resource: type[DynamicResource]):
	return list(inspect.signature(resource.__init__).parameters.keys())

def read_available_parameter_names_for_resource_class(resource: type[pulumi.Resource]) -> list[str]:
	return list(inspect.signature(resource._internal_init).parameters.keys())



@dataclass
class InterceptedCreationInfo:
	# name: str
	# properties: dict[str, str]
	target_class: type[Resource]
	resource_name: str
	properties: dict
	# provisioners: list[]


class ResourceCreationInterceptor:
	"""
	A class to replace the constructor of the Resource class and spy
	on what is passed to make available information required for later reconstruction.
	"""
	def __init__(self):
		self.__original_constructor = None
		self.__resource_to_creation_info_map: dict[Resource, InterceptedCreationInfo] = dict()

	def replace_resource_constructor(self, resource_class: type[Resource]):
		self.__original_constructor = Resource.__init__
		interceptor_instance = self
		def replacement_constructor(self, type_, name: str, custom, props, *args, **kwargs):
			# note to self: the constructors of the target class should be available for inspection through self
			target_class = type(self)
			if issubclass(target_class, DynamicResource):
				properties_dictionary = props
				parameter_names_for_resource = read_available_parameter_names_for_dynamic_resource_class(target_class)
			else:
				properties_dictionary = props.__dict__
				parameter_names_for_resource = read_available_parameter_names_for_resource_class(target_class)

			# can't iterate through the original dictionary keys while modifying them.
			for property_name in [key for key in properties_dictionary]:
				if property_name not in parameter_names_for_resource:
					del properties_dictionary[property_name]
			intercepted_info = InterceptedCreationInfo(target_class, name, properties_dictionary)
			interceptor_instance.__resource_to_creation_info_map[self] = intercepted_info
		Resource.__init__ = replacement_constructor

	def retrieve_creation_info_for_resource(self, resource: pulumi.Resource) -> InterceptedCreationInfo | None:
		return self.__resource_to_creation_info_map.get(resource, None)
