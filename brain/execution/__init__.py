
class LiveExecutionDisabled(RuntimeError):

    pass

class ExecutionEngine:

    def execute_live(self, *args, **kwargs):

        raise LiveExecutionDisabled(

            "Live execution is disabled in APEX Brain v1."

        )

