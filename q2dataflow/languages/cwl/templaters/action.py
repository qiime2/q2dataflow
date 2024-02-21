# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import collections
import locale
import yaml
from q2dataflow.core.signature_converter.templaters.action import \
    DataflowActionTemplate
from q2dataflow.core.signature_converter.case import make_action_template_id
from q2dataflow.languages.cwl.templaters.helpers import CwlSignatureConverter


class CwlActionTemplate(DataflowActionTemplate):
    def __init__(self, plugin_id, action_id, template_id, label, doc, settings):
        super().__init__(plugin_id, action_id, template_id)
        self._template_id = template_id
        self._settings = settings

        self._template_dict = self._root_structure()
        self._template_dict['id'] = self._template_id
        self._template_dict['label'] = label
        if doc is not None:
            self._template_dict['doc'] = doc
        # Note: cwl speaks yaml, but this is setting up an eventual argument to
        # q2dataflow.__main__.run, which take a *json* input file.
        self._template_dict['arguments'] = ['cwl', 'run',
            plugin_id.replace('-', '_'), action_id, 'inputs.json']

    def _root_structure(self):
        template_dict = collections.OrderedDict()
        template_dict['cwlVersion'] = 'v1.0'
        template_dict['class'] = 'CommandLineTool'
        template_dict['id'] = None
        template_dict['requirements'] = collections.OrderedDict()
        template_dict['label'] = None
        template_dict['doc'] = None
        template_dict['inputs'] = collections.OrderedDict()
        template_dict['baseCommand'] = 'q2dataflow'
        template_dict['arguments'] = None
        template_dict['outputs'] = collections.OrderedDict()

        template_dict['requirements'] = {
            'InitialWorkDirRequirement': {
                'listing': [
                    collections.OrderedDict([('entryname', 'inputs.json'),
                                             ('entry', '{"inputs": $(inputs)}')])
                ]
            }
        }
        requirements = self._make_requirements()
        requirements.update(template_dict['requirements'])
        template_dict['requirements'] = requirements

        return template_dict

    def _make_requirements(self):
        if "docker" in self._settings:
            docker_settings = self._settings["docker"]
            image_id = docker_settings["image_id"]
            inner_req = collections.OrderedDict()

            if docker_settings["availability"] == 'remote':
                inner_req['dockerPull'] = image_id
            inner_req['dockerImageId'] = image_id
            inner_req['dockerOutputDirectory'] = '/home/qiime2'

            req = {'DockerRequirement': inner_req}
        elif "conda" in self._settings:
            req = collections.OrderedDict()
            req['EnvVarRequirement'] = {
                'envDef': {
                    'MPLBACKEND': 'Agg',
                    'LC_ALL': '.'.join([locale.getlocale()[0], 'UTF-8'])
                }
            }
        else:
            raise ValueError("No known platform setting found")

        return req

    def add_param(self, param_case):
        self._param_cases.append(param_case)  # this is what superclass does
        self._template_dict['inputs'].update(param_case.inputs())
        self._template_dict['outputs'].update(param_case.outputs())

    def make_template_str(self):
        template_str = yaml.dump(
            self._template_dict, default_flow_style=False, indent=2)
        return template_str


# Required public functions
def make_action_template(plugin_id, action, settings, arguments=None):
    template_id = make_action_template_id(
        plugin_id, action.id, replace_underscores=False)
    cwl_template = CwlActionTemplate(
        plugin_id, action.id, template_id, action.name, action.description,
        settings)

    cwl_sig_converter = CwlSignatureConverter()
    cases = cwl_sig_converter.signature_to_param_cases(
        action.signature, arguments=arguments, include_outputs=True)
    for case in cases:
        cwl_template.add_param(case)

    return cwl_template


def make_action_template_str(plugin, action, settings):
    cwl_template = make_action_template(plugin.id, action, settings)
    return cwl_template.make_template_str()


def store_action_template_str(action_template_str, filepath):
    with open(filepath, 'w') as fh:
        fh.write('#!/usr/bin/env cwl-runner\n\n')
        fh.write(action_template_str)

    return filepath
