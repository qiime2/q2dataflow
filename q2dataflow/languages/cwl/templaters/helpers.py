from q2dataflow.core.signature_converter.case import SignatureConverter, \
    ParamCase, BaseSimpleCollectionCase, QIIME_STR_TYPE, QIIME_BOOL_TYPE, \
    QIIME_COLLECTION_TYPE, get_multiple_qtype_names, \
    get_possibly_str_collection_args, arg_is_dictlike

q2cwl_prefix = "q2cwl_"
metafile_synth_param_prefix = f"{q2cwl_prefix}metafile_"
reserved_param_prefix = f"{q2cwl_prefix}reserved_"
collection_keys_prefix = f"{q2cwl_prefix}collection_keys_"

_cwl_file_type = "File"
_cwl_dir_type = "Directory"
_internal_to_cwl_type = {
    QIIME_STR_TYPE: 'string',
    'Int': 'long',
    QIIME_BOOL_TYPE: 'boolean',
    'Float': 'double',
    'Color': 'string',
    _cwl_file_type: _cwl_file_type
}

# Apparently there are currently no reserved words in CWL and no plans for any
# (see https://github.com/common-workflow-language/common-workflow-language/issues/759 )
# but I think it does no harm to leave this here as room to grow
_cwl_keywords = set()


# Note that this method does NOT handle files that come from a remote URL,
# which would use the "location" key instead of the "path" key.  Currently only
# the mystery stew testing needs to generate argument dictionaries, and it
# is all local files, so this is fine for now.
def _make_path_arg_value(fp_or_dir, is_file):
    class_name = _cwl_file_type if is_file else _cwl_dir_type
    if type(fp_or_dir) is not str:
        result = []
        for curr_fp_or_dir in fp_or_dir:
            result.append({"class": class_name,
                           "path": curr_fp_or_dir})
    else:
        result = {"class": class_name,
                  "path": fp_or_dir}
    return result


def _make_file_or_path_arg_dict(name, arg, is_file):
    result = {}
    if arg is not None:
        path_arg_value = _make_path_arg_value(arg, is_file)
        result = {name: path_arg_value}
    return result


def _make_cwl_types_list(qtype_name_or_names):
    type_list = []

    if type(qtype_name_or_names) is str:
        qtype_name_or_names = [qtype_name_or_names]

    for curr_qtype_name in qtype_name_or_names:
        if curr_qtype_name in _internal_to_cwl_type:
            curr_cwl_type = _internal_to_cwl_type[curr_qtype_name]
        else:
            raise ValueError("Unknown qiime type: %r" % curr_qtype_name)

        if curr_cwl_type not in type_list:
            type_list.append(curr_cwl_type)

    if len(type_list) == 0:
        raise ValueError("Unable to map qiime type(s) %r to type in "
                         "template language" % qtype_name_or_names)

    return type_list


class CwlParamCase(ParamCase):
    dataflow_prefix = q2cwl_prefix
    _dataflow_keywords = _cwl_keywords

    def __init__(self, name, spec, arg=None, type_name=None,
                 is_optional=None, default=None):
        super(CwlParamCase, self).__init__(
            name, spec, arg=arg, type_name=type_name,
            is_optional=is_optional, default=default)

        self._suffix = ''
        if self.is_optional and self.default is None:
            self._suffix += '?'

    def _make_doc_str(self):
        result = None
        if self.spec and self.spec.has_description():
            result = self.spec.description
        return result

    def _make_param_dict_for_type_or_types(self, type_or_types):
        cwl_type = None
        # NB: here we are considering a list (array) of possible CWL types.
        # This is not to be confused with an array of values of a single type;
        # that is handled by the _suffix attribute.
        if type(type_or_types) is not str:
            if len(type_or_types) > 1:
                cwl_type = [x + self._suffix for x in type_or_types]
            else:
                type_or_types = type_or_types[0]

        if cwl_type is None:
            cwl_type = type_or_types + self._suffix

        name_dict = {
            'type': cwl_type,
            'doc': self._make_doc_str(),
        }
        if self.is_optional and self.default is not None:
            name_dict['default'] = self.default

        param_dict = {
            self.name: name_dict
        }

        return param_dict

    def inputs(self):
        cwl_types_list = _make_cwl_types_list(self.type_name)
        param_dict = self._make_param_dict_for_type_or_types(cwl_types_list)
        return param_dict

    def outputs(self):
        return {}


