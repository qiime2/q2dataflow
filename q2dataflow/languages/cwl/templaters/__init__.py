# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import types

from q2dataflow.languages.cwl.templaters.action import \
    make_action_template_str, store_action_template_str
from q2dataflow.languages.cwl.templaters.import_export import \
    make_builtin_import_template_str, make_builtin_export_template_str
from q2dataflow.core.signature_converter.case import make_action_template_id
#
#
BUILTIN_MAKERS = types.MappingProxyType({
    make_action_template_id('tools', 'import'): make_builtin_import_template_str,
    make_action_template_id('tools', 'export'): make_builtin_export_template_str,
})


__all__ = ['make_tool', 'make_action_template_id', 'BUILTIN_MAKERS']
