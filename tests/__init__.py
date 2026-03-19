import os
import tempfile
import unittest
import pulumi
from omnislash import setup_pulumi_workspace_options, StackProgramExecutor, ProgramRunner, FakeSlashStateManager, \
	PulumiStateLoader
from omnislash.automation import RelevantResourceInfo, ResourceType, RelevantStackInfo


class PulumiStateInspector:
	def __init__(self, stacks_directory: str):
		"""
		:param stacks_directory: the one for the project_name like requiem_world.
		"""
		self._stacks_directory = stacks_directory

	def get_resource(self, stack_name: str, resource_name: str, resource_type: ResourceType) -> RelevantResourceInfo | None:
		stack_file_path = os.path.join(self._stacks_directory, stack_name + ".json")
		stack_info = RelevantStackInfo.from_state_json_file(stack_file_path)
		return stack_info.find_resource_with_name_and_type(resource_name, resource_type)

	def get_resource_outputs(self, stack_name: str, resource_name: str, resource_type: ResourceType) -> dict | None:
		stack_file_path = os.path.join(self._stacks_directory, stack_name + ".json")
		stack_info = RelevantStackInfo.from_state_json_file(stack_file_path)
		return stack_info.find_resource_with_name_and_type(resource_name, resource_type).resource_outputs

	def assert_has_stack_with_name(self, stack_name: str):
		stack_file_path = os.path.join(self._stacks_directory, stack_name + ".json")
		assert os.path.exists(stack_file_path), f"stack file for {stack_name} could not be found at {stack_file_path}"

	def assert_has_no_stack_with_name(self, stack_name: str):
		try:
			self.assert_has_stack_with_name(stack_name)
		except AssertionError as e:
			return
		else:
			raise AssertionError(f"stack with name {stack_name} found")

	def assert_stack_has_resource(self, stack_name: str, resource_name: str, resource_type: type[pulumi.Resource]):
		"""
		Asserts that the stack with the given name has a resource of the given type, anywhere inside of it, including
		inside of components by checking the end of the urn e.g. urn:pulumi:my_stack::requiem_world::random:index/randomId:RandomId::server_one
		"""
		resource_type_name = str(resource_type.__name__)
		stack_file_path = os.path.join(self._stacks_directory, stack_name + ".json")
		stack_info = RelevantStackInfo.from_state_json_file(stack_file_path)
		has_resource_with_type_and_name = False
		for resource in stack_info.resources:
			if resource.resource_type.endswith(resource_type_name) and resource.resource_urn.endswith(resource_name):
				has_resource_with_type_and_name = True
				break
		assert has_resource_with_type_and_name, f"stack {stack_name} doesn't have resource of type anywhere for {resource_type_name}"


class ProgramRunnerTestCase(unittest.TestCase):
	def setUp(self):
		self._temp_directory = tempfile.TemporaryDirectory()
		workspace = setup_pulumi_workspace_options(
			project_name="test_project",
			backend_directory=self._temp_directory.name,
			secret_passphrase="12345",
			environment_variables={})
		stack_executor = StackProgramExecutor(workspace)
		self._slash_state_manager = FakeSlashStateManager()
		self._project_stacks_directory_path = os.path.join(self._temp_directory.name, ".pulumi", "stacks", workspace.project_settings.name)
		self._program_executor = ProgramRunner(stack_executor, self._slash_state_manager, PulumiStateLoader(self._project_stacks_directory_path))
		self._state_inspector = PulumiStateInspector(self._project_stacks_directory_path)


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
