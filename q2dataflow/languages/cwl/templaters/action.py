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
from q2dataflow.languages.cwl.templaters.helpers import CwlSignatureConverter
from q2dataflow.core.signature_converter.case import make_action_template_id


class CwlActionTemplate:
    def __init__(self, plugin, action, template_id, settings):
        self._plugin_id = plugin.id
        self._action_id = action.id
        self._template_id = template_id
        self._settings = settings

        self.template_dict = self._root_structure()
        self.template_dict['id'] = self._template_id
        self.template_dict['label'] = action.name
        self.template_dict['doc'] = action.description
        self.template_dict['arguments'] = [
            plugin.name.replace('-', '_'), action.id, 'inputs.json']

    def _root_structure(self):
        template_dict = collections.OrderedDict()
        template_dict['cwlVersion'] = 'v1.0'
        template_dict['class'] = 'CommandLineTool'
        template_dict['id'] = None
        template_dict['requirements'] = collections.OrderedDict()
        template_dict['label'] = None
        template_dict['doc'] = None
        template_dict['inputs'] = collections.OrderedDict()
        template_dict['baseCommand'] = 'q2cwl-run'
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
        self.template_dict['inputs'].update(param_case.inputs())
        self.template_dict['outputs'].update(param_case.outputs())

    def make_template_str(self):
        template_str = yaml.dump(
            self.template_dict, default_flow_style=False, indent=2)
        return template_str


def make_cwl_action_template(plugin, action, settings, arguments=None):
    template_id = make_action_template_id(
        plugin, action.id, replace_underscores=False)
    cwl_template = CwlActionTemplate(plugin, action, template_id, settings)

    cwl_sig_converter = CwlSignatureConverter()
    cases = cwl_sig_converter.signature_to_param_cases(
        action.signature, arguments=arguments, include_outputs=True)
    for case in cases:
        cwl_template.add_param(case)

    return cwl_template


def make_action_template_str(settings, plugin, action):
    cwl_template = make_cwl_action_template(plugin.id, action, settings)
    return cwl_template.make_template_str()


def store_action_template_str(action_template_str, filepath):
    with open(filepath, 'w') as fh:
        fh.write('#!/usr/bin/env cwl-runner\n\n')
        fh.write(action_template_str)

    return filepath
