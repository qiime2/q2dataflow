import json
import os.path
from q2cli.core.usage import CLIUsage, CLIUsageVariable
from q2dataflow.languages.wdl.templaters.action import make_wdltool
from q2dataflow.languages.wdl.util import write_tool

DOCKER_IMG_NAME = "testq2dataflow"


class WdlTestUsageVariable(CLIUsageVariable):
    def to_interface_name(self):
        if hasattr(self, '_q2cli_ref'):
            return self._q2cli_ref

        interface_name = '%s%s' % (self.name, self.ext)
        return interface_name


class WdlTestUsage(CLIUsage):
    config_fname = f"{DOCKER_IMG_NAME}.config"
    params_json_fname = "tool_params.json"

    def __init__(self, enable_assertions=False):
        super().__init__(enable_assertions=enable_assertions,
                         action_collection_size=None)
        self._wdltool = None
        self._miniwdl_fname = ""

    def action(self, action, inputs, outputs):
        vars_ = super().action(action, inputs, outputs)

        # the downside of inheriting from CLIUsage is that it insists on
        # writing CLI-specific statements to the recorder
        self.recorder = []

        ins = inputs.map_variables(lambda v: v.to_interface_name())

        vars_dict = vars_._asdict()
        outs = {k: v.to_interface_name() for k, v in vars_dict.items()}
        action_args = {**ins, **outs}

        action_f = action.get_action()
        self._wdltool = make_wdltool(action.plugin_id, action_f, action_args)
        self._miniwdl_fname = f"{action.plugin_id}_{action.action_id}.wdl"

        self.recorder.append("export MYSTERY_STEW=1")
        self.recorder.append(f"miniwdl run {self._miniwdl_fname} "
                             f"--input {self.params_json_fname} "
                             f"--cfg {self.config_fname}")

        # move the .qza and .qzv outputs from the q2wdl run
        # (that was executed via miniwdl) up from the depths of the miniwdl
        # output structure into the current directory, for access by subsequent
        # assertion tests
        self.recorder.append(r"find . -iname '*.qza' -exec cp \{\} ./ \;")
        self.recorder.append(r"find . -iname '*.qzv' -exec cp \{\} ./ \;")

        return vars_

    def save_wdl_run_files(self, working_dir):
        wdl_fp = os.path.join(working_dir, self._miniwdl_fname)
        workflow_str = self._wdltool.make_workflow_str()
        write_tool(workflow_str, wdl_fp)

        config_str = f"""[task_runtime]
defaults = {{
        "docker": "{DOCKER_IMG_NAME}:latest"
    }}
"""
        config_fp = os.path.join(working_dir, self.config_fname)
        with open(config_fp, "w") as c:
            c.write(config_str)

        json_fp = os.path.join(working_dir, self.params_json_fname)
        miniwdl_inputs = self._wdltool.make_input_dict()
        with open(json_fp, "w") as i:
            json.dump(miniwdl_inputs, i)