class CwlInputCase(CwlParamCase):
    def __init__(self, name, spec, arg=None, type_name=_cwl_file_type,
                 is_optional=None, default=None, multiple=False):
        super().__init__(name, spec, arg, type_name, is_optional, default)
        self.multiple = multiple
        self._is_file = self.spec.qiime_type.name != QIIME_COLLECTION_TYPE

    def inputs(self):
        if self.spec and self.spec.has_default() and self.spec.default is not None:
            raise NotImplementedError("inputs with non-None default values")

        if self._is_file:
            input_type = _cwl_file_type
            if self.multiple:
                self._suffix = "[]" + self._suffix
        else:
            input_type = _cwl_dir_type

        input_dict = self._make_param_dict_for_type_or_types(input_type)
        return input_dict

    def args(self):
        return _make_file_or_path_arg_dict(self.name, self.arg, self._is_file)


class CwlStrCase(CwlParamCase):
    def __init__(self, name, spec, arg=None, is_optional=None, default=None):
        super().__init__(name, spec, arg, QIIME_STR_TYPE, is_optional, default)


class CwlBoolCase(CwlParamCase):
    def __init__(self, name, spec, arg=None, is_optional=None):
        super().__init__(name, spec, arg, QIIME_BOOL_TYPE, is_optional)


class CwlPrimitiveUnionCase(CwlParamCase):
    def __init__(self, name, spec, arg=None, is_optional=None, default=None,
                 cwl_type_names_list=None):
        super().__init__(
            name, spec, arg, is_optional=is_optional, default=default)

        # If passing in the types directly, use cwl types instead of qiime ones
        self.cwl_type_names = cwl_type_names_list
        if not self.cwl_type_names:
            self.qtype_names = get_multiple_qtype_names(self.spec.qiime_type)

    def inputs(self):
        type_list = self.cwl_type_names
        if not type_list:
            type_list = _make_cwl_types_list(self.qtype_names)

        param_dict = self._make_param_dict_for_type_or_types(type_list)
        return param_dict


class CwlColumnTabularCase(CwlParamCase):
    def __init__(self, name, spec, arg=None):
        if arg is not None and type(arg) != tuple:
            raise ValueError("Unexpected type of input parameter 'arg'")
        super().__init__(name, spec, arg)

        # Note: here the synth param holds the file name
        # and the "regular" param name holds the column name
        self.synth_param_name = f"{metafile_synth_param_prefix}{self.name}"

    def inputs(self):
        if self.default is not None:
            raise NotImplementedError(
                "metadata columns with non-None default values")

        output_dict = {
            self.synth_param_name: {
                'type': _cwl_file_type + self._suffix,
                'doc': self._make_doc_str(),
            },
            self.name: {
                'type': 'string' + self._suffix,
                'doc': 'Column name to use from %r file' % self.name,
            }
        }

        return output_dict

    def args(self):
        result = {}
        if self.arg is not None:
            # expect argument to be in the form of a tuple where the first
            # element is the file name and the second is the column name
            file_arg_dict = _make_path_arg_value(self.arg[0], True)
            result = {self.synth_param_name: file_arg_dict,
                      self.name: self.arg[1]}
        return result


class CwlSimpleCollectionCase(CwlParamCase, BaseSimpleCollectionCase):
    def __init__(self, name, spec, arg=None, type_name=None,
                 is_optional=None, default=None):
        super(CwlSimpleCollectionCase, self).__init__(
            name, spec, arg=arg, type_name=type_name, is_optional=is_optional,
            default=default)

        if SignatureConverter.is_union_anywhere(self.inner_type):
            self.qtype_names = get_multiple_qtype_names(self.inner_type)
            if len(self.qtype_names) > 1:
                self.type_name = QIIME_STR_TYPE
            else:
                self.type_name = self.qtype_names[0]
        else:
            self.qtype_names = [self.inner_spec.qiime_type.name]
            self.type_name = self.inner_type.name

        self._suffix = '[]' + self._suffix

    def _convert_args(self, convertable_args):
        return get_possibly_str_collection_args(convertable_args, self.qtype_names)


class CwlSimpleCollectionDictCase(CwlSimpleCollectionCase, BaseSimpleCollectionCase):
    def __init__(self, name, spec, arg=None, type_name=None,
                 is_optional=None, default=None):
        super(CwlSimpleCollectionDictCase, self).__init__(
            name, spec, arg=arg, type_name=type_name, is_optional=is_optional,
            default=default)

        # if len(self.qtype_names) > 1:
        #     raise NotImplementedError("Collections of multiple types")

        # Note: here the synth param holds the array of keys
        # and the "regular" param name holds the (parallel) array of values
        self.synth_param_name = \
            f"{collection_keys_prefix}{self.name}"

    def _make_parallel_lists_from_dict(self, a_dict):
        make_vals_strs = self.type_name == QIIME_STR_TYPE

        key_strs = [str(x) for x in a_dict.keys()]
        if make_vals_strs:
            val_strs = [str(x) for x in a_dict.values()]
        else:
            val_strs = list(a_dict.values())
        return key_strs, val_strs

    def inputs(self):
        keys_dict = {
            'type': 'string' + self._suffix,
            'doc': 'keys for %r collection' % self.name,
        }

        cwl_type = _internal_to_cwl_type[self.type_name]
        doc_str = 'values for %r collection' % self.name
        main_doc_str = self._make_doc_str()
        if main_doc_str is not None:
            doc_str = main_doc_str + ".  " + doc_str
        vals_dict = {
            'type': cwl_type + self._suffix,
            'doc': doc_str
        }

        if self.is_optional and self.default is not None:
            key_strs, val_strs = self._make_parallel_lists_from_dict(
                self.default)
            keys_dict['default'] = key_strs
            vals_dict['default'] = val_strs

        param_dict = {
            self.synth_param_name: keys_dict,
            self.name: vals_dict
        }

        return param_dict

    def args(self):
        result = {}
        if self.arg is not None:
            # expect argument to be in the form of a dictionary
            key_strs, val_strs = self._make_parallel_lists_from_dict(self.arg)
            result = {self.synth_param_name: key_strs,
                      self.name: val_strs}
        return result


