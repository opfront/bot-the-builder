#!/usr/bin/env python
from subprocess import call, check_output

import fire
import os

TEMPLATE_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.sh')


class Builder(object):

    @staticmethod
    def _diff_files_from_master():
        git_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf-8').strip()

        return [
            x for x in
            check_output(['git', 'diff', '--name-only', f'master...{git_branch}']).decode('utf-8').strip().split('\n')
            if x
        ]

    @staticmethod
    def _cmd_exec(cmd, silent=True):

        if silent:
            with open(os.devnull, 'w') as fnull:
                status = call(cmd, stdout=fnull)
        else:
            status = call(cmd)

        if status != 0:
            # TODO: Retrieve cmd stdout/stderr
            raise OSError(f"an error ({status})  occured while running command {cmd[0]}")

    @staticmethod
    def _do_cloudbuild():
        Builder._cmd_exec([
            'gcloud',
            'container',
            'builds',
            'submit',
            '--config',
            'cloudbuild.yml',
        ])

    @staticmethod
    def _template_env_interpolation():
        filenames = os.listdir('.')

        for f in filenames:
            if f.endswith('.template'):
                new_filename = f.replace('.template', '')
                print(f'Substituting [{f}] -> [{new_filename}]')
                Builder._cmd_exec([TEMPLATE_SCRIPT, f, new_filename])

    @staticmethod
    def _do_deploy(app_root, do_cloudbuild):
        current_dir = os.getcwd()

        os.chdir(app_root)

        print('Substituting templates...')
        Builder._template_env_interpolation()

        print('Building...')

        Builder._cmd_exec(['make', 'dist'])

        print('Build complete')

        if do_cloudbuild:
            print('Found cloudbuild config, triggering cloudbuild... ')
            Builder._do_cloudbuild()
            print('cloudbuild complete')

        os.chdir(current_dir)

    def all(self, path=".", dry=False):
        # TODO: Check that path is in a git repo

        if dry:
            print('Dry run')

        changed_files = Builder._diff_files_from_master()

        abs_path = os.path.abspath(path)
        print(f"Looking for apps from [{abs_path}] ...")

        for (dirpath, dirnames, filenames) in os.walk(abs_path):
            if 'Dockerfile' in filenames and 'Makefile' in filenames:
                print(f'Found a deployable app at [{dirpath}]')

                if any([dirpath in os.path.abspath(somepath) for somepath in changed_files]):
                    print(f'App in [{dirpath}] was modified since last master deploy')

                    do_cloudbuild = 'cloudbuild.yml' in filenames or 'cloudbuild.yml.template' in filenames

                    print()

                    if not dry:
                        Builder._do_deploy(dirpath, do_cloudbuild)
                else:
                    print('App has no pending changes')


if __name__ == '__main__':
    fire.Fire(Builder)
