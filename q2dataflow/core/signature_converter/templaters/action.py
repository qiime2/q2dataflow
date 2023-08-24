class DataflowActionTemplate:
    def __init__(self, plugin_id, action_id, template_id):
        self._plugin_id = plugin_id
        self._action_id = action_id
        self._template_id = template_id
        self._param_cases = []

    def _make_input_name(self, param_name):
        return param_name

    def add_param(self, param_case):
        self._param_cases.append(param_case)

    def make_input_dict(self):
        input_dict = {}
        for curr_param in self._param_cases:
            curr_input_dict = curr_param.args()
            for k, v in curr_input_dict.items():
                # val = v if type(v) != set else list(v)
                input_dict[self._make_input_name(k)] = v

        return input_dict

    def make_template_str(self):
        raise NotImplementedError("Subclasses must implement this method")
