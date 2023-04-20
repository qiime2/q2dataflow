from q2dataflow.languages.wdl.templaters.action import WdlTool
from q2dataflow.languages.wdl.templaters.helpers import WdlStrCase, \
    WdlInputCase, WdlOutputCase


# TODO ask Evan how to handle import from directories--not sure how that
#  works w cromwell?  WDL has a File input but not a Directory one
def make_builtin_import_tool(meta, tool_id):
    import_tool = WdlTool("tools", "import", tool_id)
    import_tool.add_param(WdlStrCase("type", None, is_optional=False))
    import_tool.add_param(WdlStrCase("format", None, is_optional=True, default=None))
    import_tool.add_param(WdlStrCase("import_location", None, is_optional=False))
    import_tool.add_param(WdlOutputCase("output_location", None, is_optional=False))

    tool_str = import_tool.make_workflow_str()
    return tool_str


def make_builtin_export_tool(meta, tool_id):
    export_tool = WdlTool("tools", "export", tool_id)
    export_tool.add_param(WdlInputCase("input_location", None, is_optional=False))
    export_tool.add_param(WdlStrCase(
        "output_format", None, is_optional=True, default=None))
    export_tool.add_param(WdlStrCase("output_location", None, is_optional=False))

    tool_str = export_tool.make_workflow_str()
    return tool_str
