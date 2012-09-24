from optparse import OptionParser
import logging
import string
import sys

from timyd import SiteManager, import_site
from timyd.actions.text import TextOutput
from timyd.console import colors


class Runner(object):
    def __init__(self, site, **options):
        if options['verbosity'] == 0: # default
            level = logging.WARNING
        elif options['verbosity'] == 1: # -v
            level = logging.INFO
        else: # -v -v
            level = logging.DEBUG

        logging.basicConfig(level=level)

        SiteManager.configure(**options)
        self.site = import_site(site)

        if options['textoutput']:
            if options['colors'] == True:
                colors.enable(True)
            elif options['colors'] == False:
                colors.enable(False)
            else: # options['colors'] is None
                colors.auto()
            self.site.add_action(TextOutput())

    def check_site(self):
        self.check_services(self.site.services.keys())

    def check_services(self, service_names):
        logging.info("Checking site %s" % self.site.name)

        self._checked_services = set()
        self._active_services = set()

        for name in service_names:
            service = self.site.services[name]
            self._check_service(service)

    def _check_service(self, service):
        if service in self._checked_services:
            return
        if service in self._active_services:
            raise Exception("Loop in service dependency graph! Services:\n%s" %
                    string.join([s.name for s in self._active_services], ", "))
        self._active_services.add(service)

        for dep in self.site.get_dependencies(service):
            if dep not in self._checked_services:
                self._check_service(dep)

        service._do_check()
        self._checked_services.add(service)
        self._active_services.remove(service)

    def end_run(self):
        self.site.end_run()


def main():
    optparser = OptionParser()
    optparser.add_option(
            '-q', '--quiet',
            action='store_false', dest='textoutput',
            help="don't print service check results on stdout")
    optparser.add_option(
            '-v', '--verbose',
            action='count', dest='verbosity',
            help="increase program verbosity")
    optparser.add_option(
            '-l', '--logs',
            action='store', dest='logs',
            help="location of the service logs (default: .timyd_logs)")
    optparser.add_option(
            '--colors',
            action='store_true', dest='colors',
            help="use colored terminal output")
    optparser.add_option(
            '--no-colors',
            action='store_false', dest='colors',
            help="don't use colored terminal output")
    optparser.set_defaults(colors=None, verbosity=0, textoutput=True,
                           logs='.timyd_logs')
    (options, args) = optparser.parse_args()
    options = vars(options) # options is not a dict!?

    try:
        site = args.pop(0)
    except IndexError:
        logging.critical("No site specified")
        sys.exit(2)

    runner = Runner(site, **options)

    if not args:
        runner.check_site()
    else:
        runner.check_services(args)

    runner.end_run()
