import dill
from typing import Any
from multiprocessing import Process
from multiprocessing import Queue


def execute_function_in_new_process(function, *arguments):
	communication_queue = Queue()
	serialized_function = dill.dumps(function)
	def _execute_and_send_result_back():
		deserialized_function = dill.loads(serialized_function)
		try:
			result = deserialized_function(*arguments)
		except Exception as e:
			result = e
		communication_queue.put(dill.dumps(result))
	process = Process(target=_execute_and_send_result_back)
	process.start()
	result = dill.loads(communication_queue.get())
	if isinstance(result, Exception):
		raise result
	process.kill()
	return result
