import collections
from q2dataflow.core.signature_converter.case import SignatureConverter, \
    ParamCase, BaseSimpleCollectionCase, QIIME_STR_TYPE, QIIME_BOOL_TYPE

q2cwl_prefix = "q2cwl_"
reserved_param_prefix = f"{q2cwl_prefix}reserved_"

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

# TODO: are there any cwl keywords?
_cwl_keywords_v1 = set()


class CwlParamCase(ParamCase):
    dataflow_prefix = q2cwl_prefix
    _dataflow_keywords = _cwl_keywords_v1

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

    def _make_param_dict(self, type_or_types):
        name_dict = {
            'type': type_or_types,
            'doc': self._make_doc_str(),
        }
        if self.is_optional and self.default is not None:
            name_dict['default'] = self.default

        param_dict = {
            self.name: name_dict
        }

        return param_dict

    def inputs(self):
        if self.type_name in _internal_to_cwl_type:
            cwl_type = _internal_to_cwl_type[self.type_name] + self._suffix
            param_dict = self._make_param_dict(cwl_type)
        else:
            raise Exception("Unknown type: %r" % self.type_name)

        return param_dict

    def outputs(self):
        return {}


class CwlInputCase(CwlParamCase):
    # TODO: the multiple info passed here comes from
    #  multiple=style.style is not None
    #  but historically q2cwl instead used
    #  is_array=qiime_type.name in ('List', 'Set')
    #  Can I used the former instead of the latter here?
    def __init__(self, name, spec, arg=None, type_name=_cwl_file_type,
                 is_optional=None, default=None, multiple=False):
        super().__init__(name, spec, arg, type_name, is_optional, default)
        self.multiple = multiple

    def inputs(self):
        if self.multiple:
            self._suffix = "[]"
        if self.spec and self.spec.has_default() and self.spec.default is not None:
            raise NotImplementedError("inputs with non-None default values")
        cwl_type = _cwl_file_type + self._suffix

        input_dict = {
            self.name: collections.OrderedDict([
                ('label', self.name),
                ('doc', self._make_doc_str()),
                ('type', cwl_type)
            ])
        }

        return input_dict


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
            # TODO: q2wdl/q2galaxy get the qiime types the way shown below but
            #  q2wdl does
            #        for member in qiime_type.to_ast()['members']:
            #           union_member_name = member['name']
            #  Can we use the way below instead?
            self.qtype_names = [t.name for t in self.spec.qiime_type]
        # NB: ignoring nested primitive unions, like
        # Int % Range(5, 10) | Range(15, 20)
        # since both should have to match the outside type (Int, here) ...
        # TODO Evan, right?

    def inputs(self):
        type_list = self.cwl_type_names
        if not type_list:
            type_list = []
            for union_member_name in self.qtype_names:
                curr_cwl_type = _internal_to_cwl_type[union_member_name]
                if curr_cwl_type not in type_list:
                    type_list.append(curr_cwl_type)

        # TODO: import/export inputs and outputs, which explicitly specify
        #  their file types, don't have default values.  I see no reason why
        #  they cannot or should not.
        #  This implementation WILL NOT match the current cwl implementation
        #  specifically for the import/export inputs and outputs.

        param_dict = self._make_param_dict(type_list)
        return param_dict


class CwlColumnTabularCase(CwlParamCase):
    def __init__(self, name, spec, arg=None):
        if arg is not None and type(arg) != tuple:
            raise ValueError("Unexpected type of input parameter 'arg'")
        super().__init__(name, spec, arg)

        # Note: here the synth param holds the column name
        # and the "regular" param name holds the file name
        self.synth_param_name = self.name + '_column'

    def inputs(self):
        if self.default is not None:
            raise NotImplementedError(
                "metadata columns with non-None default values")

        output_dict = {
            self.name: {
                'type': _cwl_file_type,
                'doc': self._make_doc_str(),
            },
            self.synth_param_name: {
                'type': 'string',
                'doc': 'Column name to use from %r' % self.name,
            }
        }

        return output_dict

    def args(self):
        result = {}
        if self.arg is not None:

            # expect argument to be in the form of a tuple where the first
            # element is the file name and the second is the column name
            result = {self.name: self.arg[0],
                      self.synth_param_name: self.arg[1]}

        return result


# TODO can simple collection be something >1 dimensional (like dict)?
class CwlSimpleCollectionCase(CwlParamCase, BaseSimpleCollectionCase):
    def __init__(self, name, spec, arg=None, type_name=None,
                 is_optional=None, default=None):
        super(CwlSimpleCollectionCase, self).__init__(
            name, spec, arg=arg, type_name=type_name, is_optional=is_optional,
            default=default)

        if SignatureConverter.is_union_anywhere(self.inner_type):
            self.qtype_names = [t.name for t in self.inner_type]
        else:
            self.qtype_names = [self.inner_spec.qiime_type.name]

        if len(self.qtype_names) > 1:
            raise ValueError("CwlSimpleCollectionCase does not handle collections with more than one type")

        self._suffix = '[]' + self._suffix
        self.type_name = self.qtype_names[0]


class CwlMetadataTabularCase(CwlParamCase):
    def __init__(self, name, spec, arg=None):
        if arg is not None and type(arg) != list:
            arg = arg.split()  # default split is on whitespace
        super().__init__(name, spec, arg)

    def inputs(self):
        param_dict = {
            self.name: {
                'type': [_cwl_file_type + self._suffix,
                         _cwl_file_type + '[]' + self._suffix],
                'doc': self._make_doc_str(),
            }
        }

        return param_dict


class CwlOutputCase(CwlParamCase):
    def __init__(self, name, spec, arg=None, type_name=QIIME_STR_TYPE,
                 is_optional=None, default=None):
        super().__init__(name, spec, arg, type_name, is_optional, default)

    # TODO: ask Evan: are qiime2 plugin output names *always* captured via
    # TODO: Do cwl param names need to be unique across the whole template or
    #  only within their parent?  This makes an output with the same name as
    #  the input, which may or may not be kosher ...

    # TODO: this doesn't provide output objects for any outputs to directories.
    #  CWL does support output directory objects (see cwl export tool, which
    #  has an output with type ['File', 'Directory']) but I don't know of any
    #  way to tell from an *arbitrary* qiime input string whether it represents
    #  the name of an output directory (the tools export template was created
    #  manually by a human with the knowledge that one of the input param
    #  strings specifies a directory name).
    def outputs(self):
        out_binding_str = f"$(inputs.{self.name})"
        if self.spec:
            if self.spec.qiime_type.name == 'Visualization':
                ext = '.qzv'
            else:
                ext = '.qza'
            out_binding_str = self.name + ext

        output_dict = {
            self.name: {
                'type': _cwl_file_type,
                'doc': self._make_doc_str(),
                'label': self.name,
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
            input_dict = {
                self.name: collections.OrderedDict([
                    ('doc', self._make_doc_str()),
                    ('type', self.cwl_type_names)
                ])
            }
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
                    'label': self.name,
                    'outputBinding': {'glob': '$(inputs.output_name)'}
                }
            }

        return output_dict


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
        return CwlSimpleCollectionCase(name, spec, arg)

    def get_output_case(self, name, spec, arg):
        return CwlOutputCase(name, spec, arg)
