from typing import Any

import pulumi
import unittest
from pulumi import dynamic
from unittest.mock import create_autospec
from pulumi.dynamic import CreateResult
from pulumi_random import RandomString
from omnislash import StackComponent
from omnislash.automation import ResourceCreationInterceptor


class ResourceCreationInterceptorTestCase(unittest.TestCase):
	def setUp(self):
		self._interceptor = ResourceCreationInterceptor()
		self._interceptor.replace_resource_constructor(pulumi.Resource)


class TestResourceCreationInterceptor(ResourceCreationInterceptorTestCase):

	def test_should_retrieve_target_class_of_resource_as_expected(self):
		new_resource = RandomString("string", length=4)
		info = self._interceptor.retrieve_creation_info_for_resource(new_resource)
		self.assertIs(info.target_class, RandomString)

	def test_should_retrieve_name_of_resource_as_expected(self):
		new_resource = RandomString("MyResourceName123", length=4)
		info = self._interceptor.retrieve_creation_info_for_resource(new_resource)
		self.assertIn("MyResourceName123", info.resource_name)

	def test_should_not_retrieve_non_argument_properties(self):
		# result is the one that's being problematic as of writing this.
		new_resource = RandomString("MyResourceName", length=4)
		info = self._interceptor.retrieve_creation_info_for_resource(new_resource)
		self.assertNotIn("result", info.properties)

	def test_should_retrieve_properties_containing_required_arguments_passed(self):
		new_resource = RandomString("MyResourceName", length=4)
		info = self._interceptor.retrieve_creation_info_for_resource(new_resource)
		self.assertIn("length", info.properties)

	def test_should_retrieve_none_value_for_resource_that_was_not_intercepted(self):
		resource_mock = create_autospec(pulumi.Resource)
		random_string = RandomString("a_resource_name", length=4)
		fresh_instance = ResourceCreationInterceptor()
		fresh_instance.replace_resource_constructor(resource_mock)
		self.assertIsNone(fresh_instance.retrieve_creation_info_for_resource(random_string))

	def test_should_retrieve_properties_as_a_dictionary(self):
		# it was becoming a RandomStringArgs at one point instead.
		new_resource = RandomString("MyResourceName", length=8)
		info = self._interceptor.retrieve_creation_info_for_resource(new_resource)
		self.assertIsInstance(info.properties, dict)


class MyDynamicResourceProvider(dynamic.ResourceProvider):
	def create(self, props: dict[str, Any]) -> CreateResult:
		return CreateResult(id_="1")


class MyDynamicResource(dynamic.Resource):
	def __init__(self, resource_name: str, arbitrary_value: str):
		super().__init__(MyDynamicResourceProvider(), resource_name, {"arbitrary_value": arbitrary_value})


class TestResourceCreationInterceptorDynamicResources(ResourceCreationInterceptorTestCase):

	def test_should_retrieve_arguments_passed_to_dynamic_resources(self):
		dynamic_resource_instance = MyDynamicResource("name", arbitrary_value="123")
		info = self._interceptor.retrieve_creation_info_for_resource(dynamic_resource_instance)
		self.assertIn("arbitrary_value", info.properties)
		self.assertEqual("123", info.properties["arbitrary_value"])
