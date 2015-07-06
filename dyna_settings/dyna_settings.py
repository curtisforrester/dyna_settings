# -*- coding: utf-8 -*-
"""
dyna_settings: Framework for supporting the automatic adjustment of settings for a detected environment.

Overview
----------------
This module/package grows out of a development and testing need to adjust some of the settings to
match the operating environment. This includes production, a developer's work box(s) and testing
servers. This also reflects the need to remove secrets from the main settings file.

With this classes contain the rule and settings that are applied, given that the process is being
run in a certain environment. If the class detects something about the machine, folder, or any
other environmental condition, it then becomes the provider for settings values. Once classes are
defined and registered the program can be run or hosted with no change to settings.

Scenario Description:
    In production a Django server will connect to a database at 10.100.1.250 with the credentials
    of prodUser/prodPassword.

    Kristine and Lee are developers who work on Windows and Mac hardware. Kristine hosts her database
    within a VM running on her box while Lee simply runs his DB on his laptop. When integration
    tests are run on code push they are run on the test server.

    There are four (or more) sets of settings that are required:
        1. Production
        2. Kristine's development environment
        3. Lee's development environment
        4. The integration/unit test server

    One possible solution is for each to have their own version of the settings file. Each modifies
    the base settings.py for their own particular needs. One very real problem is that when the base
    server settings.py file changes each shadow settings file must be modified to reflect the changes.

    A better solution is what this package is about. There remains one master Django settings.py,
    but each environment defines its own "DynaSettings" class implementation and a detection rule
    to report when that implementation should be used. This detection rule can be to look for
    certain OS and folder structures, look for a file within the filesystem, or inspect an
    environment variable.

    Kristine's implementation might look like:

    class KristineDevSettings(DynaSettings):
        def value_dict(self):
            return {
                'DBServer': '192.168.56.101',
                'DBUsername': 'dev',
                'DBPassword': 'dev',
            }

        def env_detector(self):
            return os.path.exists('C:\\Source\\tech_company\\kristine.txt')

    In the base Django settings file the DB setting might be define like this:
    register_dyna_settings(KristineDevSettings())
    # ...
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': dyna_value('DBName', production_value='bit_bucket'),
            'USER': dyna_value('DBUsername', production_value='prodUser'),
            'PASSWORD': dyna_value('DBPassword', production_value='prodPassword'),
            'HOST': dyna_value('DBServer', production_value='127.0.0.1'),
            'PORT': dyna_value('DBPort', production_value=''),
            'CONN_MAX_AGE': 0,
        }
    }

    When the service is run in production the values from the production_value parameter are used.
    However, when the server is launched on Kristine's dev box the settings for HOST, USER, and
    PASSWORD will be taken from her KristineDevSetting.

 Usage Summary
 ---------------
 1. Define 1 or more class that implements DynaSettings
    - env_detector() will inspect the environment and return true if this class should override settings
    - value_dict() returns the dictionary of settings values overrides

2. Register the DynaSettings environment class(es) from the main settings file
    register_dyna_settings(MacBookSettings())

3. Assign variables with dyna_value
    This is the meat of the package. Once the environment DynaSettings classes have been registered
    settings assignment will automatically use the one that matches the environment, or will use
    the supplied "production_value" if none match.

Two strategies for production are to either specify the default, production values in the setting
assignment with dyna_value, or create a production version of DynaSetting. The advantage of creating
a production DynaSetting class is that more sophisticated code can be used to gather settings,
hiding from the main settings file.

Defining DynaSettings Classes
------------------------------
DynaSettings implementations are the providers of variable values at runtime. They may be used as
the sole-provider of a setting, or to override the default setting, given a certain environment.



Registering DynaSettings Classes
---------------------------------
Once a DynaSetting implementation(s) are created they must be registered. The process of registering
calls the entity's env_detector() method. If the return is true, and if there is not already
another DynaSetting implementation that returned true from its env_detector(), then this settings
entity becomes "the" override class that is used for resolving the value of settings.

It is a valid scenario that none of the registered classes matches the environment. The default
production_value from dyna_value() calls will be used.

If a second DynaSetting implementation returns true for env_detector() a MultipleSettingsClassMatch
exception is raised. For example, if two DynaSettings implementations were to both return True
for env_detector() call, upon registering the second settings class this exception is raised.

The name supplied to register_dyna_settings() maybe a type or instance. I recommend that this is an
instance especially if the __init__ requires parameters.

    register_dyna_settings(MacBookSettings())
    or
    register_dyna_settings(MacBookSettings)

Assigning Settings Values
---------------------------
The dyna_value function requires the name of the setting and an optional default, or production value.

If the production_value parameter is None (production_value=None, or simply omitted) then one
of the DynaSettings environment classes *must* supply the value. If the active DynaSettings class
does not supply this value an exception will be thrown.

The production_value parameter may be an atomic type, or a function. The function should return an
object of the correct/expected type.

Examples:

    ADMIN_LOGIN = dyna_value('ADMIN_LOGIN', production_value=None)
    DB_SERVER = dyna_value('DB_SERVER', production_value='127.0.0.1')
    REMOTE_PORT = dyna_value('DB_SERVER', production_value=80)

"""

