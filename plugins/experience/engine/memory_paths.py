import os

HOME = os.path.expanduser("~")
MEMORY_ROOT = os.path.realpath(
    os.environ.get("DEV_MEMORY_ROOT") or os.path.join(HOME, ".local", "share", "dev-memory")
)


def facts_root():
    return os.path.join(MEMORY_ROOT, "facts")


def methods_personal_root():
    return os.path.join(MEMORY_ROOT, "methods-personal")


def scratch_root():
    return os.path.join(MEMORY_ROOT, "scratch")


def inbox_root():
    return os.path.join(MEMORY_ROOT, "inbox")


def index_path():
    return os.path.join(MEMORY_ROOT, "index.json")


def ensure_layout():
    for p in (
        facts_root(),
        methods_personal_root(),
        scratch_root(),
        os.path.join(inbox_root(), "facts"),
        os.path.join(inbox_root(), "methods"),
    ):
        os.makedirs(p, exist_ok=True)
    if not os.path.isfile(index_path()):
        with open(index_path(), "w", encoding="utf-8") as f:
            f.write('{"schema":1,"entries":{},"never_remind":[]}\n')
    return MEMORY_ROOT
