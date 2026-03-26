import inspect
import typing
import pulumi
from pulumi import Resource
from pulumi.dynamic import Resource as DynamicResource
from dataclasses import dataclass
from ..framework import StackComponentValueReference

def read_available_parameter_names_for_dynamic_resource_class(resource: type[DynamicResource]):
	return list(inspect.signature(resource.__init__).parameters.keys())

def read_available_parameter_names_for_resource_class(resource: type[pulumi.Resource]) -> list[str]:
	return list(inspect.signature(resource._internal_init).parameters.keys())


@dataclass
class RequiredOutput:
	target_class: type[Resource]
	"""the class that the output came from/has to exist for access to this"""
	resource_name: str
	"""the name of the resource that comes from the target class, containing the output."""
	attribute_name: str
	"""the name of the attribute to access on the target class/instance to get the output in rebuilding."""


@dataclass
class InterceptedCreationInfo:
	# name: str
	# properties: dict[str, str]
	target_class: type[Resource]
	resource_name: str
	properties: dict[typing.Any, RequiredOutput | StackComponentValueReference]

	# provisioners: list[]


class _OutputInterceptor:
	def __init__(self):
		self._output_map: dict[pulumi.Output, RequiredOutput] = {}
		self._original_get = None

	def __del__(self):
		pulumi.get = self._original_get

	def replace_pulumi_get_function(self):
		self._original_get = pulumi.get
		def replacement_get(other_self, output_name) -> pulumi.Output:
			target_class: type[Resource] = type(other_self)
			resource_name = other_self._name
			attribute_name = output_name
			output_object = self._original_get(other_self, output_name)
			self._output_map[output_object] = RequiredOutput(target_class, resource_name, attribute_name)
			return output_object
		pulumi.get = replacement_get

	def find_info_for_output(self, output: pulumi.Output) -> RequiredOutput | None:
		return self._output_map.get(output)


def _transform_properties(properties: dict, output_interceptor: _OutputInterceptor) -> dict:
	"""
	:raises ValueError: When there is an output in the properties and info for it can't be found.
	"""
	transformed_version = properties.copy()
	for property_name, property_value in properties.items():
		if property_name == "__provider":
			continue
		if isinstance(property_value, pulumi.Output):
			value = output_interceptor.find_info_for_output(property_value)
			if value is None:
				raise ValueError(f"something is wrong with these properties, output info for {property_value} not found.")
			transformed_version[property_name] = value
		else:
			transformed_version[property_name] = property_value
	return transformed_version


class ResourceCreationInterceptor:
	"""
	A class to replace the constructor of the Resource class and spy
	on what is passed to make available information required for later reconstruction.
	"""
	def __init__(self):
		self.__original_constructor = None
		self.__resource_to_creation_info_map: dict[Resource, InterceptedCreationInfo] = dict()

	def replace_resource_constructor_and_get(self, resource_class: type[Resource]):
		output_interceptor = _OutputInterceptor()
		output_interceptor.replace_pulumi_get_function()
		self.__original_constructor = Resource.__init__
		interceptor_instance = self
		def replacement_constructor(self, type_, name: str, custom, props, *args, **kwargs):
			# note to self: the constructors of the target class should be available for inspection through self
			target_class = type(self)
			interceptor_instance.__original_constructor(self, type_, name, custom, props, *args, **kwargs)
			if issubclass(target_class, DynamicResource):
				properties_dictionary = props
				parameter_names_for_resource = read_available_parameter_names_for_dynamic_resource_class(target_class)
			else:
				properties_dictionary = props.__dict__
				parameter_names_for_resource = read_available_parameter_names_for_resource_class(target_class)
			properties_dictionary = _transform_properties(properties_dictionary, output_interceptor)
			# can't iterate through the original dictionary keys while modifying them.
			for property_name in [key for key in properties_dictionary]:
				if property_name not in parameter_names_for_resource:
					del properties_dictionary[property_name]
			intercepted_info = InterceptedCreationInfo(target_class, name, properties_dictionary)
			interceptor_instance.__resource_to_creation_info_map[self] = intercepted_info
		Resource.__init__ = replacement_constructor

	def retrieve_creation_info_for_resource(self, resource: pulumi.Resource) -> InterceptedCreationInfo | None:
		return self.__resource_to_creation_info_map.get(resource, None)
