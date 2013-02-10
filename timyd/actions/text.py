import sys

from timyd import Action
from timyd.console import colors


def format_status(status):
    if status == '':
        return colors.blue('OK')
    else:
        return colors.red(status)


class TextOutput(Action):
    """Displays the result of the service checks on the terminal.
    """

    def register_property_change(self, site, service, name,
            old_value, new_value):
        sys.stdout.write(colors.yellow(
                "[property change] %s.%s: %s: %s" % (
                site, service, name, new_value)))
        if old_value is not None:
            sys.stdout.write(" (was %s)\n" % old_value)
        else:
            sys.stdout.write("\n")

    def register_service_check(self, site, service, old_status, status, error,
            warnings):
        for w in warnings:
            sys.stdout.write(colors.cyan(
                    "[warning] %s: %s\n" % (
                    w[0], w[1])))

        color = colors.yellow if status != old_status else colors.white
        sys.stdout.write(color(
                "[service check] %s.%s: %s" % (
                site, service, format_status(status))))
        if old_status is not None:
            sys.stdout.write(" (was %s)\n" % format_status(old_status))
        else:
            sys.stdout.write("\n")
