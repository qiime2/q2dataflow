# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import click
from click.testing import CliRunner
import json

import q2dataflow.core.description_language.interface as clickin
from q2dataflow.languages.wdl.templaters.helpers import \
    q2wdl_prefix as wdl_prefix, \
    metafile_synth_param_prefix as wdl_metafile_synth_prefix, \
    reserved_param_prefix as wdl_reserved_prefix
from q2dataflow.languages.cwl.templaters.helpers import \
    q2cwl_prefix as cwl_prefix, \
    metafile_synth_param_prefix as cwl_metafile_synth_prefix, \
    reserved_param_prefix as cwl_reserved_prefix, \
    collection_keys_prefix as cwl_collection_keys_prefix
import q2dataflow.languages.wdl.util as wdl_util
import q2dataflow.languages.cwl.util as cwl_util

MODULE_NAME = "module_name"


def _make_metadata_param(curr_source, curr_col):
    if curr_source is None:
        return None

    curr_type = curr_source.split(".")[-1]
    if curr_type not in ["qza", "tsv"]:
        raise ValueError(f"Unexpected metadata type: '{curr_type}'")

    new_metadata_val = {'type': curr_type,
                        'source': curr_source,
                        'column': curr_col}
    return new_metadata_val


def _reformat_metadata_param(curr_metafile_key, params_dict,
                             metafile_synth_param_prefix):
    new_param_val = []
    curr_col = None

    curr_val = params_dict[curr_metafile_key]
    params_dict.pop(curr_metafile_key)

    curr_param = curr_metafile_key.replace(metafile_synth_param_prefix, "")
    if curr_val is None:
        new_param_val = None
    else:
        # if this is a metadata column param, can be only one metadata file
        if curr_param in params_dict:
            curr_col = params_dict[curr_param]
            params_dict.pop(curr_param)

            new_param_val = _make_metadata_param(curr_val, curr_col)
        else:
            # a metadata file param can have multiple files
            for curr_source in curr_val:
                curr_type = curr_source.split(".")[-1]
                if curr_type not in ["qza", "tsv"]:
                    raise ValueError(
                        f"Unexpected metadata type: '{curr_type}'")

                new_metadata_val = {'type': curr_type,
                                    'source': curr_source,
                                    'column': curr_col}
                new_param_val.append(new_metadata_val)
            # next metadata source

    params_dict[curr_param] = new_param_val
    return params_dict


def _reformat_collection_param(curr_collection_key, params_dict,
                               collection_keys_prefix):
    new_param_val = []

    # get the list of collection keys out of the param dict and remove it
    collection_keys = params_dict[curr_collection_key]
    params_dict.pop(curr_collection_key)

    # get the list of collection values out of the param dict
    param_name = curr_collection_key.replace(collection_keys_prefix, "")
    collection_vals = params_dict[param_name]

    if collection_keys is None and collection_vals is None:
        new_param_val = None
    else:
        if len(collection_keys) != len(collection_vals):
            raise ValueError("Collection keys and values must "
                             "be the same length")

        new_param_val = dict(zip(collection_keys, collection_vals))
    # endif

    params_dict[param_name] = new_param_val


def _reformat_special_params(params_dict, lang_prefix,
                             metadata_prefix, reserved_prefix,
                             collection_keys_prefix=None):
    # find and deal with any "special" params inserted by templating
    lang_special_keys = [x for x in params_dict.keys()
                         if x.startswith(lang_prefix)]
    for curr_key in lang_special_keys:
        if curr_key.startswith(metadata_prefix):
            _reformat_metadata_param(curr_key, params_dict, metadata_prefix)
        elif curr_key.startswith(reserved_prefix):
            native_key = curr_key.replace(reserved_prefix, "")
            params_dict[native_key] = params_dict[curr_key]
            params_dict.pop(curr_key)
        elif collection_keys_prefix is not None and \
                curr_key.startswith(collection_keys_prefix):
            _reformat_collection_param(curr_key, params_dict,
                                       collection_keys_prefix)
        else:
            raise ValueError(f"Unrecognized special prefix: '{curr_key}'")

    return params_dict


def _reformat_cwl_path_params(params_dict):
    def _reformat_cwl_param(param_obj):
        result = None
        if isinstance(param_obj, dict):
            path_val = param_obj.get("path", None)
            location_val = param_obj.get("location", None)
            if not path_val and not location_val:
                raise ValueError("Unable to parse CWL inputs containing "
                                 "nested dictionary without either 'path' or "
                                 "'location' key")

            result = path_val if path_val else location_val
        elif isinstance(param_obj, list):
            output_list = []
            for i in param_obj:
                output_list.append(_reformat_cwl_param(i))
            result = output_list
        else:
            result = param_obj

        return result

    output_dict = {}
    for k, v in params_dict.items():
        output_dict[k] = _reformat_cwl_param(v)

    return output_dict


