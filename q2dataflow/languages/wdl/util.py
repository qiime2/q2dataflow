from datetime import datetime

import qiime2


def get_extension():
    return ".wdl"


def write_tool(tool_str, filepath):
    temp_version = "0.1.0"
    tool_lines = []
    tool_lines.append(COPYRIGHT)
    tool_lines.append(
        "\nThis tool was automatically generated by:\n"
        f"    q2wdl (version: {temp_version})\n"
        "for:\n"
        f"    qiime2 (version: {qiime2.__version__})\n")

    tool_line_str = "\n".join(tool_lines)
    commented_str = "# " + "\n# ".join(tool_line_str.split("\n"))
    output_str = "\n".join([commented_str, tool_str])

    with open(filepath, 'w') as fh:
        fh.write(output_str)


COPYRIGHT = f"""
Copyright (c) {datetime.now().year}, QIIME 2 development team.

Distributed under the terms of the Modified BSD License. (SPDX: BSD-3-Clause)
"""
