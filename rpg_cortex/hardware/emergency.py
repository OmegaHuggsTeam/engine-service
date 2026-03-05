"""Emergency Stop - flag compartilhado para abortar operacoes."""

_emergency_stop = False


def check() -> bool:
    return _emergency_stop


def trigger():
    global _emergency_stop
    _emergency_stop = True


def reset():
    global _emergency_stop
    _emergency_stop = False
