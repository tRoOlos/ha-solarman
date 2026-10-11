"""Offline SG05LP3 power conversion. This tool has no live device access."""
import argparse
import importlib.util
import json
from dataclasses import asdict
from pathlib import Path
import sys

path = Path(__file__).resolve().parents[1] / "custom_components/solarman/remote_shadow.py"
spec = importlib.util.spec_from_file_location("remote_shadow", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--power-w", required=True)
    parser.add_argument("--rated-power-w", default="15000")
    args = parser.parse_args()
    try:
        result = module.preview_power(args.power_w, args.rated_power_w)
    except module.SafetyError as exc:
        parser.error(str(exc))
    print(json.dumps(asdict(result), default=str, indent=2))


if __name__ == "__main__":
    main()
