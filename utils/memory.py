import json
import os

FILE = "risk0_memory.json"


def load_memory():
    if not os.path.exists(FILE):
        return {}
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_memory(data: dict):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_last_budget(user_id: int):
    mem = load_memory()
    return mem.get(str(user_id))


def set_last_budget(user_id: int, budget: float):
    mem = load_memory()
    mem[str(user_id)] = budget
    save_memory(mem)
