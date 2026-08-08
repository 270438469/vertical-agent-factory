from .errors import RuntimeExecutionError


class CapabilityResolver(object):
    def __init__(self, package, handlers):
        self.package = package
        self.handlers = handlers

    def resolve(self, capability_id):
        candidates = sorted(
            self.package.bindings_for(capability_id),
            key=lambda item: item.get("priority", 0),
            reverse=True,
        )
        for binding in candidates:
            implementation = binding.get("implementation", {})
            if binding.get("status") == "unresolved":
                continue
            if binding.get("health", "healthy") != "healthy":
                continue
            if implementation.get("protocol") != "local":
                continue
            handler_name = implementation.get("handler")
            if handler_name in self.handlers:
                return binding, self.handlers[handler_name]
        raise RuntimeExecutionError(
            "No healthy executable binding for {}".format(capability_id)
        )
