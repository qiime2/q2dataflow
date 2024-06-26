import warnings
from q2dataflow.core.signature_converter.util import \
    UntestableImplementationWarning
from q2dataflow.core.signature_converter.case import SignatureConverter, \
    ParamCase, BaseSimpleCollectionCase, QIIME_STR_TYPE, QIIME_BOOL_TYPE, \
    QIIME_COLLECTION_TYPE, get_multiple_qtype_names, \
    get_possibly_str_collection_args

q2wdl_prefix = "q2wdl_"
metafile_synth_param_prefix = f"{q2wdl_prefix}metafile_"
reserved_param_prefix = f"{q2wdl_prefix}reserved_"

_wdl_file_type = "File"
_wdl_str_type = "String"

_internal_to_wdl_type = {
    "Int": "Int",
    "Float": "Float",
    "Threads": "Int",
    "Jobs": "Int",
    QIIME_BOOL_TYPE: "Boolean",
    QIIME_STR_TYPE: _wdl_str_type,
    _wdl_file_type: _wdl_file_type
}

# from https://github.com/chanzuckerberg/miniwdl/blob/06ce305b92687974cd74c835602c070d83dba1f2/WDL/_grammar.py#L262-L267
_wdl_keywords_draft2 = set("Array File Float Int Map None Pair String as call "
                           "command else false if import input left meta "
                           "object output parameter_meta right runtime "
                           "scatter task then true workflow".split(" "))
_wdl_keywords_v1 = _wdl_keywords_draft2 | set(["alias", "struct"])


def _make_input_dec_str(input_name, wdl_type,
                        is_optional, default_val):
    optional_str = "?" if is_optional and default_val is None else ""
    return f"{wdl_type}{optional_str} {input_name}"


def _make_basic_input_dec(input_name, input_internal_type,
                          is_optional, default_val):
    wdl_type = _internal_to_wdl_type[input_internal_type]
    return _make_input_dec_str(input_name, wdl_type, is_optional, default_val)


def _make_array_input_dec(input_name, input_internal_type,
                          is_optional, default_val):
    internal_wdl_type = _internal_to_wdl_type[input_internal_type]
    wdl_type = f"Array[{internal_wdl_type}]"
    return _make_input_dec_str(input_name, wdl_type, is_optional, default_val)


def _make_map_input_dec(input_name, input_internal_type,
                        is_optional, default_val):
    internal_wdl_type = _internal_to_wdl_type[input_internal_type]
    wdl_type = f"Map[{_wdl_str_type}, {internal_wdl_type}]"
    return _make_input_dec_str(input_name, wdl_type, is_optional, default_val)


def _make_file_input_dec(input_name, is_optional, default_val):
    return _make_input_dec_str(
        input_name, _wdl_file_type, is_optional, default_val)


def _make_basic_default(case_representation, has_default, default):
    default_str = ""
    if has_default and default is not None:
        default_str = f" = {default}"

    result = f"{case_representation}{default_str}"
    return result


def _make_array_inputs(name, array_inner_type, is_optional, default,
                       include_defaults=False):
    param = _make_array_input_dec(
        name, array_inner_type, is_optional, default)

    if include_defaults:
        default_str = ""
        if is_optional and default is not None:
            if type(default) == set:
                default = list(default)

            if type(default) != list:
                default = [default]

            default_rewrites = None
            if array_inner_type == QIIME_BOOL_TYPE:
                default_rewrites = [WdlBoolCase.py_to_wdl_bool_val(x) for x in default]
            elif array_inner_type in [QIIME_STR_TYPE, _wdl_file_type]:
                default_rewrites = [f"'{x}'" for x in default]

            if default_rewrites:
                default_list_str = ", ".join(default_rewrites)
                default_str = f" = [{default_list_str}]"
            else:
                default_str = f" = {default}"

        param = f"{param}{default_str}"

    return [param]


def _make_map_inputs(name, map_inner_type, is_optional, default,
                     include_defaults=False):
    param = _make_map_input_dec(name, map_inner_type, is_optional, default)

    if include_defaults:
        default_exp = ""
        if is_optional and default is not None:
            # Default values are stored as list of tuple of strings instead of
            # as a dictionary that is then converted to a string because WDL
            # requires that a boolean be represented as lower-case true or
            # false--which can't be represented in a dict except as a string,
            # which then gets quotes around it when the dict is converted to a
            # string, which WDL won't accept.
            default_rewrites = []
            for k, v in default.items():
                if map_inner_type == QIIME_BOOL_TYPE:
                    k_v = (k, str.lower(str(v)))
                elif map_inner_type in [QIIME_STR_TYPE, _wdl_file_type]:
                    k_v = (k, f"'{str(v)}'")
                else:
                    k_v = (k, v)
                # endif

                default_rewrites.append(k_v)
            # next item

            default_rewrites_str = ", ".join(
                [f"{k}: {v}" for k, v in default_rewrites])
            default_exp = f" = {{{default_rewrites_str}}}"

        param = f"{param}{default_exp}"

    return [param]


