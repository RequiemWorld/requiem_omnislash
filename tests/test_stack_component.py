import unittest
from omnislash import StackComponent
from pulumi_random import RandomId
from pulumi_random import RandomString


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
