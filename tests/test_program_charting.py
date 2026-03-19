import unittest
import pulumi_random
from omnislash import _chart_program
from omnislash import StackComponent


class TestChartingStackComponentCapture(unittest.TestCase):
	def test_should_capture_name_of_only_stack_component_in_program(self):
		def target_program():
			component = StackComponent("my_stack555")
		self.assertEqual("my_stack555", _chart_program(target_program).stack_components[0].name)

	def test_should_capture_names_of_multiple_stack_components_in_program(self):
		def target_program():
			component_one = StackComponent("my_stack111")
			component_two = StackComponent("my_stack222")
		stack_components = _chart_program(target_program).stack_components
		self.assertEqual("my_stack111", stack_components[0].name)
		self.assertEqual("my_stack222", stack_components[1].name)


class TestChartingStackComponentResourceCapture(unittest.TestCase):
	def test_should_capture_name_of_only_resource_in_stack_component(self):
		def target_program():
			random_string = pulumi_random.RandomString("my_string123", length=4)
			component_one = StackComponent("my_stack111")
			component_one.add_resource(random_string)
		component = _chart_program(target_program).stack_components[0]
		self.assertEqual("my_string123", component.created_resources[0].resource_name)

	def test_should_capture_arguments_given_to_only_resource_in_stack_component(self):
		def target_program():
			random_string = pulumi_random.RandomString("random_string", length=4)
			component_one = StackComponent("my_stack111")
			component_one.add_resource(random_string)
		component = _chart_program(target_program).stack_components[0]
		self.assertEqual(4, component.created_resources[0].properties.get("length"))


class TestChartingStackComponentProvisioners(unittest.TestCase):
	def test_should_capture_very_simple_provisioner_callable(self):
		def target_program():
			stack_component = StackComponent("name123")
			stack_component.add_provisioner(lambda component: component)
		component = _chart_program(target_program).stack_components[0]
		self.assertEqual("abc", component.provisioners[0]("abc"))


class TestChartingStackComponentsAfterExternalCreation(unittest.TestCase):

	def test_should_not_capture_stack_components_created_outside_of_charting_code(self):
		bad_stack_component = StackComponent("bad_one")
		def target_program():
			good_stack_component = StackComponent("good_one")
		components = _chart_program(target_program).stack_components
		for component in components:
			self.assertNotEqual("bad_one", component.name)
