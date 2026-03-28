from omnislash import StackComponent
from . import ProgramRunnerTestCase


class TestStackComponentCreationSuperState(ProgramRunnerTestCase):
	def test_should_create_managed_stack_with_right_name_in_super_state(self):
		def target_program():
			component = StackComponent("abcd")
		self._program_executor.run_program(target_program)
		self.assertEqual("abcd", self._super_state_manager.saved_state.managed_stacks[0].name)

class TestStackComponentDeletionSuperState(ProgramRunnerTestCase):

	def test_should_delete_managed_stack_for_simple_component_in_super_state(self):
		# There may be a lot to say about replacement later, but none of it to say here.
		def target_program():
			component = StackComponent("efgh")
		self._program_executor.run_program(target_program)
		self.assertEqual("efgh", self._super_state_manager.saved_state.managed_stacks[0].name)
		def empty_program():
			pass
		self._program_executor.run_program(empty_program)
		self.assertEqual([], self._super_state_manager.saved_state.managed_stacks)