class CwlMetadataTabularCase(CwlParamCase):
    def __init__(self, name, spec, arg=None):
        if arg is not None and type(arg) != list:
            arg = arg.split()  # default split is on whitespace
        super().__init__(name, spec, arg)

        mod_param_name = self.name.replace(reserved_param_prefix, "")
        self.name = f"{metafile_synth_param_prefix}{mod_param_name}"

    def inputs(self):
        param_dict = self._make_param_dict_for_type_or_types(
            [_cwl_file_type, _cwl_file_type + '[]'])
        return param_dict

    def args(self):
        return _make_file_or_path_arg_dict(self.name, self.arg, True)


class CwlOutputCase(CwlParamCase):
    def __init__(self, name, spec, arg=None, type_name=QIIME_STR_TYPE,
                 is_optional=None, default=None):
        super().__init__(name, spec, arg, type_name, is_optional, default)

    def outputs(self):
        out_binding_str = f"$(inputs.{self.name})"
        type_suffix = "file"
        cwl_type = _cwl_file_type

        if self.spec.qiime_type.name == 'Collection':
            type_suffix = "dir"
            cwl_type = _cwl_dir_type

        output_dict = {
            (self.name + "_" + type_suffix): {
                'type': cwl_type,
                'doc': self._make_doc_str(),
                'outputBinding': {'glob': out_binding_str}
            }
        }

        return output_dict


# This special class is used only by the builtin's tool import and export
# cases, where it is called directly
class CwlFileAndDirCase(CwlPrimitiveUnionCase):
    def __init__(self, name, spec, arg=None, is_optional=None, default=None,
                 is_output=False):
        super().__init__(name, spec, arg, is_optional=is_optional,
                         default=default,
                         cwl_type_names_list=[_cwl_file_type, _cwl_dir_type])
        self._is_output = is_output

    def inputs(self):
        if not self._is_output:
            input_dict = self._make_param_dict_for_type_or_types(
                self.cwl_type_names)
        else:
            temp_str_case = CwlStrCase(self.name, self.spec, arg=self.arg,
                                       is_optional=self.is_optional,
                                       default=self.default)
            input_dict = temp_str_case.inputs()

        return input_dict

    def outputs(self):
        output_dict = {}
        if self._is_output:
            output_dict = {
                self.name: {
                    'type': self.cwl_type_names,
                    'doc': self._make_doc_str(),
                    'outputBinding': {'glob': '$(inputs.output_name)'}
                }
            }

        return output_dict

    def args(self):
        is_file = not arg_is_dictlike(self.arg)
        return _make_file_or_path_arg_dict(self.name, self.arg, is_file)


class CwlSignatureConverter(SignatureConverter):
    def get_input_case(self, name, spec, arg, multiple):
        return CwlInputCase(name, spec, arg, multiple=multiple)

    def get_str_case(self, name, spec, arg):
        return CwlParamCase(name, spec, arg)

    def get_bool_case(self, name, spec, arg):
        return CwlParamCase(name, spec, arg)

    def get_numeric_case(self, name, spec, arg):
        return CwlParamCase(name, spec, arg)

    def get_primitive_union_case(self, name, spec, arg):
        return CwlPrimitiveUnionCase(name, spec, arg)

    def get_column_tabular_case(self, name, spec, arg):
        return CwlColumnTabularCase(name, spec, arg)

    def get_metadata_tabular_case(self, name, spec, arg):
        return CwlMetadataTabularCase(name, spec, arg)

    def get_simple_collection_case(self, name, spec, arg):
        if spec.qiime_type.name == QIIME_COLLECTION_TYPE:
            return CwlSimpleCollectionDictCase(name, spec, arg)
        else:
            return CwlSimpleCollectionCase(name, spec, arg)

    def get_output_case(self, name, spec, arg):
        return CwlOutputCase(name, spec, arg)