import logging
import types

__author__ = 'curtis'

LOG = logging.getLogger('dyna_settings')

__all__ = (
    'DynaSettingsController',
    'register_dyna_settings',
    "dyna_value",
    'DynaSettings',
)


class NoMatchingSettingsClass(Exception):
    """
    Raised if there is no default production_value and the active registered DynaSettings
    class does not provide the value.
    """
    pass


class MultipleSettingsClassMatch(Exception):
    """
    Raised if more than 1 of the DynaSettings implementations return true for the
    env_detector() method.
    """
    pass


class DynaSettingsController(object):
    def __init__(self):
        self.dyna_settings_classes = []
        self.detected_settings = None
        self.did_find_multiple_matches = False
        self.environ_vars_trump = False

    @classmethod
    def set_environ_vars_trump(cls, flag=True):
        """Sets the 'Singleton' instance's environ_vars_trump value globally"""
        _dyna_controller.environ_vars_trump = flag

    def register(self, env_settings_class):
        """
        :param env_settings_class: The class instance or type to register as a settings provider
        :return: None
        """
        if env_settings_class in self.dyna_settings_classes:
            message = 'Re-registering env_settings_class: %s' % str(env_settings_class)
            LOG.warning(message)
            raise Exception(message)

        # Are we registering a class instance or a type? Instance is better
        is_type = isinstance(env_settings_class, type)
        if is_type:
            is_typeof = issubclass(env_settings_class, DynaSettings)
            env_settings_class = env_settings_class()

        # Is this an instance?
        if isinstance(env_settings_class, DynaSettings):
            if env_settings_class.env_detector():
                if self.detected_settings:
                    self.did_find_multiple_matches = True
                    raise Exception('Multiple environment checks matched for DynaSettings while registering %s', str(type(env_settings_class)))

                # Set this as our detected environment
                env_settings_class.init_values()
                # Did this implementation want us to set environment vars trump?
                if not self.environ_vars_trump:
                    self.environ_vars_trump = env_settings_class.environ_vars_trump
                # It's a keeper. Set this as our active "detected_settings" instance
                self.detected_settings = env_settings_class

            # Save each registered instance for posterity. (Will be used in a later version for craziness)
            self.dyna_settings_classes.append(env_settings_class)
        else:
            LOG.error('Not a type of DynaSettings: %s', str(type(env_settings_class)))

    def dyna_value(self, setting_name, production_value=None):
        # Trump trumps
        if self.environ_vars_trump:
            import os
            val = os.environ.get(setting_name)
            if val:
                return val

        if not self.detected_settings:
            if production_value is not None:
                return production_value
            raise NoMatchingSettingsClass()

        assert isinstance(self.detected_settings, DynaSettings)
        val = self.detected_settings.get_value(setting_name=setting_name, production_value=production_value)

        if self.environ_vars_trump and not val:
            raise NoMatchingSettingsClass()
        return val

    def reset(self):
        """
        Primarily used for unit tests
        """
        self.detected_settings = None
        self.dyna_settings_classes = []
        self.did_find_multiple_matches = False
        self.environ_vars_trump = False

# End DynaSettingsController class

# The one and only controller
_dyna_controller = DynaSettingsController()

def register_dyna_settings(class_name):
    """
    Registers a DynaSettings class containing alternative settings
    :param class_name:
    :return: None
    """
    _dyna_controller.register(class_name)


def dyna_value(setting_name, production_value=None):
    return _dyna_controller.dyna_value(setting_name=setting_name, production_value=production_value)


def dyna_values():
    if _dyna_controller.detected_settings:
        return _dyna_controller.detected_settings.all_settings

class DynaSettings(object):
    """
    Virtual class custom environment settings must implement.
    """
    def __init__(self):
        self._value_dict = {}
        self._environ_vars_trump = False

    def init_values(self):
        self._value_dict.update(self.value_dict())

    @property
    def environ_vars_trump(self):
        return self._environ_vars_trump

    @property
    def all_settings(self):
        return self._value_dict

    def get_value(self, setting_name, production_value):
        if setting_name in self._value_dict:
            val = self._value_dict[setting_name]
            if isinstance(val, types.FunctionType):
                return val(production_value=production_value)
            return val
        return production_value

    def env_detector(self):
        """
        Detects the environment that is currently hosting the code. There can be only a single
        DynaSettings class that returns true.
        :return: True if this is the environment, False if not
        :rtype: bool
        """
        raise NotImplementedError()

    def value_dict(self):
        """
        Called to setup the values the child is specifying for the environment matching env_detector().
        The values in this dictionary are referenced from the main settings file by name. For example:
            ADMIN_LOGIN = dyna_value('ADMIN_LOGIN', production_value=None)

        This is called only once, and only if the environment matched env_detector()
        :return: A dictionary of the settings the instance is specifying values for
        :rtype: dict
        """
        raise NotImplementedError()