@click.command("plugin")
@click.option('--quiet/--no-quiet', default=False)
@click.argument('plugin', type=str)
@click.argument('output', type=clickin.OUTPUT_DIR)
@click.pass_context
def _template_plugin(ctx, plugin: str, output: str, quiet: bool = False):
    clickin.plugin(
        plugin, output, ctx.obj[MODULE_NAME], quiet, settings=ctx.obj)


@click.command("builtins")
@click.option('--quiet/--no-quiet', default=False)
@click.argument('output', type=clickin.OUTPUT_DIR)
@click.pass_context
def _template_builtins(ctx, output: str, quiet: bool = False):
    clickin.builtins(output, ctx.obj[MODULE_NAME], quiet, settings=ctx.obj)


@click.command("all")
@click.option('--quiet/--no-quiet', default=False)
@click.argument('output', type=clickin.OUTPUT_DIR)
@click.pass_context
def _template_all(ctx, output: str, quiet: bool = False):
    clickin.all(output, ctx.obj[MODULE_NAME], quiet, settings=ctx.obj)


@click.group()
def root():
    pass


# Q2 plugin version
@root.command()
@click.argument('plugin', type=str)
def version(plugin):
    clickin.version(plugin)


# WDL
@root.group()
@click.version_option(wdl_util.Q2_WDL_VERSION)
@click.pass_context
def wdl(ctx):
    ctx.obj = {MODULE_NAME: "q2dataflow.languages.wdl"}


@wdl.group("template",
           short_help="Generate WDL workflow templates from available actions")
@click.pass_context
def wdl_template(ctx):
    pass


@wdl.command("run",
             help="Do not use directly: used internally by q2dataflow wdl")
@click.argument('plugin', type=str)
@click.argument('action', type=str)
@click.argument('inputs-json',
                type=click.Path(file_okay=True, dir_okay=False, exists=True))
def run_wdl(plugin: str, action: str, inputs_json):
    with open(inputs_json, 'r') as fh:
        config = json.load(fh)

    config = _reformat_special_params(
        config, wdl_prefix, wdl_metafile_synth_prefix, wdl_reserved_prefix)

    clickin.run(plugin, action, config, parse_primitives=True)


# CWL
@root.group()
@click.version_option(cwl_util.Q2_CWL_VERSION)
@click.pass_context
def cwl(ctx):
    ctx.obj = {MODULE_NAME: "q2dataflow.languages.cwl"}


@cwl.group(name="template",
           short_help="Generate CWL tool templates from available actions")
@click.pass_context
def cwl_template(ctx):
    ctx.obj["conda"] = True


@cwl.command(name="run",
             help="Do not use directly: used internally by q2dataflow cwl")
@click.argument('plugin', type=str)
@click.argument('action', type=str)
@click.argument('inputs-json',
                type=click.Path(file_okay=True, dir_okay=False, exists=True))
def run_cwl(plugin, action, inputs_json):
    # TODO: remove copy of inputs json
    # import shutil
    # shutil.copy(inputs_json, "/Users/abirmingham/Desktop/test1")

    with open(inputs_json, 'r') as fh:
        raw_inputs_json = json.load(fh)
        config = raw_inputs_json['inputs']

    config = _reformat_cwl_path_params(config)
    config = _reformat_special_params(
        config, cwl_prefix, cwl_metafile_synth_prefix, cwl_reserved_prefix,
        cwl_collection_keys_prefix)

    clickin.run(plugin, action, config, parse_primitives=True)


wdl_template.add_command(_template_plugin)
wdl_template.add_command(_template_builtins)
wdl_template.add_command(_template_all)
cwl_template.add_command(_template_plugin)
cwl_template.add_command(_template_builtins)
cwl_template.add_command(_template_all)

if __name__ == '__main__':
    # TODO: take out debugging call and put back root call
    #run_cwl(["mystery_stew", "collection_primitive_union_params_1", "/Users/abirmingham/Desktop/test1/inputs.json"])
    #run_wdl(["mystery_stew", "collection_artifact_params_1", "/Users/abirmingham/Desktop/test1/20231006_163646_wkflw_qiime2_mystery_stew_collection_artifact_params_1/call-qiime2_mystery_stew_collection_artifact_params_1/inputs.json"])
    root()
