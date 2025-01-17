#!/usr/bin/env python
from paste.script import command
from paste.script import create_distro
from paste.script import entrypoints
import contextlib
import io
import os
import re
import shutil
import six
import sys
import tempfile
import textwrap
import unittest

PY2_ENTRY_POINTS=textwrap.dedent('''
    14 entry point groups found:
    [console_scripts]
      When a package is installed, any entry point listed here will be
      turned into a command-line script.
    [distutils.commands]
      This will add a new command when running ``python setup.py entry-
      point-name`` if the package uses setuptools.
    [distutils.setup_keywords]
      This adds a new keyword to setup.py's setup() function, and a
      validator to validate the value.
    [egg_info.writers]
      This adds a new writer that creates files in the PkgName.egg-info/
      directory.
    [paste.app_factory]
    [paste.composite_factory]
    [paste.entry_point_description]
      This is an entry point that describes other entry points.
    [paste.filter_app_factory]
    [paste.global_paster_command]
      Entry point that adds a command to the ``paster`` script globally.
    [paste.paster_command]
      Entry point that adds a command to the ``paster`` script to a
      project that has specifically enabled the command.
    [paste.paster_create_template]
      Entry point for creating the file layout for a new project from a
      template.
    [paste.server_runner]
    [setuptools.finalize_distribution_options]
    [setuptools.installation]
''')

PY3_ENTRY_POINTS=textwrap.dedent('''
    13 entry point groups found:
    [console_scripts]
      When a package is installed, any entry point listed here will be
      turned into a command-line script.
    [distutils.commands]
      This will add a new command when running ``python setup.py entry-
      point-name`` if the package uses setuptools.
    [distutils.setup_keywords]
      This adds a new keyword to setup.py's setup() function, and a
      validator to validate the value.
    [egg_info.writers]
      This adds a new writer that creates files in the PkgName.egg-info/
      directory.
    [paste.app_factory]
    [paste.composite_factory]
    [paste.entry_point_description]
      This is an entry point that describes other entry points.
    [paste.filter_app_factory]
    [paste.global_paster_command]
      Entry point that adds a command to the ``paster`` script globally.
    [paste.paster_command]
      Entry point that adds a command to the ``paster`` script to a
      project that has specifically enabled the command.
    [paste.paster_create_template]
      Entry point for creating the file layout for a new project from a
      template.
    [paste.server_runner]
    [setuptools.finalize_distribution_options]
''')


@contextlib.contextmanager
def capture_stdout():
    stdout = sys.stdout
    try:
        sys.stdout = six.StringIO()
        yield sys.stdout
    finally:
        sys.stdout = stdout


@contextlib.contextmanager
def temporary_dir():
    old_dir = os.getcwd()
    try:
        if hasattr(tempfile, 'TemporaryDirectory'):
            # Python 3
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                yield
        else:
            # Python 2
            tmpdir = tempfile.mkdtemp()
            try:
                os.chdir(tmpdir)
                yield
            finally:
                shutil.rmtree(tmpdir)
    finally:
        os.chdir(old_dir)


class CommandTest(unittest.TestCase):
    maxDiff = 1024

    def test_help(self):
        usage = textwrap.dedent('''
            Usage: <test_command> [paster_options] COMMAND [command_options]

            Options:
              --version         show program's version number and exit
              --plugin=PLUGINS  Add a plugin to the list of commands (plugins are Egg
                                specs; will also require() the Egg)
              -h, --help        Show this help message

            Commands:
              create       Create the file layout for a Python distribution
              grep         Search project for symbol
              help         Display help
              make-config  Install a package and create a fresh config file/directory
              points       Show information about entry points
              post         Run a request for the described application
              request      Run a request for the described application
              serve        Serve the described application
              setup-app    Setup an application, given a config file
        ''').strip() + "\n\n"

        with capture_stdout() as stdout:
            argv = sys.argv
            sys.argv = ['<test_command>', '--help']
            try:
                try:
                    command.run(['--help'])
                except SystemExit as exc:
                    self.assertEqual(exc.code, 0)
                else:
                    self.fail("SystemExit not raised")
            finally:
                sys.argv = argv
            self.assertEqual(usage, stdout.getvalue())


