import abc
import copy
import json
import typing
import pulumi
from pulumi import Resource
from typing import Callable
from dataclasses import dataclass
from .framework import StackComponent, StackComponentValueReference
from .automation import StackProgramExecutor, ResourceCreationInterceptor, PulumiResourceMaterializer, RequiredOutput
from .automation import InterceptedCreationInfo
from .automation import setup_pulumi_workspace_options
from .automation import PulumiStateLoader
from .framework import Provisioner, StackComponent
from .processes import execute_function_in_new_process


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


class _StackComponentCreationInterceptor:
	def __init__(self):
		self.__original_constructor = None
		self.__captured_components: list[StackComponent] = list()

	def replace_constructor(self, clazz: type[StackComponent]):
		self.__original_constructor = clazz.__init__
		def replacement_constructor(other_self, *args, **kwargs) -> None:
			self.__original_constructor(other_self, *args, **kwargs)
			self.__captured_components.append(other_self)
		clazz.__init__ = replacement_constructor

	def retrieve_components(self) -> list[StackComponent]:
		return self.__captured_components.copy()


# TODO turn this into a public function and test it in isolation
def _run_program_get_result(program) -> ProgramResult:
	# need to replace the resource constructor so that props can be captured and logged
	interceptor = ResourceCreationInterceptor()
	interceptor.replace_resource_constructor_and_get(Resource)
	stack_component_interceptor = _StackComponentCreationInterceptor()
	stack_component_interceptor.replace_constructor(StackComponent)
	program()
	stack_component_infos: list[StackComponentConstructionInfo] = []
	for stack_component in stack_component_interceptor.retrieve_components():
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

@dataclass
class ManagedStack:
	name: str


class SuperState:

	def __init__(self, managed_stacks: list[ManagedStack]):
		self.managed_stacks = managed_stacks


class SuperStateManager(abc.ABC):

	@abc.abstractmethod
	def load_state(self) -> SuperState:
		raise NotImplementedError

	@abc.abstractmethod
	def save_state(self, state: SuperState):
		raise NotImplementedError


class JSONSuperStateManager(SuperStateManager):
	def __init__(self, state_file_path: str):
		self._state_file_path = state_file_path

	def load_state(self) -> SuperState:
		with open(self._state_file_path) as f:
			fields = json.load(f)
		return SuperState(fields["existing_stack_names"])

	def save_state(self, state: SuperState):
		fields = {
			"created_stack_names": state.existing_stack_names
		}
		with open(self._state_file_path, "w") as f:
			json.dump(fields, f, indent=4)


class FakeSuperStateManager(SuperStateManager):

	def __init__(self):
		self._saved_state: SuperState | None = None
		self._failed_to_load_at_least_once = False

	@property
	def saved_state(self) -> SuperState | None:
		return self._saved_state

	def load_state(self) -> SuperState:
		if self._saved_state is None:
			self._failed_to_load_at_least_once = True
			raise Exception
		return copy.deepcopy(self._saved_state)

	def save_state(self, state: SuperState) -> None:
		self._saved_state = copy.deepcopy(state)

	def assert_state_saved(self):
		assert self._saved_state is not None, "there was never any attempt to save the state."

	def assert_failed_to_load_at_least_once(self):
		assert self._failed_to_load_at_least_once


