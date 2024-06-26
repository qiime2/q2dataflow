# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import re
from q2dataflow.core.signature_converter.case import make_action_template_id
from q2dataflow.core.signature_converter.util import \
    get_q2_version, get_copyright
from q2dataflow.core.signature_converter.templaters.action import \
    DataflowActionTemplate
from q2dataflow.languages.wdl.util import Q2_WDL_VERSION
from q2dataflow.languages.wdl.templaters.helpers import WdlSignatureConverter


def _append_or_extend(content_holder, new_content):
    if type(new_content) is list:
        content_holder.extend(new_content)
    else:
        content_holder.append(new_content)
    return content_holder


class WdlActionTemplate(DataflowActionTemplate):
    def __init__(self, plugin_id, action_id, template_id):
        super().__init__(plugin_id, action_id, template_id)
        self._wkflow_id = f"wkflw_{self._template_id}"

    def _make_input_name(self, param_name):
        return f"{self._wkflow_id}.{param_name}"

    def _get_param_strs(self, get_inputs, include_defaults):
        param_strs = []
        for curr_param in self._param_cases:
            if get_inputs:
                curr_param_strs = curr_param.inputs(include_defaults=include_defaults)
            else:
                curr_param_strs = curr_param.outputs()
            param_strs = _append_or_extend(param_strs, curr_param_strs)

        return param_strs

    def _get_delimited_param_str(self, get_inputs, include_defaults, delimiter):
        result = ""
        param_strs = self._get_param_strs(get_inputs, include_defaults)

        if len(param_strs) > 0:
            result = delimiter.join(param_strs)

        return result

    def _get_input_declarations(self, delimiter="\n    "):
        result = self._get_delimited_param_str(True, False, delimiter)
        return result

    def _get_input_declarations_w_defaults(self, delimiter="\n        "):
        result = ""
        input_strs = self._get_delimited_param_str(True, True, delimiter)

        if input_strs:
            result = f"""input {{
        {input_strs}
    }}"""
        return result

    def _get_input_assignments(self, separator=": ", delimiter=",\n        "):
        inputs = self._get_param_strs(True, False)
        # Use a pattern that matches square brackets and their contents to
        # strip out the brackets of type info from any Map types in the params.
        # This takes a string like "String a, Map[String, Int] b" and returns
        # "String a, Map b", which we can then split on spaces to get names
        pattern = r'\[[^\]]*\]'

        input_name_pairs = []
        for curr_input_str in inputs:
            curr_stripped_input = re.sub(pattern, '', curr_input_str)
            curr_name_only = curr_stripped_input.split()[1]
            input_name_pairs.append(
                f"{curr_name_only}{separator}{curr_name_only}")

        return delimiter.join(input_name_pairs)

    def _get_outputs(self, delimiter="\n        "):
        result = ""
        outputs_str = self._get_delimited_param_str(False, False, delimiter)
        if outputs_str:
            result = f"""output {{
        {outputs_str}
    }}"""
        return result

    def _make_task_str(self):
        task_str = f"""
version 1.0

struct {self._template_id}_params {{
    {self._get_input_declarations()}
}}

task {self._template_id} {{

    {self._get_input_declarations_w_defaults()}

    {self._template_id}_params task_params = object {{
        {self._get_input_assignments()}
    }}

    command {{
        q2dataflow wdl run {self._plugin_id} {self._action_id} ~{{write_json(task_params)}}
    }}

    {self._get_outputs()}

}}
"""
        return task_str

    def _make_workflow_str(self):
        task_str = self._make_task_str()

        wrkflow_str = f"""
{task_str}

workflow {self._wkflow_id} {{
{self._get_input_declarations_w_defaults()}

    call {self._template_id} {{
        input: {self._get_input_assignments(separator="=", delimiter=", ")}
    }}

}}
"""

        return wrkflow_str

    def make_template_str(self):
        return self._make_workflow_str()


# Required public functions
def make_action_template(plugin_id, action, settings=None, arguments=None):
    wdl_sig_converter = WdlSignatureConverter()
    template_id = make_action_template_id(
        plugin_id, action.id, replace_underscores=False)
    wdl_template = WdlActionTemplate(plugin_id, action.id, template_id)

    cases = wdl_sig_converter.signature_to_param_cases(
        action.signature, arguments=arguments, include_outputs=True)
    for case in cases:
        wdl_template.add_param(case)

    return wdl_template


def make_action_template_str(plugin, action, settings=None):
    wdl_template = make_action_template(plugin.id, action, settings=settings)
    return wdl_template.make_template_str()


def store_action_template_str(action_template_str, filepath):
    temp_lines = []
    temp_lines.append(get_copyright())
    temp_lines.append(
        "\nThis template was automatically generated by:\n"
        f"    q2dataflow wdl (version: {Q2_WDL_VERSION})\n"
        "for:\n"
        f"    qiime2 (version: {get_q2_version()})\n")

    temp_line_str = "\n".join(temp_lines)
    commented_str = "# " + "\n# ".join(temp_line_str.split("\n"))
    output_str = "\n".join([commented_str, action_template_str])

    with open(filepath, 'w') as fh:
        fh.write(output_str)