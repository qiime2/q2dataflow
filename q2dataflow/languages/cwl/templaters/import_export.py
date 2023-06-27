from q2dataflow.languages.cwl.templaters.action import CwlActionTemplate
from q2dataflow.languages.cwl.templaters.helpers import CwlStrCase, \
    CwlInputCase, CwlOutputCase, CwlFileAndDirCase


def make_builtin_import_template_str(settings, template_id):
    import_template = CwlActionTemplate(
        "tools", "import", template_id, settings)
    # TODO: q2cwl makes label = "type" not "input_type"... why?
    import_template.add_param(CwlStrCase("input_type", None, is_optional=False))
    import_template.add_param(CwlStrCase(
        "input_format", None, is_optional=True, default=None))
    import_template.add_param(CwlFileAndDirCase(
        "input_data", None, label="data", is_output=False))
    import_template.add_param(CwlOutputCase(
        'output_name', None, is_optional=True, default='artifact.qza'))

    return import_template.make_template_str()


def make_builtin_export_template_str(settings, template_id):
    export_template = CwlActionTemplate(
        "tools", "export", template_id, settings)
    export_template.add_param(CwlInputCase(
        "input_artifact", None, is_optional=False))
    export_template.add_param(CwlStrCase(
        "output_format", None, is_optional=True, default=None))
    export_template.add_param(CwlFileAndDirCase(
        "output_name", None, is_optional=True, default='data', is_output=True))

    return export_template.make_template_str()
