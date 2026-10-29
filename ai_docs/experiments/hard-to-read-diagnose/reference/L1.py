"""Apply the reference fix: make the parcel-profile computation depend only on
its arguments by passing the tariff's measuring rules explicitly, so cached
profiles computed under an older rate card can no longer be served.

Usage: python reference_fix.py <tree_dir>
"""

import sys
from pathlib import Path


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"expected exactly one occurrence in {path}:\n{old}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def main(tree: Path) -> None:
    dims = tree / "freightdesk" / "pricing" / "dimensions.py"
    engine = tree / "freightdesk" / "pricing" / "engine.py"

    replace(
        dims,
        "from freightdesk.pricing.tariffs import get_tariff\n",
        "",
    )
    replace(
        dims,
        'def profile_parcel(carrier: str, length_cm, width_cm, height_cm, weight_kg) -> dict:\n'
        '    """Measure one parcel for ``carrier``.\n',
        'def profile_parcel(dim_divisor, weight_step_kg, length_cm, width_cm, height_cm, weight_kg) -> dict:\n'
        '    """Measure one parcel under a tariff\'s divisor and weight step.\n',
    )
    replace(
        dims,
        "    tariff = get_tariff(carrier)\n",
        "    divisor = to_decimal(dim_divisor, \"dim_divisor\")\n"
        "    step = to_decimal(weight_step_kg, \"weight_step_kg\")\n",
    )
    replace(
        dims,
        "    dim_weight = quantize(volume / tariff.dim_divisor, \"0.01\")\n"
        "    billable = round_up_to_step(max(actual, dim_weight), tariff.weight_step_kg)\n",
        "    dim_weight = quantize(volume / divisor, \"0.01\")\n"
        "    billable = round_up_to_step(max(actual, dim_weight), step)\n",
    )
    replace(
        engine,
        "        profile = profile_parcel(\n"
        "            tariff.code, parcel.length_cm, parcel.width_cm, parcel.height_cm, parcel.weight_kg\n"
        "        )\n",
        "        profile = profile_parcel(\n"
        "            tariff.dim_divisor,\n"
        "            tariff.weight_step_kg,\n"
        "            parcel.length_cm,\n"
        "            parcel.width_cm,\n"
        "            parcel.height_cm,\n"
        "            parcel.weight_kg,\n"
        "        )\n",
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python reference_fix.py <tree_dir>")
    main(Path(sys.argv[1]))
