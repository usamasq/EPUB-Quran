import argparse
import glob
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "releases", "kindle-preview")


def list_epubs(epubs):
    if epubs:
        return epubs
    return sorted(glob.glob(os.path.join(PROJECT_ROOT, "releases", "*.epub")))


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Optional Kindle Previewer conversion check.\n"
            "Pass --command-template using placeholders {epub} and {out_dir}.\n"
            'Example: --command-template "\"C:/Program Files/Kindle Previewer 3/Kindle Previewer 3.exe\" '
            '-convert \"{epub}\" -output \"{out_dir}\""'
        )
    )
    parser.add_argument("--epubs", nargs="*", help="EPUB files to validate")
    parser.add_argument(
        "--command-template",
        default=os.environ.get("KINDLE_PREVIEWER_COMMAND", ""),
        help="Command template with {epub} and {out_dir} placeholders",
    )
    parser.add_argument("--require", action="store_true", help="Fail when command template is missing")
    parser.add_argument("--out-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    epubs = list_epubs(args.epubs)
    if not epubs:
        print("[FAIL] No EPUB files found for Kindle Previewer check.")
        return 1

    if not args.command_template:
        msg = "[SKIP] Kindle Previewer command template not configured."
        if args.require:
            print(msg.replace("[SKIP]", "[FAIL]"))
            return 1
        print(msg)
        return 0

    os.makedirs(args.out_dir, exist_ok=True)
    for epub_path in epubs:
        cmd = args.command_template.format(epub=epub_path, out_dir=args.out_dir)
        print(f"[INFO] Running Kindle conversion: {os.path.basename(epub_path)}")
        result = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            print(f"[FAIL] Kindle Previewer conversion failed for {epub_path}")
            return result.returncode

    print("[RESULT] Kindle Previewer conversions completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
