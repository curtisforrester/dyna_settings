# -*- coding: utf-8 -*-
"""
dyna_settings: Framework for supporting the automatic adjustment of settings for a detected environment.
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
    'NoMatchingSettingsClass',
    'MultipleSettingsClassMatch',
    'dyna_values',
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