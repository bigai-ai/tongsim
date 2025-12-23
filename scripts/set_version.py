import ast
import sys


def set_version(file_path: str, new_version: str):
    with open(file_path, encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    version_lineno = None

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "VERSION":
                    version_lineno = node.lineno
                    break

    if version_lineno is None:
        raise RuntimeError("No VERSION assignment found")

    # 更新该行内容
    lines = source.splitlines()
    lines[version_lineno - 1] = f'VERSION = "{new_version}"'

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    set_version("src/tongsim/version.py", sys.argv[1])
