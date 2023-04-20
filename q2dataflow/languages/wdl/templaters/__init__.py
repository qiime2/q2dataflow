# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import types

from q2dataflow.languages.wdl.templaters.action import make_tool
from q2dataflow.languages.wdl.templaters.import_export import \
    make_builtin_import_tool, make_builtin_export_tool
from q2dataflow.core.signature_converter.case import make_tool_id
#
#
BUILTIN_MAKERS = types.MappingProxyType({
    make_tool_id('tools', 'import'): make_builtin_import_tool,
    make_tool_id('tools', 'export'): make_builtin_export_tool,
})


__all__ = ['make_tool', 'make_tool_id', 'BUILTIN_MAKERS']
