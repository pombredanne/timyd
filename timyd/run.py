from optparse import OptionParser
import logging
import sys

from timyd import SiteManager, import_site


class Runner(object):
    def __init__(self, site, **options):
        level = {
                0: logging.ERROR, # --quiet
                1: logging.WARNING, # default
                2: logging.INFO, # -v
                3: logging.DEBUG, # -v -v
                }[options['verbosity']]

        logging.basicConfig(level=level)

        SiteManager.configure(**options)
        self.site = import_site(site)

    def check_site(self):
        self.check_services(self.site.services.keys())

    def check_services(self, service_names):
        logging.info("Checking site %s" % self.site.name)
        # TODO : run in the correct order, considering the dependencies
        for name in service_names:
            service = self.site.services[name]
            service._do_check()

    def end_run(self):
        self.site.end_run()


def main():
    optparser = OptionParser()
    optparser.add_option(
            '-q', '--quiet',
            action='store_const', const=0, dest='verbosity',
            default=1,
            help="don't print status messages to stdout")
    optparser.add_option(
            '-v', '--verbose',
            action='count', dest='verbosity',
            default=1,
            help="increase program verbosity")
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
