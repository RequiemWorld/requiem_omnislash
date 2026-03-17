from omnislash import StackComponent
from omnislash.test_tools import FileResource
from pulumi_random import RandomId, RandomString


def pulumi_program() -> None:
	stack_component_one = StackComponent("Randomness")
	# this won't dill.dumps right -> RandomString(name="random_1", length=4)
	stack_component_one.add_resource(FileResource("abc", "my_output.txt"))

def finally_atomic_resources():
	pass

pulumi_program()