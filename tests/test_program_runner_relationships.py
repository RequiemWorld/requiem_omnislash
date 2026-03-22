from pulumi_random import RandomString
from . import ViableFileFixture
from . import ProgramRunnerTestCase
from omnislash import StackComponent
from omnislash.test_tools import FileResource


class TestProgramRunnerRelationships(ProgramRunnerTestCase):

	def test_should_be_able_to_use_output_of_existing_resource_as_input_to_new_resource(self):
		viable_file_fixture = ViableFileFixture()
		def target_program() -> None:
			resource_one = RandomString("string", length=8)
			resource_two = FileResource("abc",
										output_path=viable_file_fixture.viable_one_off_path,
										content=resource_one.result)
			component = StackComponent("abcd")
			component.add_resource(resource_one)
			component.add_resource(resource_two)
		self._program_executor.run_program(target_program)
		outputs = self._state_inspector.get_resource_outputs("abcd", "string", RandomString)
		random_string_value = outputs.get("result")
		viable_file_fixture.assertFileContents(random_string_value)