class _ResourceCreator:
	"""
	Handles the resource creation for resources on one stack, keeping
	track of created resources and resolving outputs and references to other stacks.
	"""
	def __init__(self, pulumi_state_loader: PulumiStateLoader):
		self._resource_map: dict[tuple[type[Resource], str], Resource] = dict()
		self._pulumi_state_loader = pulumi_state_loader

	def _resolve_required_output_value(self, required_output: RequiredOutput) -> typing.Any:  # probably pulumi.Output
		resource_with_output = self._resource_map.get((required_output.target_class, required_output.resource_name))
		output = getattr(resource_with_output, required_output.attribute_name)
		assert type(output) is pulumi.Output
		return output

	def _resolve_stack_reference_value(self, reference: StackComponentValueReference) -> typing.Any:
		stacks = self._pulumi_state_loader.load_pulumi_state(reference.stack_name).stacks
		referenced_stack_state = stacks[reference.stack_name]
		resource_state = referenced_stack_state.find_resource_with_name_and_type(
			name=reference.resource_name,
			type_=reference.resource_type)
		value_being_pointed_to = resource_state.resource_outputs[reference.property_name]
		return value_being_pointed_to

	def create_resource(self, creation_info: InterceptedCreationInfo):
		construction_kwargs = {}
		for property_name, property_value in creation_info.properties.items():
			if type(property_value) is RequiredOutput:
				resolved_value = self._resolve_required_output_value(property_value)
				construction_kwargs[property_name] = resolved_value
			elif type(property_value) is StackComponentValueReference:
				resolved_value = self._resolve_stack_reference_value(property_value)
				construction_kwargs[property_name] = resolved_value
			else:
				construction_kwargs[property_name] = property_value
		new_resource = creation_info.target_class(creation_info.resource_name, **construction_kwargs)
		self._resource_map[(creation_info.target_class, creation_info.resource_name)] = new_resource


class _ComponentLifecycleHandler:
	def __init__(self,
				 working_state: SuperState,
				 state_manager: SuperStateManager,
				 program_executor: StackProgramExecutor,
				 pulumi_state_loader: PulumiStateLoader):
		self._working_state = working_state
		self._state_manager = state_manager
		self._program_executor = program_executor
		self._pulumi_state_loader = pulumi_state_loader

	def handle_component_cleanup(self, current_components: list[StackComponentConstructionInfo]) -> None:
		"""
		Takes every component for the current program, and destroys any that
		aren't in the state from the last ones.
		"""
		def empty_program() -> None:
			pass
		found_stack_component_names = [component.name for component in current_components]
		for managed_stack in self._working_state.managed_stacks.copy():
			if managed_stack.name not in found_stack_component_names:
				self._program_executor.tear_down(empty_program, managed_stack.name)
				self._working_state.managed_stacks.remove(managed_stack)
				self._state_manager.save_state(self._working_state)

	def handle_component_lifecycle(self, component: StackComponentConstructionInfo) -> None:
		def new_target():
			resource_creator = _ResourceCreator(self._pulumi_state_loader)
			for resource_creation_info in component.created_resources:
				resource_creator.create_resource(resource_creation_info)

		self._program_executor.bring_up(new_target, component.name)
		pulumi_state = self._pulumi_state_loader.load_pulumi_state(component.name)
		materializer = PulumiResourceMaterializer(pulumi_state)
		def reconstruct_stack_component(creation_info: StackComponentConstructionInfo) -> StackComponent:
			component = StackComponent(name=creation_info.name)
			for resource_info in creation_info.created_resources:
				reconstructed_resource = materializer.materialize_resource(creation_info.name, resource_info.resource_name, resource_info.target_class)
				component.add_resource(reconstructed_resource)
			return component
		for provisioner in component.provisioners:
			provisioner(reconstruct_stack_component(component))


class ProgramRunner:
	def __init__(self,
				 program_executor: StackProgramExecutor,
				 slash_state_manager: SuperStateManager,
				 pulumi_state_loader: PulumiStateLoader):
		self._program_executor = program_executor
		self._state_manager = slash_state_manager
		self._pulumi_state_loader = pulumi_state_loader

	def run_program(self, target_program: Callable) -> None:
		try:
			loaded_state = self._state_manager.load_state()
		except Exception:
			loaded_state = SuperState([])
		component_lifecycle_handler = _ComponentLifecycleHandler(
			working_state=loaded_state,
			state_manager=self._state_manager,
			program_executor=self._program_executor,
			pulumi_state_loader=self._pulumi_state_loader)
		result = _chart_program(target_program)
		component_lifecycle_handler.handle_component_cleanup(result.stack_components)
		for stack_component in result.stack_components:
			loaded_state.managed_stacks.append(ManagedStack(name=stack_component.name))
			component_lifecycle_handler.handle_component_lifecycle(stack_component)
		self._state_manager.save_state(loaded_state)