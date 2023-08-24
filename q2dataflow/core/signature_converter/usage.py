import importlib
import os.path
from q2cli.core.usage import CLIUsage


class DataflowTestUsage(CLIUsage):
    dataflow_module_name = None  # Will be defined in child classes
    params_fname = ""  # Will be defined in child classes
    _dataflow_module = None

    def __init__(self, settings=None):
        super().__init__(enable_assertions=True, action_collection_size=None)
        self._settings = settings
        self._template_obj = None
        self._template_fname = ""
        if self.dataflow_module_name:
            self._dataflow_module = importlib.import_module(
                self.dataflow_module_name)

    def action(self, action, inputs, outputs):
        vars_ = super().action(action, inputs, outputs)

        self.recorder = []

        ins = inputs.map_variables(lambda v: v.to_interface_name())
        vars_dict = vars_._asdict()
        outs = {k: v.to_interface_name() for k, v in vars_dict.items()}
        action_args = {**ins, **outs}

        action_f = action.get_action()
        self._template_obj = self.make_action_template(
            action.plugin_id, action_f, self._settings, action_args)
        self._template_fname = self.make_action_template_id(
            action.plugin_id, action.action_id) + self.get_extension()

        self.recorder.append("export MYSTERY_STEW=1")
        self.recorder.append("echo $PATH")
        self.recorder.append(self.get_run_command())

        self.recorder.append(r"find . -iname '*.qza' -exec cp \{\} ./ \;")
        self.recorder.append(r"find . -iname '*.qzv' -exec cp \{\} ./ \;")

        return vars_

    def save_run_files(self, working_dir):
        # make the template file
        template_fp = os.path.join(working_dir, self._template_fname)
        template_str = self._template_obj.make_template_str()
        self.store_action_template_str(template_str, template_fp)

        # make the inputs file
        inputs_fp = os.path.join(working_dir, self.params_fname)
        inputs_dict = self._template_obj.make_input_dict()
        with open(inputs_fp, "w") as i:
            self.dump_input_dict(inputs_dict, i)

        # make the config file (if necessary)
        self.make_config_file(working_dir)

    def make_action_template(self, plugin_id, action_f, settings, action_args):
        if self._dataflow_module:
            return self._dataflow_module.make_action_template(
                plugin_id, action_f, settings=settings, arguments=action_args)
        else:
            raise NotImplementedError("Subclasses must implement this method")

    def make_action_template_id(self, plugin_id, action_id):
        if self._dataflow_module:
            return self._dataflow_module.make_action_template_id(
                plugin_id, action_id)
        else:
            raise NotImplementedError("Subclasses must implement this method")

    def get_extension(self):
        if self._dataflow_module:
            return self._dataflow_module.get_extension()
        else:
            raise NotImplementedError("Subclasses must implement this method")

    def store_action_template_str(self, template_str, template_fp):
        if self._dataflow_module:
            return self._dataflow_module.store_action_template_str(
                template_str, template_fp)
        else:
            raise NotImplementedError("Subclasses must implement this method")

    def make_config_file(self, working_dir):
        raise NotImplementedError("Subclasses must implement this method")

    def get_run_command(self):
        raise NotImplementedError("Subclasses must implement this method")

    def dump_input_dict(self, inputs_dict, inputs_fp):
        raise NotImplementedError("Subclasses must implement this method")
