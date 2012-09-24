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
        self._property_values = dict()

    def _do_check(self):
        if self._log is None:
            self._log = SiteManager.get_log_for_service(
                    self.site.name, self.name)
        logging.info("Running test for service %s" % self.name)
        try:
            old_status = self.status
        except KeyError:
            old_status = None
        self._warnings = []
        try:
            self.check()
        except CheckFailure, e:
            status = e.__class__.__name__
            self.site.service_checked(
                    self,
                    old_status, status, e, self._warnings)
            self.status = status
        else:
            self.site.service_checked(
                    self,
                    old_status, '', None, self._warnings)
            self.status = ''
        self._warnings = None

    def warning(self, name, msg):
        logging.warning("%s.%s warning '%s': %s" % (
                self.site.name, self.name, name, msg))
        self._warnings.append((name, msg))

    def end_run(self):
        if self._log is not None:
            self._log.close()

    def get_property(self, prop):
        if self._log is not None:
            return self._log.get_property(prop)[1]
        else:
            return self._property_values[prop]

    def set_property(self, prop, value):
        try:
            old_value = self.get_property(prop)
            if old_value == value:
                return
        except KeyError:
            old_value = None
        if prop != 'status':
            self.site.property_changed(self, prop, old_value, value)
        if self._log is not None:
            self._log.set_property(prop, value)
        else:
            self._property_values[prop] = value


class Action(object):
    """An action, i.e. something that is done with the results of the checks.

    These objects are fed the results of the tests and the property changes,
    and are in charge of generating alerts of reports.
    """

    def register_status_change(self, site, service, old_status, new_status):
        """Method called when the status of a service changed.

        When a service check is run, if the status found is different from the
        last, this method will be called. If old_status is None, there was no
        previous status (this check was just added, or the database was reset).
        You can buffer these changes and take action when run_ended is called.
        """
        pass

    def register_property_change(self, site, service, name,
            old_value, new_value):
        """Method called when a property of a service changed.

        If a service check computes a value for a property and the property
        finds that it is different from the last, this method will be called.
        old_value might be None.
        You can buffer these changes and take action when run_ended is called.
        """
        pass

    def register_service_check(self, site, service,
            old_status, status, error, warnings):
        """Method called when a service check has been run.

        This method will be called after a service check is run, regardless of
        its results. You can probably ignore this, as other methods are enough
        to listen to changes ; taking action here could generate a lot of
        noise.
        old_status may be the same as status.
        If status is not ST_ERROR, error is None, else it is the CheckFailure
        that was raised by the service check.
        """
        pass

    def end_run(self):
        """Method called after a run, when all requested checks have finished.

        If you want to take action when all the events are known, you can defer
        it into this method.
        """
        pass


class SiteManager(object):
    def __init__(self):
        self._next_site = None
        self._sites = dict()

    def configure(self, **options):
        self._log_location = options['logs']

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
        if service not in self._sites[site].services:
            return None
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
        self.actions = list() # [Action]

    def add_check(self, service, dependencies=()):
        service.site = self
        self.services[service.name] = service
        self._dependencies[service] = dependencies
        if hasattr(service, 'dependencies'):
            deps = service.dependencies()
            if isinstance(deps, Service):
                deps = (deps,)
            self._dependencies[service] += deps
            for dep in deps:
                dep.site = self

    def get_dependencies(self, service):
        try:
            return self._dependencies[service]
        except KeyError:
            return ()

    def add_action(self, action):
        action.site = self
        self.actions.append(action)

    def service_checked(self, service, old_status, new_status,
            error, warnings):
        if service.name not in self.services:
            return
        for action in self.actions:
            action.register_service_check(
                    self.name, service.name,
                    old_status, new_status, error, warnings)

    def property_changed(self, service, name, old_value, new_value):
        for action in self.actions:
            action.register_property_change(
                    self.name, service.name, name,
                    old_value, new_value)

    def end_run(self):
        for service in self.services.itervalues():
            service.end_run()
        for action in self.actions:
            action.end_run()

_Site = Site
Site = SiteManager.site_from_module
