import unittest
from omnislash import StackComponent
from pulumi_random import RandomId
from pulumi_random import RandomString
from omnislash.framework import MatchingResourceNotFound


class TestStackComponentResources(unittest.TestCase):

	def setUp(self):
		self._stack_component = StackComponent("stack_name")

	def test_should_be_able_to_get_added_resources_of_given_type(self):
		random_string_1 = RandomString("name1", length=1)
		random_string_2 = RandomString("name2", length=1)
		self._stack_component.add_resource(random_string_1)
		self._stack_component.add_resource(random_string_2)
		self.assertEqual([random_string_1, random_string_2], self._stack_component.get_resources(RandomString))

	def test_should_be_able_to_get_added_resources_only_of_given_type(self):
		random_id = RandomId("name", byte_length=4)
		random_string = RandomString("name", length=4)
		self._stack_component.add_resource(random_id)
		self._stack_component.add_resource(random_string)
		self.assertEqual([random_id], self._stack_component.get_resources(RandomId))


class TestStackComponentValueReferences(unittest.TestCase):

	def test_should_raise_matching_resource_not_found_when_trying_to_find_resource_on_empty_component(self):
		empty_component = StackComponent("abc")
		with self.assertRaises(MatchingResourceNotFound):
			empty_component.get_reference(RandomString, "123", "property")

	def test_should_raise_matching_resource_not_found_when_trying_to_find_resource_of_wrong_type_and_right_name(self):
		component = StackComponent("555")
		component.add_resource(RandomId("name", byte_length=4))
		with self.assertRaises(MatchingResourceNotFound):
			component.get_reference(RandomId, "value", "result")

	def test_should_raise_matching_resource_not_found_when_trying_to_find_resource_of_wrong_name_and_right_type(self):
		component = StackComponent("888")
		component.add_resource(RandomString("ueval", length=8))
		with self.assertRaises(MatchingResourceNotFound):
			component.get_reference(RandomString, "lavue", "result")

	def test_should_return_correct_value_reference_when_there_is_one_with_type_and_name_contained_within(self):
		component = StackComponent("123")
		component.add_resource(RandomString("string", length=4))
		reference = component.get_reference(RandomString, "string", "result")
		self.assertEqual("123", reference.stack_name)
		self.assertIs(RandomString, reference.resource_type)
		self.assertEqual("string", reference.resource_name)
		self.assertEqual("result", reference.property_name)
