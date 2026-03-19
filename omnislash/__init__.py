import abc
import copy
import json
import pulumi
from pulumi import Resource
from typing import Self
from typing import TypeVar
from typing import Callable
from dataclasses import dataclass
from .automation import StackProgramExecutor, ResourceCreationInterceptor, PulumiResourceMaterializer
from .automation import InterceptedCreationInfo
from .automation import setup_pulumi_workspace_options
from .automation import PulumiStateLoader
from .processes import execute_function_in_new_process

Provisioner = Callable[[Self], None]
TResource = TypeVar("TResource")

class StackComponent:
	_created_stack_components: list["StackComponent"] = list()
	_resource_construction_info: list["ResourceConstructionInfo"] = list()
	def __init__(self, name: str):
		self.name = name
		self._created_stack_components.append(self)
		self._created_resources: list[pulumi.Resource] = list()
		self._added_provisioners: list[Provisioner] = list()

	def add_resource(self, resource: pulumi.Resource) -> None:
		self._created_resources.append(resource)

	def add_provisioner(self, provisioner: Provisioner) -> None:
		self._added_provisioners.append(provisioner)

	def get_resources(self, resource_type: type[TResource]) -> list[TResource]:
		return [resource for resource in self._created_resources if type(resource) is resource_type]


@dataclass
class StackComponentConstructionInfo:
	name: str
	created_resources: list[InterceptedCreationInfo]
	provisioners: list[Provisioner]
	# @staticmethod
	# def from_stack_component(
	# 		stack_component: StackComponent,
	# 		resource_to_construction_info: dict[Resource, ResourceConstructionInfo]) -> None:
	# 	name = stack_component.name
	# 	created_resources = []
	# 	for resource in stack_component._created_resources:
	# 		info = ResourceConstructionInfo(resource.pulumi_resource_name, resource.__class__, resource.__props__)
	# 	raise NotImplementedError


@dataclass
class ProgramResult:
	stack_components: list[StackComponentConstructionInfo]


# TODO turn this into a public function and test it in isolation
def _run_program_get_result(program) -> ProgramResult:
	# need to replace the resource constructor so that props can be captured and logged
	interceptor = ResourceCreationInterceptor()
	interceptor.replace_resource_constructor(Resource)
	program()
	stack_component_infos: list[StackComponentConstructionInfo] = []
	for stack_component in StackComponent._created_stack_components:
		provisioners = stack_component._added_provisioners.copy()
		resource_construction_infos = []
		for resource in stack_component._created_resources:
			retrieved_resource_info = interceptor.retrieve_creation_info_for_resource(resource)
			assert retrieved_resource_info is not None, f"unable to retrieve creation info for resource {resource}"
			resource_construction_infos.append(retrieved_resource_info)
		stack_component_construction_info = StackComponentConstructionInfo(stack_component.name, resource_construction_infos, provisioners)
		stack_component_infos.append(stack_component_construction_info)
	return ProgramResult(stack_component_infos)


def _chart_program(target_program) -> ProgramResult:
	return execute_function_in_new_process(_run_program_get_result, target_program)


class SlashState:
	def __init__(self, existing_stack_names: list[str]):
		self.existing_stack_names = existing_stack_names


class SlashStateManager(abc.ABC):

	@abc.abstractmethod
	def load_state(self) -> SlashState:
		raise NotImplementedError

	@abc.abstractmethod
	def save_state(self, state: SlashState):
		raise NotImplementedError


class JSONSlashStateManager(SlashStateManager):
	def __init__(self, state_file_path: str):
		self._state_file_path = state_file_path

	def load_state(self) -> SlashState:
		with open(self._state_file_path) as f:
			fields = json.load(f)
		return SlashState(fields["existing_stack_names"])

	def save_state(self, state: SlashState):
		fields = {
			"created_stack_names": state.existing_stack_names
		}
		with open(self._state_file_path, "w") as f:
			json.dump(fields, f, indent=4)


class FakeSlashStateManager(SlashStateManager):

	def __init__(self):
		self._saved_state: SlashState | None = None
		self._failed_to_load_at_least_once = False
	def load_state(self) -> SlashState:
		if self._saved_state is None:
			self._failed_to_load_at_least_once = True
			raise Exception
		return copy.deepcopy(self._saved_state)

	def save_state(self, state: SlashState) -> None:
		self._saved_state = copy.deepcopy(state)

	def assert_state_saved(self):
		assert self._saved_state is not None, "there was never any attempt to save the state."

	def assert_failed_to_load_at_least_once(self):
		assert self._failed_to_load_at_least_once


class ProgramRunner:
	def __init__(self,
				 program_executor: StackProgramExecutor,
				 slash_state_manager: SlashStateManager,
				 pulumi_state_loader: PulumiStateLoader):
		self._program_executor = program_executor
		self._state_manager = slash_state_manager
		self._pulumi_state_loader = pulumi_state_loader

	def run_program(self, target_program: Callable) -> None:
		try:
			loaded_state = self._state_manager.load_state()
		except Exception:
			loaded_state = SlashState([])
		result = _chart_program(target_program)
		found_stack_component_names = [component.name for component in result.stack_components]
		for stack_name in loaded_state.existing_stack_names:
			if stack_name not in found_stack_component_names:
				def empty_target():
					pass
				self._program_executor.tear_down(empty_target, stack_name)
		for stack_component in result.stack_components:
			loaded_state.existing_stack_names.append(stack_component.name)
			def new_target():
				for resource in stack_component.created_resources:
					new_resource = resource.target_class(resource.resource_name, **resource.properties)
				# 	resource = resource
			self._program_executor.bring_up(new_target, stack_component.name)
			pulumi_state = self._pulumi_state_loader.load_pulumi_state(stack_component.name)
			materializer = PulumiResourceMaterializer(pulumi_state)
			def reconstruct_stack_component(creation_info: StackComponentConstructionInfo) -> StackComponent:
				component = StackComponent(name=creation_info.name)
				for resource_info in creation_info.created_resources:
					reconstructed_resource = materializer.materialize_resource(creation_info.name, resource_info.resource_name, resource_info.target_class)
					component.add_resource(reconstructed_resource)
				return component
			for provisioner in stack_component.provisioners:
				provisioner(reconstruct_stack_component(stack_component))
		self._state_manager.save_state(loaded_state)