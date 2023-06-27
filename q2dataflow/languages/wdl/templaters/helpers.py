from q2dataflow.core.signature_converter.case import SignatureConverter, \
    ParamCase, BaseSimpleCollectionCase, QIIME_STR_TYPE, QIIME_BOOL_TYPE

q2wdl_prefix = "q2wdl_"
metafile_synth_param_prefix = f"{q2wdl_prefix}metafile_"
reserved_param_prefix = f"{q2wdl_prefix}reserved_"

_wdl_file_type = "File"

_internal_to_wdl_type = {
    "Int": "Int",
    "Float": "Float",
    QIIME_BOOL_TYPE: "Boolean",
    QIIME_STR_TYPE: "String",
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


class WdlParamCase(ParamCase):
    def __init__(self, name, spec, arg=None, type_name=None,
                 is_optional=None, default=None):
        super().__init__(
            name, spec, arg, type_name, is_optional, default)

        if self.name in _wdl_keywords_v1:
            # can't use this as a param name bc it is a wdl reserved word
            self.name = reserved_param_prefix + self.name

        self.synth_param_name = None

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

        if self.multiple:
            param = _make_array_input_dec(
                self.name, _wdl_file_type, self.is_optional, self.default)
        else:
            param = _make_file_input_dec(
                self.name, self.is_optional, self.default)

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

        self.qtype_names = [t.name for t in self.spec.qiime_type]
        # NB: ignoring nested primitive unions, like
        # Int % Range(5, 10) | Range(15, 20)
        # since both should have to match the outside type (Int, here) ...
        # TODO Evan, right?

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

        self.synth_param_name = f"{metafile_synth_param_prefix}{self.name}"

    def get_file_or_col_arg(self, get_col=False):
        result = None
        if self.arg is not None:
            tuple_index = int(get_col)
            result = self.arg[tuple_index]
        return result

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
            result = {self.name: self.get_file_or_col_arg(get_col=True),
                      self.synth_param_name: self.get_file_or_col_arg(
                          get_col=False)}

        return result


# TODO can simple collection be something >1 dimensional (like dict)?
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

        return _make_array_inputs(
            self.name, param_type, self.is_optional, self.default,
            include_defaults=include_defaults)

    def args(self):
        result = {}

        args = self.arg
        if type(self.arg) == set:
            args = list(self.arg)

        str_args = []
        if len(self.qtype_names) > 1:
            if args is not None:
                for curr_arg in args:
                    str_args.append(str(curr_arg))
        if len(str_args) > 0:
            args = str_args

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

    # TODO: ask Evan: are qiime2 plugin output names *always* captured via
    #  inputs parameters? If so, WDL output entries need to rename the
    #  output params: e.g., if the param that captures the output name is
    #  named "visualization", then the output param that actually holds that
    #  visualization file will need to be given a distinct name like
    #  "visualization_file" because you can't reuse the same param name for
    #  both an input and an output. This is done below.
    def outputs(self):
        file_param_name = self.name + "_file"
        dec_base = _make_file_input_dec(file_param_name, False, None)
        dec_str = f"{dec_base} = \"~{{{self.name}}}\""
        return [dec_str]


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
