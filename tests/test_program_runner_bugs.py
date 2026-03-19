from omnislash import StackComponent
from . import ProgramRunnerTestCase


class TestRunningProgramAfterExternalStackComponentCreation(ProgramRunnerTestCase):
	# When a stack component is created outside the program (e.g. by executing a target by accident),
	# it will contaminate global state and result in the next program not constructing right.
	def test_should_be_able_to_run_program_after_stack_component_created_outside_of_it(self):
		bad_component = StackComponent("bad")
		def target_program() -> None:
			good_component = StackComponent("good")
		self._program_executor.run_program(target_program)
		self._state_inspector.assert_has_no_stack_with_name("bad")
		self._state_inspector.assert_has_stack_with_name("good")