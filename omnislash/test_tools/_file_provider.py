import os.path
import pulumi
from typing import Any
from pulumi.dynamic import Resource, CreateResult, DiffResult
from pulumi.dynamic import ResourceProvider


class BetterDynamicResource(Resource):
	def __init__(self, provider: ResourceProvider, name: str, **properties):
		super().__init__(provider, name, properties)


class FileProvider(ResourceProvider):

	def create(self, props: dict[str, Any]) -> CreateResult:
		output_path = props["output_path"]
		with open(output_path, "w") as f:
			content = props.get("content")
			if content is not None:
				f.write(content)

		return CreateResult(id_=output_path, outs={"output_path": output_path})

	def delete(self, _id: str, _props: dict[str, Any]) -> None:
		output_path = _props.get("output_path")
		if os.path.exists(output_path):
			os.remove(output_path)


class FileResource(BetterDynamicResource):
	output_path: pulumi.Output[str]
	def __init__(self, name: str, output_path: str, content: str = ""):
		super().__init__(FileProvider(), name, output_path=output_path, content=content)

