import unittest
from pulumi_random import RandomString
from omnislash import StackComponent
from omnislash import _chart_program, RequiredOutput
from omnislash.test_tools import FileResource
from tests import ViableFileFixture


class TestProgramChartingRelationshipCapture(unittest.TestCase):

	def test_should_capture_required_output_for_resource(self):
		viable_file_fixture = ViableFileFixture()
		def target_program() -> None:
			resource_one = RandomString("string", length=8)
			resource_two = FileResource("abc",
										output_path=viable_file_fixture.viable_one_off_path,
										content=resource_one.result)
			component = StackComponent("abcd")
			component.add_resource(resource_one)
			component.add_resource(resource_two)
		info = _chart_program(target_program)
		property_that_is_output: RequiredOutput = info.stack_components[0].created_resources[1].properties["content"]
		self.assertEqual("string", property_that_is_output.resource_name)
		self.assertEqual("result", property_that_is_output.attribute_name)
		self.assertIs(RandomString, property_that_is_output.target_class)
