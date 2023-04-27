# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from q2dataflow.languages.wdl.templaters.helpers import WdlSignatureConverter
from q2dataflow.core.signature_converter.case import make_tool_id


def _append_or_extend(content_holder, new_content):
    if type(new_content) is list:
        content_holder.extend(new_content)
    else:
        content_holder.append(new_content)
    return content_holder


class WdlTool:
    def __init__(self, plugin_id, action_id, tool_id):
        self.plugin_id = plugin_id
        self.action_id = action_id
        self.tool_id = tool_id
        self.wkflow_id = f"wkflw_{self.tool_id}"
        self.param_cases = []
        # self._inputs = []
        # self._inputs_w_defaults = []
        # self._inputs_w_args  = {}
        # #self._keyval_strs = []
        # self._outputs = []

    def add_param(self, param_case):
        self.param_cases.append(param_case)
        # self._inputs = _append_or_extend(self._inputs, param_case.inputs())
        # self._inputs_w_defaults = _append_or_extend(
        #     self._inputs_w_defaults, param_case.inputs(include_defaults=True))
        # self._inputs_w_args = self._inputs_w_args | param_case.inputs_w_args()
        # # self._keyval_strs = _append_or_extend(
        # #     self._keyval_strs, param_case.keyval_strs())
        # self._outputs = _append_or_extend(self._outputs, param_case.outputs())

    def _get_param_strs(self, get_inputs, include_defaults):
        param_strs = []
        for curr_param in self.param_cases:
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

    def get_input_declarations(self, delimiter="\n    "):
        result = self._get_delimited_param_str(True, False, delimiter)
        return result

    def get_input_declarations_w_defaults(self, delimiter="\n        "):
        result = ""
        input_strs = self._get_delimited_param_str(True, True, delimiter)

        if input_strs:
            result = f"""input {{
        {input_strs}
    }}"""
        return result

    def get_input_assignments(self, separator=": ", delimiter=",\n        "):
        inputs = self._get_param_strs(True, False)
        input_names_only = [x.split()[1] for x in inputs]
        input_name_pairs = [f"{x}{separator}{x}" for x in input_names_only]
        return delimiter.join(input_name_pairs)

    def get_outputs(self, delimiter="\n        "):
        result = ""
        outputs_str = self._get_delimited_param_str(False, False, delimiter)
        if outputs_str:
            result = f"""output {{
        {outputs_str}
    }}"""
        return result

    def make_input_dict(self):
        input_dict = {}
        for curr_param in self.param_cases:
            curr_input_dict = curr_param.args()
            for k, v in curr_input_dict.items():
                # val = v if type(v) != set else list(v)
                input_dict[f"{self.wkflow_id}.{k}"] = v

        return input_dict

    def make_tool_str(self):
        #munged_action_name = self.action_id.replace("_", "-")

        tool_str = f"""
version 1.0

struct {self.tool_id}_params {{
    {self.get_input_declarations()}
}}

task {self.tool_id} {{

    {self.get_input_declarations_w_defaults()}

    {self.tool_id}_params task_params = object {{
        {self.get_input_assignments()}
    }}

    command {{
        q2dataflow q2wdl run {self.plugin_id} {self.action_id} ~{{write_json(task_params)}}
    }}

    {self.get_outputs()}

}}
"""
        return tool_str

    def make_workflow_str(self):
        tool_str = self.make_tool_str()

        wrkflow_str = f"""
{tool_str}

workflow {self.wkflow_id} {{
{self.get_input_declarations_w_defaults()}

    call {self.tool_id} {{
        input: {self.get_input_assignments(separator="=", delimiter=", ")}
    }}

}}
"""

        return wrkflow_str


def make_wdltool(plugin_id, action, arguments=None):
    wdl_sig_converter = WdlSignatureConverter()
    tool_id = make_tool_id(plugin_id, action.id, replace_underscores=False)
    wdl_tool = WdlTool(plugin_id, action.id, tool_id)

    cases = wdl_sig_converter.signature_to_param_cases(
        action.signature, arguments=arguments, include_outputs=True)
    for case in cases:
        wdl_tool.add_param(case)

    return wdl_tool


def make_tool(conda_meta, plugin, action, make_workflow=True):
    wdl_tool = make_wdltool(plugin.id, action)

    if make_workflow:
        return wdl_tool.make_workflow_str()
    else:
        return wdl_tool.make_tool_str()
