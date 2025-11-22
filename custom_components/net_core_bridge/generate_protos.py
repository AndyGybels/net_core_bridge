#!/usr/bin/env python3
import os
import subprocess
import re
import sys
from pathlib import Path

# -------------------------------------------------------------
# Config
# -------------------------------------------------------------

# Path to .NET Core project with proto files
DOTNET_PROTO_DIR = Path("HomeAssistantCore/HomeAssistant.Core/Protos")

# Python gRPC output destination
PYTHON_OUT = Path("./clients")

# Regex to fix imports: "import xxx_pb2 as..." -> "from . import xxx_pb2"
IMPORT_FIX = re.compile(r"^import (.*_pb2) as (.*)$")


# -------------------------------------------------------------
# Helper: Run a shell command
# -------------------------------------------------------------
def run(cmd):
    print(f"[ RUN ] {' '.join(cmd)}")
    subprocess.check_call(cmd)


# -------------------------------------------------------------
# Helper: Fix Python gRPC import paths
# -------------------------------------------------------------
def fix_imports(py_file: Path):
    text = py_file.read_text()

    # Replace:   import hacore_pb2 as hacore__pb2
    # With:      from . import hacore_pb2 as hacore__pb2
    new_text = IMPORT_FIX.sub(r"from . import \1 as \2", text)

    if text != new_text:
        py_file.write_text(new_text)
        print(f"[ FIXED ] {py_file}")


# -------------------------------------------------------------
# Main
# -------------------------------------------------------------
def main():
    if not DOTNET_PROTO_DIR.exists():
        print(f"ERROR: Proto directory not found: {DOTNET_PROTO_DIR}")
        sys.exit(1)

    # Detect python executable
    python = "python3"
    if sys.platform.startswith("win"):
        python = "python"

    # Find all proto files
    protos = list(DOTNET_PROTO_DIR.glob("*.proto"))
    if not protos:
        print("No .proto files found.")
        return

    for proto in protos:
        print(f"[ GEN ] Processing {proto.name}")

        run(
            [
                python,
                "-m",
                "grpc_tools.protoc",
                f"-I{DOTNET_PROTO_DIR}",
                f"--python_out={PYTHON_OUT}",
                f"--grpc_python_out={PYTHON_OUT}",
                str(proto),
            ]
        )

    # Fix imports for Home Assistant module structure
    for file in PYTHON_OUT.glob("*_pb2.py"):
        fix_imports(file)
    for file in PYTHON_OUT.glob("*_pb2_grpc.py"):
        fix_imports(file)

    print("\n[ DONE ] Python gRPC stubs regenerated successfully!")


if __name__ == "__main__":
    main()
