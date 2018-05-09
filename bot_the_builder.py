#!/usr/bin/env python
from contextlib import contextmanager
from datetime import datetime
from subprocess import call, check_output

import fire
import os

TEMPLATE_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.sh')

@contextmanager
def dirswitch(dirpath):
    old_path = os.getcwd()
    os.chdir(dirpath)
    yield dirpath
    os.chdir(old_path)


class Builder(object):

    @staticmethod
    def _diff_files_from_master():
        git_tag = check_output(['git', 'describe', '--tags', '--abbrev=0', '--match', 'deploy-*']).decode('utf-8').strip()
        commit_hash = check_output(['git', 'rev-list', '-n', '1', git_tag]).decode('utf-8').strip()

        return [
            x for x in
            check_output(['git', 'diff', '--name-only', commit_hash, 'HEAD']).decode('utf-8').strip().split('\n')
            if x
        ]
    
    @staticmethod
    def _tag_current():
        date = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
        tag = f'deploy-{date}'
        print(f'Tagging [{tag}]...')

        Builder._cmd_exec(['git', 'tag', tag])
        Builder._cmd_exec(['git', 'push', 'origin', tag])

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
        with dirswitch(app_root):
            print('Substituting templates...')
            Builder._template_env_interpolation()

            print('Building...')

            Builder._cmd_exec(['make', 'dist'])

            print('Build complete')

            if do_cloudbuild:
                print('Found cloudbuild config, triggering cloudbuild... ')
                Builder._do_cloudbuild()
                print('cloudbuild complete')

    def fetch_dependencies(self, app_path):
        with dirswitch(app_path):
            deps = check_output([
                "go",
                "list",
                "-f",
                "'{{ .Deps }}'"
            ]).decode('utf-8').strip()

        deps = [dep for dep in deps[2:-2].split(' ') if '/' in dep]

        return deps
    
    def has_changed(self, dirpath, changed_files):
        app_dependencies = self.fetch_dependencies(dirpath)

        for somepath in changed_files:
            absFpath = os.path.abspath(somepath)

            if dirpath in absFpath:
                return True
            
            for dep in app_dependencies:
                if dep in absFpath:
                    print(f'Detected change in dependency [{dep}]')
                    return True

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

                if self.has_changed(dirpath, changed_files):
                    print(f'App in [{dirpath}] was modified since last master deploy')

                    do_cloudbuild = 'cloudbuild.yml' in filenames or 'cloudbuild.yml.template' in filenames

                    print()

                    if not dry:
                        Builder._do_deploy(dirpath, do_cloudbuild)
                        Builder._tag_current()
                else:
                    print('App has no pending changes')


if __name__ == '__main__':
    fire.Fire(Builder)
