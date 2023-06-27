from q2dataflow.languages.wdl.templaters.action import WdlActionTemplate
from q2dataflow.languages.wdl.templaters.helpers import WdlStrCase, \
    WdlInputCase, WdlOutputCase


# TODO ask Evan how to handle import from directories--not sure how that
#  works w cromwell?  WDL has a File input but not a Directory one
def make_builtin_import_template_str(settings, template_id):
    import_template = WdlActionTemplate("tools", "import", template_id)
    import_template.add_param(WdlStrCase("type", None, is_optional=False))
    import_template.add_param(WdlStrCase("format", None, is_optional=True, default=None))
    import_template.add_param(WdlStrCase("import_location", None, is_optional=False))
    import_template.add_param(WdlOutputCase("output_location", None, is_optional=False))

    import_template_str = import_template.make_workflow_str()
    return import_template_str


def make_builtin_export_template_str(meta, template_id):
    export_template = WdlActionTemplate("tools", "export", template_id)
    export_template.add_param(WdlInputCase("input_location", None, is_optional=False))
    export_template.add_param(WdlStrCase(
        "output_format", None, is_optional=True, default=None))
    export_template.add_param(WdlStrCase("output_location", None, is_optional=False))

    export_template_str = export_template.make_workflow_str()
    return export_template_str
