from __future__ import unicode_literals
import plistlib
import launchd
import os
import six

_USER = launchd.plist.USER

_INTERVALS = {"Minute", "Hour", "Day", "Weekday", "Month"}

# man launchd.plist

# TO DO - Nicer interface for setting ProgramArguments, StartCalendarInterval

try:
    _string_type = basestring
except NameError:
    _string_type = str


# Typechecking is based on the typedecorator library, available at
# https://github.com/dobarkod/typedecorator -- this is meant to
# cut down on the amount of boilerplate required to set up our
# class properties
def _constraint_to_string(t):
    if isinstance(t, type):
        return t.__name__
    if isinstance(t, _string_type):
        return t
    elif isinstance(t, list) and len(t) == 1:
        return "[%s]" % _constraint_to_string(t[0])
    elif isinstance(t, dict) and len(t) == 1:
        k, v = list(t.items())[0]
        return "{%s:%s}" % (_constraint_to_string(k), _constraint_to_string(v))


def _verify_type_constraint(v, t):
    if isinstance(t, type):
        return isinstance(v, t)
    elif isinstance(t, _string_type) and type(v).__name__ == t:
        return True
    elif isinstance(t, list) and isinstance(v, list):
        return all(_verify_type_constraint(vx, t[0]) for vx in v)
    elif isinstance(t, dict) and isinstance(v, dict):
        tk, tv = list(t.items())[0]
        return all(
                _verify_type_constraint(vk, tk) and
                _verify_type_constraint(vv, tv) for vk, vv in v.items()
            )
    else:
        return False


def _property_factory(prop_name, signature, doc=None):

    def fget(la): return la.plist.get(prop_name)

    def fdel(la): del la.plist[prop_name]

    def fset(la, val):
        if not _verify_type_constraint(val, signature):
            raise TypeError(
                "LaunchAgent\"s {} property must match {}"
                .format(prop_name, _constraint_to_string(signature))
            )
        la.plist[prop_name] = val

    if not doc:
        doc = "The {} property of the LaunchAgent.".format(prop_name)

    return property(fget, fset, fdel, doc)


class LaunchAgent(object):
    def __init__(self, label):
        if label.endswith(".plist"):
            self.plist_filepath = label
            label = self.plist_filepath[0:-7]
        else:
            # plist generation must occur first so that our properties
            # have a place to live
            self.plist_filepath = os.path.expanduser(os.path.join(
                launchd.plist.PLIST_LOCATIONS[_USER],
                "{}.plist".format(label)
            ))
        if os.path.isfile(self.plist_filepath):
            self.plist = launchd.plist.read(label, _USER)
        else:
            self.plist = {}

        self.label = label

    label = _property_factory("Label", _string_type)
    program = _property_factory("Program", _string_type)
    program_arguments = _property_factory("ProgramArguments", [_string_type])

    disabled = _property_factory("Disabled", bool)
    user_name = _property_factory("UserName", _string_type)
    group_name = _property_factory("GroupName", _string_type)
    limit_load_to_hosts = _property_factory(
        "LimitListToHosts", [_string_type])
    limit_load_from_hosts = _property_factory(
        "LimitListFromHosts", [_string_type])
    limit_load_to_session_type = _property_factory(
        "LimitLoadToSessionType", _string_type)
    nice = _property_factory("nice", int)
    enable_globbing = _property_factory("EnableGlobbing", bool)
    enable_transactions = _property_factory("EnableTransactions", bool)
    enable_pressured_exit = _property_factory("EnablePressuredExit", bool)
    run_at_load = _property_factory("RunAtLoad", bool)
    root_directory = _property_factory("RootDirectory", _string_type)
    working_directory = _property_factory("WorkingDirectory", _string_type)
    environment_variables = _property_factory(
        "EnvironmentVariables", {str: str})
    time_out = _property_factory("TimeOut", int)
    exit_time_out = _property_factory("ExitTimeOut", int)
    throttle_interval = _property_factory("ThrottleInterval", int)
    start_interval = _property_factory(
        "StartInterval", int, """
        The StartInternval property of the LaunchAgent causes launchd
        to start the job every N seconds.
        """
    )

    # Some properties which require additional validation or handling
    @property
    def start_calendar_interval(self):
        """
        The StartCalendarInterval property of the LaunchAgent, composed
        of a dict or list of dicts, with the keys of the dicts specifying
        the calendar interval. This property causes launchd to start the
        LaunchAgent job every specified interval. See `man launchd.plist`
        for additional details
        """
        return self.plist["StartCalendarInterval"]

    @start_calendar_interval.setter
    def start_calendar_interval(self, val):
        invalid = False
        if isinstance(val, list):
            for v in val:
                if not self._validate_calendar_interval(v):
                    invalid = True
                    break
        elif isinstance(val, dict):
            invalid = not self._validate_calendar_interval(val)
        else:
            invalid = True
        if invalid:
            raise TypeError(
                "The StartCalendarInterval property of the LaunchAgent "
                "must be a dict or a list of dicts, with dict keys "
                "indicating the period."
            )
        self.plist["StartCalendarInterval"] = val

    @start_calendar_interval.deleter
    def start_calendar_interval(self):
        del self.plist["StartCalendarInterval"]

    def _validate_calendar_interval(self, v):
        return isinstance(v, dict) and set(v.keys()).issubset(_INTERVALS) and\
            set([type(entry) for entry in v.values()]).issubset({int})

    # launchagent's properties outside those defined by a LaunchAgent plist
    def is_loaded(self):
        """
        Boolean indicating whether the configuration file for this LaunchAgent
        has been loaded.
        """
        return launchd.LaunchdJob(self.label).exists()

    def job(self):
        """The launchd.LaunchdJob for this LaunchAgent."""
        if self.is_loaded:
            return launchd.LaunchdJob(self.label)
        else:
            return None

    # Actions
    def write(self):
        """Generate a plist file for this LaunchAgent."""
        launchd.plist.write(self.label, self.plist)

    def load(self):
        """Load this LaunchAgent if not already loaded."""
        if not self.is_loaded():
            launchd.cmd.launchctl("load", self.plist_filepath)

    def unload(self):
        """Unload this LaunchAgent if loaded."""
        if self.is_loaded():
            launchd.cmd.launchctl("unload", self.plist_filepath)

    def reload(self):
        """Reload this LaunchAgent."""
        self.unload()
        self.load()

    # Internal
    def _validate(self):
        # UserName and GroupName are meaningless outside root context
        # but we are not currently checking for this.
        return self.label and (self.program or self.program_arguments)

    def __str__(self):
        return "<LaunchAgent: {}>".format(self.label)
