import sublime, sublime_plugin
import os
import re
import sys

version = sublime.version()

from unittest import TextTestRunner
if version >= '3000':
    from .unittesting import TestLoader
    from .unittesting import DeferringTextTestRunner
else:
    from unittesting import TestLoader

# todo: customable
tests_dir = 'tests'

class OutputPanelInsert(sublime_plugin.TextCommand):
    def run(self, edit, characters):
        self.view.set_read_only(False)
        self.view.insert(edit, self.view.size(), characters)
        self.view.set_read_only(True)
        self.view.show(self.view.size())

class OutputPanel:
    def __init__(self, name, file_regex='', line_regex = '', base_dir = None, word_wrap = False, line_numbers = False,
        gutter = False, scroll_past_end = False, syntax = 'Packages/Text/Plain text.tmLanguage'):

        self.name = name
        self.window = sublime.active_window()
        self.output_view = self.window.get_output_panel(name)

        # default to the current file directory
        if (not base_dir and self.window.active_view() and self.window.active_view().file_name()):
            base_dir = os.path.dirname(self.window.active_view().file_name())

        self.output_view.settings().set("result_file_regex", file_regex)
        self.output_view.settings().set("result_line_regex", line_regex)
        self.output_view.settings().set("result_base_dir", base_dir)
        self.output_view.settings().set("word_wrap", word_wrap)
        self.output_view.settings().set("line_numbers", line_numbers)
        self.output_view.settings().set("gutter", gutter)
        self.output_view.settings().set("scroll_past_end", scroll_past_end)
        self.output_view.settings().set("syntax", syntax)
        self.closed = False

    def write(self, s):
        self.output_view.run_command('output_panel_insert', {'characters': s})

    def flush(self):
        pass

    def show(self):
        self.window.run_command("show_panel", {"panel": "output."+self.name})

    def close(self):
        self.closed = True
        pass

def input_parser(package):
    m = re.match(r'([^/]+)/(.+)', package)
    if m:
        return m.groups()
    else:
        return (package, "test*.py")

class UnitTestingCommand(sublime_plugin.ApplicationCommand):
    def run(self, package=None, output=None, async=False, deferred=False):
        self.settingsFileName = "UnitTesting.sublime-settings"
        self.s = sublime.load_settings(self.settingsFileName)

        # pattern is a regex of filenames to be tested

        if package:
            # save the package name
            self.s.set("recent_package", package)
            sublime.save_settings(self.settingsFileName)

            (package, pattern) = input_parser(package)
            if output=="panel":
                output_panel = OutputPanel('unittests', file_regex = r'File "([^"]*)", line (\d+)')
                output_panel.show()
                stream = output_panel
            else:
                if output:
                    outfile = output
                else:
                    outputdir = os.path.join(sublime.packages_path(), 'User', 'UnitTesting', "tests_output")
                    if not os.path.isdir(outputdir):
                        os.makedirs(outputdir)
                    outfile = os.path.join(outputdir, package)

                if os.path.exists(outfile): os.remove(outfile)
                stream = open(outfile, "w")

            if version<'3000':
                deferred = False
                async = False

            if async:
                sublime.set_timeout_async(lambda: self.testing(package, pattern, stream, False), 100)
            else:
                self.testing(package, pattern, stream, deferred)

        else:
            recent_package = self.s.get("recent_package", "Package Name")
            view = sublime.active_window().show_input_panel('Package:', recent_package,
                lambda x: sublime.run_command("unit_testing", {
                        "package":x, "output":output, "async":async, "deferred":deferred
                    }), None, None )
            view.run_command("select_all")

    def testing(self, package, pattern, stream, deferred=False):
        try:
            # and use custom loader which support ST2 and reloading modules
            loader = TestLoader(deferred)
            test = loader.discover(os.path.join(sublime.packages_path(),package, tests_dir), pattern)
            # use deferred test runner or default test runner
            if deferred:
                testRunner = DeferringTextTestRunner(stream, verbosity=2)
            else:
                testRunner = TextTestRunner(stream, verbosity=2)
            testRunner.run(test)
        except Exception as e:
            if not stream.closed:
                stream.write("ERROR: %s\n" % e)
        if not deferred:
            stream.close()