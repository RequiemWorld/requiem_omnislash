import os
from pulumi.automation import ProjectBackend
from pulumi.automation import select_stack, create_or_select_stack
from pulumi.automation import ProjectSettings
from pulumi.automation import LocalWorkspaceOptions
from ._interception import InterceptedCreationInfo
from ._interception import ResourceCreationInterceptor


def setup_pulumi_workspace_options(
		project_name: str,
		backend_directory: str,
		secret_passphrase: str,
		environment_variables: dict) -> LocalWorkspaceOptions:
	"""
	Tailored towards creating LocalWorkspaceOptions with a local backend out of a directory, and
	secrets stored within, encrypted with the given passphrase. Creates backend_directory when it doesn't exist.

	:param backend_directory: The directory that will contain the .pulumi directory with state, locks, etc.
	:param secret_passphrase: The password used to encrypt any secrets (this uses a local backend so they're probably stored/encrypted there).
	:param environment_variables: The environment variables that should be present when pulumi is run. (secret_passphrase will be tacked onto them as PULUMI_CONFIG_PASSPHRASE)
	"""
	os.makedirs(backend_directory, exist_ok=True)
	backend_directory_absolute_path = os.path.abspath(backend_directory)
	project_settings = ProjectSettings(
		name=project_name,
		runtime="python",
		backend=ProjectBackend(f"file://{backend_directory_absolute_path}"))
	env_vars = environment_variables.copy()
	env_vars["PULUMI_CONFIG_PASSPHRASE"] = secret_passphrase
	return LocalWorkspaceOptions(project_settings=project_settings, env_vars=env_vars)


class StackProgramExecutor:
	def __init__(self, workspace: LocalWorkspaceOptions):
		self._workspace = workspace

	def bring_up(self, target_program, stack_name: str) -> None:
		stack = create_or_select_stack(stack_name, self._workspace.project_settings.name, target_program, opts=self._workspace)
		stack.up()

	def tear_down(self, target_program, stack_name: str) -> None:
		stack = select_stack(stack_name, self._workspace.project_settings.name, target_program, opts=self._workspace)
		stack.destroy()
		stack.workspace.remove_stack(stack_name)
