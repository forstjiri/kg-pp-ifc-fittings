"""Jediné CLI pro generování knihoven tvarovek (a volitelného náhledu)."""

import argparse
from pathlib import Path

ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--standard", choices=("kg", "pp", "all"), default="all",
        help="která knihovna (kg = EN 1401-1, pp = EN 1451-1)",
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="navíc vygenerovat mřížku vzorků do out/preview-*.ifc",
    )
    args = parser.parse_args()
    output = ROOT / "out"
    written = []
    if args.standard in ("kg", "all"):
        from kg_generator import generate_kg_library

        written.append(generate_kg_library(output / "tvarovky-EN1401-1.ifc"))
    if args.standard in ("pp", "all"):
        from pp_generator import generate_pp_library

        written.append(generate_pp_library(output / "tvarovky-EN1451-1.ifc"))
    if args.preview:
        from tools.build_preview import build_preview

        if args.standard in ("kg", "all"):
            written.append(build_preview("kg"))
        if args.standard in ("pp", "all"):
            written.append(build_preview("pp"))
    print("Hotovo:\n  " + "\n  ".join(str(path) for path in written))


if __name__ == "__main__":
    main()
