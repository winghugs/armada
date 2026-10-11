import os
import tempfile
from pathlib import Path

# Discrete script to change the config file for the power limit daemon to pick up.


CONFIG_PATH = Path("/var/home/armada/.config/armada/power-limit.conf")
POWER_SUPPLY_PATH = Path("/sys/class/power_supply")
DEFAULT_LIMIT = 100
MIN_LIMIT = 50
MAX_LIMIT = 100
LIMIT_STEP = 5


def power_charge_limit_supported():
    try:
        batteries = [
            path
            for path in POWER_SUPPLY_PATH.iterdir()
            if "bat" in path.name.lower()
        ]
    except OSError:
        return False
    if len(batteries) != 1:
        return False

    battery_path = batteries[0]
    return all(
        (battery_path / attribute).is_file()
        for attribute in ("capacity", "constant_charge_current", "constant_charge_current_max")
    )


def power_charge_limit():
    try:
        value = int(CONFIG_PATH.read_text(encoding="utf-8").strip())
        if MIN_LIMIT <= value <= MAX_LIMIT and value % LIMIT_STEP == 0:
            return value
    except (OSError, ValueError):
        pass
    return DEFAULT_LIMIT


def set_power_charge_limit(limit):
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("power limit must be an integer")
    if not MIN_LIMIT <= limit <= MAX_LIMIT:
        raise ValueError("power limit must be from 50 to 100")

    # Round to the nearest step
    limit = ((limit + LIMIT_STEP // 2) // LIMIT_STEP) * LIMIT_STEP

    # Make the file if not yet made
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{CONFIG_PATH.name}.", dir=CONFIG_PATH.parent
    )

    # Setting permissions so no funky business
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as config_file:
            config_file.write(f"{limit}\n")
            config_file.flush()
            os.fsync(config_file.fileno())
        os.replace(temporary_path, CONFIG_PATH)
    except Exception:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise
    return limit