class WdlParamCase(ParamCase):
    dataflow_prefix = q2wdl_prefix
    _dataflow_keywords = _wdl_keywords_v1

    def __init__(self, name, spec, arg=None, type_name=None,
                 is_optional=None, default=None):
        super().__init__(
            name, spec, arg, type_name, is_optional, default)

        self._is_collection = (self.spec is not None and
            self.spec.qiime_type.name == QIIME_COLLECTION_TYPE)

    def _make_input_dec(self):
        return _make_basic_input_dec(
            self.name, self.type_name, self.is_optional, self.default)

    def inputs(self, include_defaults=False):
        param = self._make_input_dec()
        if include_defaults:
            param = _make_basic_default(param, self.is_optional, self.default)
        return [param]

    def args(self):
        result = {}

        args = self.arg
        if type(self.arg) == set:
            args = list(self.arg)

        if args is not None:
            result = {self.name: args}
        return result

    def outputs(self):
        return []


class WdlInputCase(WdlParamCase):
    def __init__(self, name, spec, arg=None, type_name=_wdl_file_type,
                 is_optional=None, default=None, multiple=False):
        super().__init__(
            name, spec, arg, type_name, is_optional, default)
        self.multiple = multiple

    def inputs(self, include_defaults=False):
        if self.default:
            raise NotImplementedError(
                "inputs with non-None default values")

        if self._is_collection:
            warnings.warn(UntestableImplementationWarning(
                "Unable to test Artifact Collection inputs for WDL "
                "using miniWDL"))

        # if this is a collection of inputs, represent its directory path as a
        # string (since WDL doesn't currently have a Directory type); otherwise
        # represent it as a File type
        curr_type = QIIME_STR_TYPE if self._is_collection else _wdl_file_type

        if self.multiple and not self._is_collection:
            param = _make_array_input_dec(
                self.name, curr_type, self.is_optional, self.default)
        else:
            param = _make_basic_input_dec(self.name, curr_type,
                                          self.is_optional, self.default)

        if include_defaults:
            param = _make_basic_default(param, self.is_optional, self.default)
        return [param]


class WdlStrCase(WdlParamCase):
    def __init__(self, name, spec, arg=None, is_optional=None, default=None):
        super().__init__(name, spec, arg, QIIME_STR_TYPE, is_optional, default)

    def inputs(self, include_defaults=False):
        param = self._make_input_dec()
        if include_defaults:
            default_str = ""
            if self.is_optional and self.default is not None:
                default_str = f" = \"{self.default}\""

            param = f"{param}{default_str}"

        return [param]


class WdlBoolCase(WdlParamCase):
    def __init__(self, name, spec, arg=None, is_optional=None):
        super().__init__(name, spec, arg, QIIME_BOOL_TYPE, is_optional)

    @staticmethod
    def py_to_wdl_bool_val(py_bool_val):
        return str(py_bool_val).lower()

    def inputs(self, include_defaults=False):
        param = self._make_input_dec()
        if include_defaults:
            default_str = ""
            if self.is_optional and self.default is not None:
                default_str = f" = {self.py_to_wdl_bool_val(self.default)}"

            param = f"{param}{default_str}"
        return [param]


class WdlPrimitiveUnionCase(WdlParamCase):
    def __init__(self, name, spec, arg=None):
        super().__init__(name, spec, arg)

        self.qtype_names = get_multiple_qtype_names(self.spec.qiime_type)

    def inputs(self, include_defaults=False):
        if len(self.qtype_names) > 1:
            param_type = QIIME_STR_TYPE
        else:
            param_type = self.qtype_names[0]

        param_default = self.default
        if self.is_optional and self.default is not None:
            wrapper = "'" if param_type == QIIME_STR_TYPE else ""
            param_default = f"{wrapper}{self.default}{wrapper}"

        param = _make_basic_input_dec(
            self.name, param_type, self.is_optional, param_default)
        if include_defaults:
            param = _make_basic_default(
                param, self.is_optional, param_default)

        return [param]

    def args(self):
        arg_val = self.arg
        result = {}

        # Note: for any primitive union that allows more than one type,
        # q2dataflow wdl treats its variable as a string type (see above), so
        # in this case we need to convert the arg value into a string
        if len(self.qtype_names) > 1:
            if arg_val is not None:
                arg_val = str(self.arg)

        if arg_val is not None:
            result[self.name] = arg_val

        return result


