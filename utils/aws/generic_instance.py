# Opinionated dict
class GenericInstance(dict):
    def __init__(
        self,
        type: str,
        id: str,
        region: str,
        name: str,
        email: str,
        state: str,
        exceptions: dict,
        tags: dict,
    ) -> None:
        self.type = type
        self.id = id
        self.region = region
        self.name = name
        self.email = email
        self.state = state
        self.exceptions = exceptions if exceptions else dict()
        self.tags = tags if tags else dict()

    # Allow dot access
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__