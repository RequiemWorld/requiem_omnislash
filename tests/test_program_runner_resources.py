import os.path
import tempfile
from pulumi_random import RandomString
from omnislash.test_tools import FileResource
from . import ProgramRunnerTestCase
from omnislash import StackComponent


class TestProgramRunnerStackComponentCreation(ProgramRunnerTestCase):
	def test_should_create_pulumi_stack_for_each_stack_component_in_program(self):
		def target_program():
			stack_component_one = StackComponent("stack_12345")
			stack_component_two = StackComponent("stack_45678")
		self._program_executor.run_program(target_program)
		self._state_inspector.assert_has_stack_with_name("stack_12345")
		self._state_inspector.assert_has_stack_with_name("stack_45678")

	def test_should_create_pulumi_stack_for_stack_component_and_contain_resources_added(self):
		def target_program():
			stack_component_one = StackComponent("Randomness")
			stack_component_one.add_resource(RandomString(resource_name="random_1", length=4))
			stack_component_one.add_resource(RandomString(resource_name="random_2", length=4))
		self._program_executor.run_program(target_program)
		self._state_inspector.assert_stack_has_resource("Randomness", "random_1", RandomString)


class TestProgramRunnerStateResilience(ProgramRunnerTestCase):
	def test_should_create_new_slash_state_created_when_none_exists_at_time_of_running(self):
		def target_program():
			some_component = StackComponent("my_stack")
		self._program_executor.run_program(target_program)
		self._slash_state_manager.assert_state_saved()
		self._slash_state_manager.assert_failed_to_load_at_least_once()


class TestProgramRunnerStackCleanUp(ProgramRunnerTestCase):

	def test_should_delete_stack_when_stack_removed_from_program_via_empty_program(self):
		def target_program():
			stack_component_one = StackComponent("some_stack")
		def emptied_program():
			pass
		self._program_executor.run_program(target_program)
		self._state_inspector.assert_has_stack_with_name("some_stack")
		self._program_executor.run_program(emptied_program)
		self._state_inspector.assert_has_no_stack_with_name("some_stack")

	def test_should_delete_resources_in_stack_before_deleting_the_stack(self):
		temp_directory = tempfile.TemporaryDirectory()
		viable_file_path = os.path.join(temp_directory.name, "file")
		def target_program():
			stack_component_one = StackComponent("some_stack")
			stack_component_one.add_resource(FileResource("file", viable_file_path))

		def emptied_program():
			pass
		self._program_executor.run_program(target_program)
		assert os.path.exists(viable_file_path)
		self._program_executor.run_program(emptied_program)
		assert not os.path.exists(viable_file_path)
		self._state_inspector.assert_has_no_stack_with_name("some_stack")


class TestProgramRunnerStackComponentProvisioning(ProgramRunnerTestCase):
	def setUp(self):
		super().setUp()
		self._storage_temp_directory = tempfile.TemporaryDirectory()
		self._viable_one_off_path = os.path.join(self._storage_temp_directory.name, "some_file")

	def assertFileContents(self, path: str, contents: str) -> None:
		with open(path, "r") as f:
			assert contents == f.read()

	# this test fails and then plenty of others start failing after it.
	def test_should_create_resource_and_execute_provisioning_code_after(self):
		def target_program():
			def _write_to_the_files(component: StackComponent) -> None:
				for file_resource in component.get_resources(FileResource):
					with open(file_resource.output_path.get(), "w") as f:
						f.write("hello world")
			file = FileResource("resource_name", self._viable_one_off_path)
			example = StackComponent("StandInForServer")
			example.add_resource(file)
			example.add_provisioner(_write_to_the_files)
		self._program_executor.run_program(target_program)
		self.assertFileContents(self._viable_one_off_path, "hello world")
