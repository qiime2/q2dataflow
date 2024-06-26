# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import itertools
from qiime2.sdk.util import (interrogate_collection_type, is_semantic_type,
                             is_union, is_metadata_type,
                             is_metadata_column_type)
from qiime2.core.type.signature import ParameterSpec

QIIME_STR_TYPE = "Str"
QIIME_BOOL_TYPE = "Bool"
QIIME_COLLECTION_TYPE = "Collection"


def make_action_template_id(plugin_id, action_id, replace_underscores=True):
    if replace_underscores:
        munged_plugin_id = plugin_id.replace('_', '-')
        munged_action_id = action_id.replace('_', '-')
    else:
        munged_plugin_id = plugin_id
        munged_action_id = action_id
    return '_'.join(['qiime2',
                     munged_plugin_id,
                     munged_action_id])


def get_multiple_qtype_names(spec_qiime_type):
    qtypes_list = []
    for curr_included_type in spec_qiime_type:
        if curr_included_type.name == "":
            # NB: this happens in cases like when the current included type is
            # *itself* a combination, like a primitive union, e.g.
            # (Int % Range(5, 10) | Range(15, 20))
            raise NotImplementedError(
                f"Unable to map qiime type with members "
                f"{curr_included_type.members} but without name to type "
                f"in template language")
        qtypes_list.append(curr_included_type.name)
    return qtypes_list


def get_possibly_str_collection_args(arg, qtype_names):
    args = arg
    str_args = None

    # if there are multiple types, some languages (wdl, cwl) have
    # to punt by treating the param's variable as a string, so all
    # arguments to that variable need to be converted to strings
    if len(qtype_names) > 1:
        if arg is not None:
            if arg_is_dictlike(arg):
                str_args = {str(k): str(v) for k, v in arg.items()}
            else:
                str_args = [str(x) for x in arg]

    if str_args and len(str_args) > 0:
        args = str_args

    return args


def arg_is_dictlike(arg):
    try:
        items = arg.items()
    except (AttributeError, TypeError):
        return False
    else:
        # no exception raised--meaning this quacks like a dict
        return True


class ParamCase:
    dataflow_prefix = None  # Will be defined in child classes
    _dataflow_keywords = []  # Will be defined in child classes

    def __init__(self, name, spec, arg=None, type_name=None,
                 is_optional=None, default=None):
        super(ParamCase, self).__init__()
        self.name = name
        self.spec = spec
        self.arg = arg

        self.type_name = type_name
        if type_name is None:
            if self.spec:
                # TODO the below doesn't handle multiple qiime_types ... need
                #  something for that case like
                #  self.type_name = spec.qiime_type.fields[0].name maybe?
                self.type_name = self.spec.qiime_type.name
            else:
                # TODO: put in a warning?
                pass

        self.default = default
        self.is_optional = is_optional
        # Unless we are explicitly told this param is optional, dig for it ...
        if is_optional is None:
            if spec:
                if self.spec.has_default():
                    if self.spec.default != self.spec.NOVALUE:
                        self.is_optional = True
                        self.default = self.spec.default

        self.reserved_param_prefix = f"{self.dataflow_prefix}reserved_"

        if self.name in self._dataflow_keywords:
            # can't use this as a param name bc it is a cwl reserved word
            self.name = self.reserved_param_prefix + self.name

        self.synth_param_name = None

    def _convert_args(self, convertable_args):
        return convertable_args

    def inputs(self):
        raise NotImplementedError(self.__class__)

    def args(self):
        result = {}

        args = self.arg
        if type(self.arg) == set:
            args = list(self.arg)

        args = self._convert_args(args)

        if args is not None:
            result[self.name] = args

        return result


class NotImplementedCase(ParamCase):
    def inputs(self, **attributes):
        raise NotImplementedError(f'{self.name} has an unsupported type.')


class BaseSimpleCollectionCase(ParamCase):
    def __init__(self, name, spec, arg=None, type_name=None,
                 is_optional=None, default=None):
        super(BaseSimpleCollectionCase, self).__init__(
            name, spec, arg=arg, type_name=type_name, is_optional=is_optional,
            default=default)

        # If we have a simple collection, we only have a single field
        self.inner_type = spec.qiime_type.fields[0]
        self.inner_spec = ParameterSpec(self.inner_type, spec.view_type)

    def inputs(self):
        raise NotImplementedError("inputs")


class SignatureConverter:
    @staticmethod
    def is_union_anywhere(qiime_type):
        return is_union(qiime_type) or (
            qiime_type.predicate is not None and is_union(qiime_type.predicate))

    def get_input_case(self, name, spec, arg, multiple):
        raise NotImplementedError

    def get_str_case(self, name, spec, arg):
        raise NotImplementedError

    def get_bool_case(self, name, spec, arg):
        raise NotImplementedError

    def get_numeric_case(self, name, spec, arg):
        raise NotImplementedError

    def get_primitive_union_case(self, name, spec, arg):
        raise NotImplementedError

    def get_column_tabular_case(self, name, spec, arg):
        raise NotImplementedError

    def get_metadata_tabular_case(self, name, spec, arg):
        raise NotImplementedError

    def get_simple_collection_case(self, name, spec, arg):
        raise NotImplementedError

    def get_output_case(self, name, spec, arg):
        raise NotImplementedError

    def get_not_implemented_case(self, name, spec, arg):
        return NotImplementedCase(name, spec, arg)

    def signature_to_param_cases(self, signature, arguments=None,
                                 include_outputs=False):
        for name, spec in itertools.chain(signature.inputs.items(),
                                          signature.parameters.items()):
            if arguments is None:
                arg = None
            elif name not in arguments:
                continue
            else:
                arg = arguments[name]
            yield self._identify_arg_case(name, spec, arg)

        if include_outputs:
            for name, spec in signature.outputs.items():
                out_arg = None if arguments is None else arguments.get(name)
                yield self.get_output_case(name, spec, out_arg)

    def _identify_arg_case(self, name, spec, arg):
        style = interrogate_collection_type(spec.qiime_type)

        if is_semantic_type(spec.qiime_type):
            return self.get_input_case(
                name, spec, arg, multiple=style.style is not None)

        if style.style is None:  # not a collection
            if self.is_union_anywhere(spec.qiime_type):
                return self.get_primitive_union_case(name, spec, arg)
            elif is_metadata_type(spec.qiime_type):
                if is_metadata_column_type(spec.qiime_type):
                    return self.get_column_tabular_case(name, spec, arg)
                else:
                    return self.get_metadata_tabular_case(name, spec, arg)
            elif spec.qiime_type.name == 'Bool':
                return self.get_bool_case(name, spec, arg)
            elif spec.qiime_type.name == 'Str':
                return self.get_str_case(name, spec, arg)
            else:
                return self.get_numeric_case(name, spec, arg)

        elif style.style == 'simple':  # single type collection
            return self.get_simple_collection_case(name, spec, arg)
        elif style.style == 'monomorphic':  # multiple types, but monomorphic
            return self.get_not_implemented_case(name, spec, arg)
        elif style.style == 'composite':  # multiple types, but polymorphic
            return self.get_simple_collection_case(name, spec, arg)
        elif style.style == 'complex':  # oof
            return self.get_not_implemented_case(name, spec, arg)

        raise NotImplementedError
