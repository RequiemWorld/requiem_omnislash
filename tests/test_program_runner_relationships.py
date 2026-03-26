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


class TestStackComponentReferenceInputs(ProgramRunnerTestCase):
	def test_should_be_able_to_use_resource_output_on_other_stack_component_in_resource_in_new_component(self):
		viable_file_fixture = ViableFileFixture()
		def target_program() -> None:
			stack_one_component = StackComponent("333")
			stack_one_component.add_resource(RandomString("string", length=4))

			random_string_value = stack_one_component.get_reference(RandomString, "string", "result")
			stack_two_component = StackComponent("444")
			stack_two_component.add_resource(FileResource("file", viable_file_fixture.viable_one_off_path, content=random_string_value))
		self._program_executor.run_program(target_program)
		string_result = self._state_inspector.get_resource_outputs("333", "string", RandomString)["result"]
		viable_file_fixture.assertFileContents(string_result)
