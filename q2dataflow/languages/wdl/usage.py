import json
import os.path
from q2dataflow.core.signature_converter.usage import DataflowTestUsage

# DOCKER_IMG_NAME = "testq2dataflow"
DOCKER_IMG_NAME = "localhost:5000/qiime2/testq2dataflow"

class WdlTestUsage(DataflowTestUsage):
    dataflow_module_name = "q2dataflow.languages.wdl"
    params_fname = "template_params.json"
    docker_image = DOCKER_IMG_NAME
    config_fname = f"{docker_image}.config"

    def dump_input_dict(self, inputs_dict, i):
        json.dump(inputs_dict, i)

    def make_config_file(self, working_dir):
        config_str = f"""[task_runtime]
        defaults = {{
                "docker": "{self.docker_image}:latest"
            }}
        """
        config_fp = os.path.join(working_dir, self.config_fname)
        with open(config_fp, "w") as c:
            c.write(config_str)

    def get_run_commands(self):
        cmd = f"miniwdl run {self._template_fname} " \
               f"--input {self.params_fname} " \
               f"--cfg {self.config_fname}"

        work_find_and_sync_cmd = 'find . -type d -name "work" -exec rsync ' \
                                 '-av --exclude="_miniwdl*" {}/ "./" \;'

        return [cmd, work_find_and_sync_cmd]