class WdlColumnTabularCase(WdlParamCase):
    def __init__(self, name, spec, arg=None):
        if arg is not None and type(arg) != tuple:
            raise ValueError("Unexpected type of input parameter 'arg'")
        super().__init__(name, spec, arg)

        # Note: here the synth param holds the file name
        # and the "regular" param name holds the column name
        self.synth_param_name = f"{metafile_synth_param_prefix}{self.name}"

    def inputs(self, include_defaults=False):
        if self.is_optional:
            if self.default is not None:
                raise NotImplementedError(
                    "metadata columns with non-None default values")

        col_input = _make_basic_input_dec(
            self.name, QIIME_STR_TYPE, self.is_optional, self.default)
        file_input = _make_file_input_dec(
            self.synth_param_name, self.is_optional, self.default)
        result = [col_input, file_input]
        return result

    def args(self):
        result = {}
        if self.arg is not None:
            # expect argument to be in the form of a tuple where the first
            # element is the file name and the second is the column name
            result = {self.synth_param_name: self.arg[0],
                      self.name: self.arg[1]}

        return result


class WdlSimpleCollectionCase(BaseSimpleCollectionCase, WdlParamCase):
    def __init__(self, name, spec, arg=None):
        super().__init__(name, spec, arg)

        if SignatureConverter.is_union_anywhere(self.inner_type):
            self.qtype_names = [t.name for t in self.inner_type]
        else:
            self.qtype_names = [self.inner_spec.qiime_type.name]

    def inputs(self, include_defaults=False):
        if len(self.qtype_names) > 1:
            param_type = QIIME_STR_TYPE
        else:
            param_type = self.qtype_names[0]

        if not self._is_collection:
            return _make_array_inputs(
                self.name, param_type, self.is_optional, self.default,
                include_defaults=include_defaults)
        else:
            return _make_map_inputs(
                self.name, param_type, self.is_optional, self.default,
                include_defaults=include_defaults)

    def args(self):
        result = {}

        args = self.arg
        if type(self.arg) == set:
            args = list(self.arg)

        args = get_possibly_str_collection_args(args, self.qtype_names)

        if args is not None:
            result[self.name] = args

        return result


class WdlMetadataTabularCase(WdlParamCase):
    def __init__(self, name, spec, arg=None):
        if arg is not None and type(arg) != list:
            arg = arg.split()  # default split is on whitespace
        super().__init__(name, spec, arg)

        mod_param_name = self.name.replace(reserved_param_prefix, "")
        self.name = f"{metafile_synth_param_prefix}{mod_param_name}"

    def inputs(self, include_defaults=False):
        return _make_array_inputs(self.name, _wdl_file_type,
                                  self.is_optional, self.default,
                                  include_defaults=include_defaults)


class WdlOutputCase(WdlParamCase):
    def __init__(self, name, spec, arg=None, type_name=QIIME_STR_TYPE,
                 is_optional=None, default=None):
        super().__init__(
            name, spec, arg, type_name, is_optional, default)

    def inputs(self, include_defaults=False):
        # TODO can outputs have defaults?
        if self.is_optional:
            raise NotImplementedError("outputs with default values")
        return [_make_basic_input_dec(self.name, QIIME_STR_TYPE, False, None)]

    def outputs(self):
        result = []
        if not self._is_collection:
            file_param_name = self.name + "_file"
            dec_base = _make_file_input_dec(file_param_name, False, None)
            dec_str = f"{dec_base} = \"~{{{self.name}}}\""
            result = [dec_str]
        return result


class WdlSignatureConverter(SignatureConverter):
    def get_input_case(self, name, spec, arg, multiple):
        return WdlInputCase(name, spec, arg, multiple=multiple)

    def get_str_case(self, name, spec, arg):
        return WdlStrCase(name, spec, arg)

    def get_bool_case(self, name, spec, arg):
        return WdlBoolCase(name, spec, arg)

    def get_numeric_case(self, name, spec, arg):
        return WdlParamCase(name, spec, arg)

    def get_primitive_union_case(self, name, spec, arg):
        return WdlPrimitiveUnionCase(name, spec, arg)

    def get_column_tabular_case(self, name, spec, arg):
        return WdlColumnTabularCase(name, spec, arg)

    def get_metadata_tabular_case(self, name, spec, arg):
        return WdlMetadataTabularCase(name, spec, arg)

    def get_simple_collection_case(self, name, spec, arg):
        return WdlSimpleCollectionCase(name, spec, arg)

    def get_output_case(self, name, spec, arg):
        return WdlOutputCase(name, spec, arg)
