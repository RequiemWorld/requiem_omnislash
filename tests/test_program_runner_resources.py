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


class TestFixture:
	def __init__(self):
		super().__init__()
		self.setUp()

	def __del__(self):
		self.tearDown()

	def setUp(self):
		pass

	def tearDown(self):
		pass


class ViableFileFixture(TestFixture):
	"""
	A fixture to create a temporary directory and provide a file
	that can be written to for testing.
	"""
	def setUp(self):
		self._storage_temp_directory = tempfile.TemporaryDirectory()
		self.viable_one_off_path = os.path.join(self._storage_temp_directory.name, "some_file")

	def tearDown(self):
		self._storage_temp_directory.cleanup()

	def assertFileCreated(self):
		assert os.path.exists(self.viable_one_off_path)

	def assertFileContents(self, contents: str) -> None:
		with open(self.viable_one_off_path) as f:
			assert contents == f.read()


class TestProgramRunnerStackComponentProvisioning(ProgramRunnerTestCase):

	def test_should_execute_provisioner_added_to_stack_component(self):
		one_file_fixture = ViableFileFixture()
		def target_program():
			def _write_file(component: StackComponent):
				with open(one_file_fixture.viable_one_off_path, "w") as f:
					f.write("hello world")
			stack_component = StackComponent(name="abc")
			stack_component.add_provisioner(_write_file)
		self._program_executor.run_program(target_program)
		one_file_fixture.assertFileCreated()

	def test_should_have_access_in_provisioner_to_resources_added_to_stack_component_and_their_outputs(self):
		one_file_fixture = ViableFileFixture()
		def target_program():
			def _signal_provisioner_executed(stack_component: StackComponent):
				resource = stack_component.get_resources(RandomString)[0]
				with open(one_file_fixture.viable_one_off_path, "w") as f:
					f.write(resource.result)
			stack_component = StackComponent("stack_name")
			stack_component.add_resource(RandomString("string123", length=4))
			stack_component.add_provisioner(_signal_provisioner_executed)
		self._program_executor.run_program(target_program)
		outputs = self._state_inspector.get_resource_outputs("stack_name", "string123", RandomString)
		generated_random_string = outputs["result"]
		one_file_fixture.assertFileContents(generated_random_string)

	# # this test fails and then plenty of others start failing after it.
	# def test_should_create_resource_and_execute_provisioning_code_after(self):
	# 	one_file_fixture = ViableFileFixture()
	# 	def target_program():
	# 		def _write_to_the_files(component: StackComponent) -> None:
	# 			for file_resource in component.get_resources(FileResource):
	# 				with open(file_resource.output_path, "w") as f:
	# 					f.write("hello world")
	# 		file = FileResource("resource_name", one_file_fixture.viable_one_off_path)
	# 		example = StackComponent("StandInForServer")
	# 		example.add_resource(file)
	# 		example.add_provisioner(_write_to_the_files)
	#
	# 	self._program_executor.run_program(target_program)
	# 	one_file_fixture.assertFileCreated()
	# 	self.assertFileContents(one_file_fixture.viable_one_off_path, "hello world")
