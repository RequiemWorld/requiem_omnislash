import pulumi
import inspect
from pulumi_random import RandomString

from omnislash import setup_pulumi_workspace_options
from my_script import pulumi_program
from pulumi.automation import create_or_select_stack

from tests import PulumiStateInspector

workspace_options = setup_pulumi_workspace_options(
	project_name="requiem_world",
	backend_directory="./backend_test",
	secret_passphrase="12343456",
	environment_variables={})




from pulumi_random import RandomString
#
# state_inspector = PulumiStateInspector("./backend_test/.pulumi/stacks/requiem_world/")
stack = create_or_select_stack("my_stack", workspace_options.project_settings.name, pulumi_program, opts=workspace_options)
stack.up()
