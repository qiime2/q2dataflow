import yaml
from q2dataflow.core.signature_converter.usage import DataflowTestUsage

# class CwlTestUsageVariable(CLIUsageVariable):
#     def to_interface_name(self):
#         if hasattr(self, '_q2cli_ref'):
#             return self._q2cli_ref
# 
#         interface_name = '%s%s' % (self.name, self.ext)
#         return interface_name


class CwlTestUsage(DataflowTestUsage):
    dataflow_module_name = "q2dataflow.languages.cwl"
    params_fname = "template_params.yaml"

    def __init__(self, settings):
        super().__init__(settings=settings)
        self._working_dir = settings['working_dir']

    def get_run_commands(self):
        cmd = f"cwltool --debug --preserve-entire-environment " \
              f"--outdir {self._working_dir} " \
              f"{self._template_fname} " \
              f"{self.params_fname}"
        return [cmd]

    def dump_input_dict(self, inputs_dict, i):
        yaml.dump(inputs_dict, i)

    def make_config_file(self, working_dir):
        # cwl doesn't require a config file
        pass