class CreateDistroCommandTest(unittest.TestCase):
    maxDiff = 1024

    def setUp(self):
        self.cmd = create_distro.CreateDistroCommand('create_distro')

    def test_list_templates(self):
        templates = textwrap.dedent('''
            Available templates:
              basic_package:  A basic setuptools-enabled package
              paste_deploy:   A web application deployed through paste.deploy
        ''').strip() + "\n"
        with capture_stdout() as stdout:
            self.cmd.run(['--list-templates'])
            self.assertEqual(templates, stdout.getvalue())

    def test_basic_package(self):
        inputs = [
            '1.0',  # Version
            'description',   # Description
            'long description',   # Long description
            'keyword1 keyword2',   # Keywords
            'author name',   # Author name
            'author@domain.com',   # Author email
            'http://example.com',   # URL of homepage
            'license',   # License
            'True',   # zip_safe
        ]
        name = 'test'

        setup_cfg = textwrap.dedent('''
            [egg_info]
            tag_build = dev
            tag_svn_revision = true
        ''').strip() + '\n'

        setup_py = textwrap.dedent(r'''
            from setuptools import setup, find_packages
            import sys, os

            version = '1.0'

            setup(name='test',
                  version=version,
                  description="description",
                  long_description="""\
            long description""",
                  classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
                  keywords='keyword1 keyword2',
                  author='author name',
                  author_email='author@domain.com',
                  url='http://example.com',
                  license='license',
                  packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
                  include_package_data=True,
                  zip_safe=True,
                  install_requires=[
                      # -*- Extra requirements: -*-
                  ],
                  entry_points="""
                  # -*- Entry points: -*-
                  """,
                  )
        ''').strip() + "\n"

        with temporary_dir():
            stdin = sys.stdin
            try:
                sys.stdin = six.StringIO('\n'.join(inputs))
                with capture_stdout():
                    self.cmd.run(['--template=basic_package', name])
            finally:
                sys.stdin = stdin

            os.chdir(name)

            with open("setup.cfg") as f:
                self.assertEqual(setup_cfg, f.read())

            with open("setup.py") as f:
                self.assertEqual(setup_py, f.read())

            with open(os.path.join(name, "__init__.py")) as f:
                self.assertEqual("#\n", f.read())


class EntryPointsTest(unittest.TestCase):
    maxDiff = 4096

    def setUp(self):
        self.cmd = entrypoints.EntryPointCommand('entrypoint')

    def test_list(self):
        entrypoints_list = PY3_ENTRY_POINTS
        if six.PY2:
            entrypoints_list = PY2_ENTRY_POINTS
        entrypoints_list = entrypoints_list.strip() + '\n'
        with capture_stdout() as stdout:
            res = self.cmd.run(['--list'])
            self.assertEqual(res, 0)

            self.assertEqual(entrypoints_list,
                             stdout.getvalue(), stdout.getvalue())

    def test_show(self):
        entrypoint = textwrap.dedent('''
            [console_scripts]
            When a package is installed, any entry point listed here will be
            turned into a command-line script.
        ''').strip() + '\n'
        with capture_stdout() as stdout:
            res = self.cmd.run(['console_scripts'])
            self.assertEqual(res, 0)
            out = stdout.getvalue()
        self.assertTrue(out.startswith(entrypoint),
                        "%r doesn't start with %r" % (out, entrypoint))

    def test_paster_command(self):
        # Issue #20: Check that SuperGeneric works on Python 3
        paster = textwrap.dedent('''
            create = paste.script.create_distro:CreateDistroCommand
                (self, name)
            exe = paste.script.exe:ExeCommand
                (self, name)
            help = paste.script.help:HelpCommand
                (self, name)
            make-config = paste.script.appinstall:MakeConfigCommand
                (self, name)
            points = paste.script.entrypoints:EntryPointCommand
                (self, name)
            post = paste.script.request:RequestCommand
                (self, name)
            request = paste.script.request:RequestCommand
                (self, name)
            serve = paste.script.serve:ServeCommand
                (self, name)
            setup-app = paste.script.appinstall:SetupCommand
                (self, name)
        ''').strip()
        with capture_stdout() as stdout:
            res = self.cmd.run(['paster_command'])
            self.assertEqual(res, 0)
            out = stdout.getvalue()

        self.assertIn(paster, out)


class PostTest(unittest.TestCase):
    maxDiff = 4096

    def test_post(self):
        config = os.path.join('docs', 'example_app.ini')
        url = '/'
        with capture_stdout() as stdout:
            if six.PY3:
                stdout.buffer = io.BytesIO()
            try:
                command.run(['post', config, url])
            except SystemExit as exc:
                self.assertEqual(exc.code, 0)
            else:
                self.fail("SystemExit not raised")
            if six.PY3:
                out = stdout.buffer.getvalue()
                out = out.decode('utf-8')
            else:
                out = stdout.getvalue()
        html_regex = textwrap.dedent('''
            <html>
            <head>
              <title>Test Application</title>
            </head>
            <body>
            .*
            </body>
            </html>
        ''').strip()
        html_regex = '\n%s\n' % html_regex
        html_regex = re.compile(html_regex, re.DOTALL)
        six.assertRegex(self, out, html_regex)

if __name__ == "__main__":
    unittest.main()
