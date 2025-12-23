#!/usr/bin/env python
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# TODO:
PROTO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "protobuf"))
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "src"))
BLACKLIST_DIRS = ["demo"]


def is_blacklisted(path: str) -> bool:
    relative = os.path.relpath(path, PROTO_DIR)
    return any(relative.split(os.sep)[0] == b for b in BLACKLIST_DIRS)


def find_proto_files():
    for root, _, files in os.walk(PROTO_DIR):
        if is_blacklisted(root):
            continue
        for f in files:
            if f.endswith(".proto"):
                yield os.path.join(root, f)


def ensure_init_packages(relevant_path: str):
    """Ensure all intermediate folders have __init__.py"""
    pkg_dir = os.path.dirname(relevant_path)
    if pkg_dir.startswith(OUTPUT_DIR):
        init_path = os.path.join(pkg_dir, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write("# Auto-generated\n")


def generate_pb(proto_file: str):
    relative_path = os.path.relpath(proto_file, PROTO_DIR)
    output_subdir = os.path.join(OUTPUT_DIR, os.path.dirname(relative_path))
    os.makedirs(output_subdir, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={OUTPUT_DIR}",
        f"--pyi_out={OUTPUT_DIR}",
        f"--grpc_python_out={OUTPUT_DIR}",
        proto_file,
    ]
    print(f"[Info]  Compiling {proto_file}")
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(result.stderr.decode("utf-8"))
        sys.exit(1)

    # Generate __init__.py for all relevant directories
    base = os.path.splitext(os.path.relpath(proto_file, PROTO_DIR))[0]
    relevant_path = os.path.join(OUTPUT_DIR, base)
    ensure_init_packages(relevant_path)


def main():
    if not os.path.exists(PROTO_DIR):
        print(f"[Error] Proto directory not found: {PROTO_DIR}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    proto_files = list(find_proto_files())
    if not proto_files:
        print("[Warning]  No .proto files found.")
        return

    for proto_file in proto_files:
        generate_pb(proto_file)

    print("[Info] gRPC Python code generation complete.")


if __name__ == "__main__":
    main()
