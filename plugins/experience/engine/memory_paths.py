import os

HOME = os.path.expanduser("~")
PRODUCT_VERSION = "0.3.0"


def memory_root():
    return os.path.realpath(
        os.environ.get("DEV_MEMORY_ROOT") or os.path.join(HOME, ".local", "share", "dev-memory")
    )


def facts_root():
    return os.path.join(memory_root(), "facts")


def methods_personal_root():
    return os.path.join(memory_root(), "methods-personal")


def scratch_root():
    return os.path.join(memory_root(), "scratch")


def inbox_root():
    return os.path.join(memory_root(), "inbox")


def logs_root():
    return os.path.join(memory_root(), "logs")


def todos_root():
    return os.path.join(memory_root(), "todos")


def habits_root():
    return os.path.join(memory_root(), "habits")


def habits_index_path():
    return os.path.join(habits_root(), "index.json")


def state_path():
    return os.path.join(memory_root(), "state.json")


def index_path():
    return os.path.join(memory_root(), "index.json")


def personal_techniques_index_path():
    return os.path.join(methods_personal_root(), "index.json")


def events_path():
    return os.path.join(logs_root(), "events.jsonl")


def install_marker_path():
    return os.path.join(memory_root(), "PERSONAL_INSTALL.json")


def ensure_layout():
    for p in (
        facts_root(),
        methods_personal_root(),
        scratch_root(),
        os.path.join(inbox_root(), "facts"),
        os.path.join(inbox_root(), "methods"),
        logs_root(),
        todos_root(),
        habits_root(),
    ):
        os.makedirs(p, exist_ok=True)
    if not os.path.isfile(index_path()):
        with open(index_path(), "w", encoding="utf-8") as f:
            f.write('{"schema":1,"entries":{},"never_remind":[]}\n')
    if not os.path.isfile(personal_techniques_index_path()):
        with open(personal_techniques_index_path(), "w", encoding="utf-8") as f:
            f.write('{"schema":1,"entries":[]}\n')
    if not os.path.isfile(state_path()):
        with open(state_path(), "w", encoding="utf-8") as f:
            f.write('{"schema":1,"enabled":true}\n')
    return memory_root()


# Legacy name: prefer memory_root() / ensure_layout() for fresh values.
MEMORY_ROOT = memory_root()
