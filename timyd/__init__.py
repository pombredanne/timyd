import logging
import os
import sys

from timyd.logged_properties import BinaryLog, StringProperty


class CheckFailure(Exception):
    pass


class Service(object):
    status = StringProperty('status')

    def __init__(self, name):
        self.name = name
        self.site = None
        self._log = None

    def _do_check(self):
        if self._log is None:
            self._log = SiteManager.get_log_for_service(self.site, self.name)
        logging.info("Running test for service %s" % self.name)
        try:
            self.check()
        except CheckFailure, e:
            logging.error("%s.%s: error: %s:\n%s" % (
                          self.site, self.name, e.__class__.__name__, e))
            self.status = e.__class__.__name__
        else:
            logging.warning("%s.%s: ok", self.site, self.name)
            self.status = ''

    def warning(self, name, msg):
        logging.warning("%s.%s warning '%s': %s" % (
                self.site, self.name, name, msg))
        # TODO : warnings
        pass

    def end_run(self):
        self._log.close()


class Action(object):
    pass


class SiteManager(object):
    def __init__(self):
        self._next_site = None
        self._sites = dict()

    def configure(self, **options):
        self._log_location = options.get('logs', '.timyd_logs')

    def prepare_site(self, sitename):
        self._next_site = _Site(sitename)
        self._sites[sitename] = self._next_site

    def get_last_site(self):
        s = self._next_site
        self._next_site = None
        return s

    def site_from_module(self):
        return self._next_site

    def get_log_for_service(self, site, service):
        path = self._log_location
        if not os.path.isdir(path):
            os.mkdir(path)
        path = os.path.join(path, site)
        if not os.path.isdir(path):
            os.mkdir(path)
        return BinaryLog(os.path.join(path, '%s.binlog' % service))
        

SiteManager = SiteManager()


def import_site(site_name):
    if os.sep != '/':
        site_name = site_name.replace(os.sep, '/')
    if site_name[-3:].lower() == '.py':
        site_name = site_name[:-3]
    parts = site_name.split('/')
    name = parts.pop(-1)
    dir = os.sep.join(parts)

    sys.path.insert(0, dir)
    logging.info("Importing module '%s' from %s" % (name, dir))
    SiteManager.prepare_site(name)
    mod = __import__(name, globals(), locals(), [], -1)
    site = SiteManager.get_last_site()
    del sys.path[0]

    try:
        site.doc = mod.__doc__
    except AttributeError:
        site.doc = None
    return site


class Site(object):
    def __init__(self, name):
        self.name = name
        self.services = dict() # Service#name -> Service
        self._dependencies = dict() # Service -> tuple(Service)
        self._actions = list() # [Action]

    def add_check(self, service, dependencies=()):
        service.site = self.name
        self.services[service.name] = service
        self._dependencies[service] = dependencies
        if hasattr(service, 'dependencies'):
            deps = service.dependencies()
            if isinstance(deps, Service):
                deps = (deps,)
            self._dependencies[service] += deps
            for dep in deps:
                dep.site = self.name

    def get_dependencies(self, service):
        try:
            return self._dependencies[service]
        except KeyError:
            return ()

    def add_action(self, action):
        action.site = self.name
        self._actions.append(action)

    def end_run(self):
        for service in self.services.itervalues():
            service.end_run()

_Site = Site
Site = SiteManager.site_from_module
