import os.path
import tempfile
import unittest
from omnislash import StackComponent
from omnislash.test_tools import FileResource
from .. import ViableFileFixture
from .. import ProgramRunnerTestCase


class TestFileResourceCreation(ProgramRunnerTestCase):

	def setUp(self):
		super().setUp()
		self._storage_temp_directory = tempfile.TemporaryDirectory()

	def test_should_create_empty_file_resource_at_given_path_as_expected(self):
		output_path = os.path.join(self._storage_temp_directory.name, "my_file.txt")
		def test_program():
			empty_file = FileResource(name="MyFile", output_path=output_path)
			stack_component = StackComponent("single_file")
			stack_component.add_resource(empty_file)

		self._program_executor.run_program(test_program)
		self.assertTrue(os.path.exists(output_path))

	def test_should_create_file_with_contents_at_path_given_to_resource_as_expected(self):
		one_file_fixture = ViableFileFixture()
		def target_program() -> None:
			filled_file = FileResource(name="MyFile", output_path=one_file_fixture.viable_one_off_path, content="1235")
			component = StackComponent("name")
			component.add_resource(filled_file)
		self._program_executor.run_program(target_program)
		one_file_fixture.assertFileContents("1235")


	def test_should_delete_empty_file_resource_at_given_path_when_removed_from_program(self):
		output_path = os.path.join(self._storage_temp_directory.name, "my_file.txt")
		def test_program():
			empty_file = FileResource(name="file", output_path=output_path)
			stack_component = StackComponent("single_file")
			stack_component.add_resource(empty_file)
		self._program_executor.run_program(test_program)
		self.assertTrue(os.path.exists(output_path))
		def emptied_program():
			pass
		self._program_executor.run_program(emptied_program)
		self.assertFalse(os.path.exists(output_path))

