import pulumi
from pulumi import Resource
from dataclasses import dataclass
from pulumi_random import RandomString


@dataclass
class OutputInfo:
	target_class: type[Resource]
	resource_name: str
	attribute_name: str


output_map: dict[pulumi.Output, OutputInfo] = {}


def resolve_output_info(output) -> OutputInfo | None:
	return output_map.get(output)


original_get = pulumi.get
def replacement_get(self, output_name: str):
	target_class: type[Resource] = type(self)
	resource_name = self._name
	attribute_name = output_name
	output_object = original_get(self, output_name)
	output_map[output_object] = OutputInfo(target_class, resource_name, attribute_name)
	return output_object

pulumi.get = replacement_get
string = RandomString("abc", length=4)
print(resolve_output_info(string.result))