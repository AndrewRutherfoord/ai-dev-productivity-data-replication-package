from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import logging

def execute_tasks_in_parallel(tasks: list[tuple], func, handle_result: Callable):
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        future_to_task = {
            executor.submit(func, *args): args
            for args in tasks
        }
        for future in as_completed(future_to_task):
            args = future_to_task[future]
            try:
                result = future.result()
                handle_result(args, result)
            except Exception as e:
                logging.error(f"Failed for {args}: {e}")