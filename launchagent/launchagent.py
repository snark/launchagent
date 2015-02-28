from __future__ import unicode_literals
import plistlib
import launchd
import os

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
    init_groups = _property_factory("InitGroups", int)
    start_on_mount = _property_factory("StartOnMount", int)
    standard_in_path = _property_factory("StandardInPath", _string_type)
    standard_out_path = _property_factory("StandardOutPath", _string_type)
    standard_error_path = _property_factory("StandardErrorPath", _string_type)
    debug = _property_factory("Debug", bool)
    wait_for_debug = _property_factory("WaitForDebugger", bool)
    abandon_process_group = _property_factory("AbandonProcessGroup", bool)
    low_priority_io = _property_factory("LowPriorityIO", bool)
    launch_only_once = _property_factory("LaunchOnlyOnce", bool)

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
                if not self.__validate_calendar_interval(v):
                    invalid = True
                    break
        elif isinstance(val, dict):
            invalid = not self.__validate_calendar_interval(val)
        else:
            invalid = True
        if invalid:
            raise TypeError(
                "The StartCalendarInterval property of the LaunchAgent "
                "must be a dict or a list of dicts, with dict keys "
                "indicating the period."
            )
        self.plist["StartCalendarInterval"] = val

    def __validate_calendar_interval(self, v):
        return isinstance(v, dict) and set(v.keys()).issubset(_INTERVALS) and\
            set([type(entry) for entry in v.values()]).issubset({int})

    @start_calendar_interval.deleter
    def start_calendar_interval(self):
        del self.plist["StartCalendarInterval"]

    @property
    def umask(self):
        """
        A value specifying what key should passed to umask before running
        the LaunchAgent's job.
        """
        return self.plist["Umask"]

    @umask.setter
    def umask(self, val):
        if not isinstance(val, int) or val < 0 or val > 511:
            raise TypeError(
                """
                umask value must be an integer corresponsding to
                a valid three-digit octal mask.
                """
            )
        self.plist["Umask"] = val

    @umask.deleter
    def umask(self):
        del self.plist["Umask"]

    @property
    def inetd_compatibility(self):
        """
        The inetdCompatibility property of the LaunchAgent, indicating
        that the daemon expects to be run as if it were launched from inetd.
        """
        return self.plist["inetdCompatibility"]

    @inetd_compatibility.setter
    def inetd_compatibility(self, val):
        if not isinstance(val, dict) or len(val.keys()) != 1 or\
                ("Wait" not in dict):
            if not isinstance(val, bool):
                raise TypeError(
                    """
                    The inetdCompatibility property must be a dictionary
                    with a single key, "Wait", associated with a boolean
                    value, or, as a convenience setter, the boolean
                    directly.
                    """
                )
        if isinstance(val, dict):
            self.plist["inetdCompatibility"] = val
        else:
            self.plist["inetdCompatibility"] = {"Wait": val}

    @inetd_compatibility.deleter
    def start_calendar_interval(self):
        del self.plist["StartCalendarInterval"]

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

    def is_valid(self):
        """
        Return a value indicating the the contextual validity of
        the values assigned to this LaunchAgent.
        """
        return self.label and (self.program or self.program_arguments)

    # Internal
    def __str__(self):
        return "<LaunchAgent: {}>".format(self.label)
