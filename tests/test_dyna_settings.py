#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_dyna_settings
----------------------------------

Tests for `dyna_settings` module. I normally use py.test.
"""

import unittest
from dyna_settings.core import DynaSettings, _dyna_controller, register_dyna_settings, dyna_value, \
    NoMatchingSettingsClass, DynaSettingsController

__author__ = 'curtis'


class ChildOK_Match(DynaSettings):
    def value_dict(self):
        return {'A': 'a', 'B': 'b', 'C': 9}

    def env_detector(self):
        return True


class ChildOK_NoMatch(DynaSettings):
    def value_dict(self):
        return {'A': 'aa', 'B': 'bb', 'C': 99}

    def env_detector(self):
        return False


class EnvSettingTrue(DynaSettings):

    def __init__(self):
        super(EnvSettingTrue, self).__init__()
        self._environ_vars_trump = True

    def value_dict(self):
        return {
            'PATH': 'a very wrong path',
            'AINT_THAR': 'This aint gonna be there'
        }

    def env_detector(self):
        return True


class TestDynaSettings(unittest.TestCase):
    def test_parent_interface_excepts(self):
        bad = DynaSettings()
        with self.assertRaises(NotImplementedError):
            bad.env_detector()

        with self.assertRaises(NotImplementedError):
            bad.value_dict()

    def test_child_interface(self):
        good = ChildOK_Match()
        self.assertIsInstance(good.value_dict(), dict)
        self.assertTrue(good.env_detector())

        good.init_values()
        self.assertEqual(good.get_value('A', 'x'), 'a')

    def test_no_match_child_interface(self):
        good = ChildOK_NoMatch()
        self.assertIsInstance(good.value_dict(), dict)
        self.assertFalse(good.env_detector())

        good.init_values()
        self.assertEqual(good.get_value('A', 'x'), 'aa')

    def test_register_match(self):
        _dyna_controller.reset()
        instance = ChildOK_Match()
        register_dyna_settings(instance)
        register_dyna_settings(ChildOK_NoMatch())
        self.assertEqual(_dyna_controller.detected_settings, instance)

    def test_register_nomatch(self):
        _dyna_controller.reset()
        register_dyna_settings(ChildOK_NoMatch())
        self.assertIsNone(_dyna_controller.detected_settings)

    def test_get_values(self):
        _dyna_controller.reset()
        register_dyna_settings(ChildOK_Match())
        register_dyna_settings(ChildOK_NoMatch())

        val = dyna_value('A', production_value='x')
        self.assertEqual(val, 'a')
        val = dyna_value('B', production_value='x')
        self.assertEqual(val, 'b')

        val = dyna_value('UNDEFINED', production_value='prod')
        self.assertEqual(val, 'prod')

    def test_get_values_with_no_settings_class(self):
        _dyna_controller.reset()

        with self.assertRaises(NoMatchingSettingsClass):
            val = dyna_value('BAD')

    def test_environ_var_trump_global(self):
        """
        Verify that with the global trump set True we'll get from the environment
        :return:
        """
        DynaSettingsController.set_environ_vars_trump(flag=True)

        self.assertTrue(_dyna_controller.environ_vars_trump)
        import os

        path = os.environ.get('PATH')
        self.assertTrue(path)

        path_from_settings = dyna_value('PATH', production_value=None)
        self.assertTrue(path_from_settings)
        self.assertEqual(path_from_settings, path)

    def test_environ_var_trump_off(self):
        """
        Verify that with the environment var trump off we obtain the value from
        our dyna settings and not the environment variable.
        :return:
        """
        DynaSettingsController.set_environ_vars_trump(flag=False)

        self.assertFalse(_dyna_controller.environ_vars_trump)
        import os

        path = os.environ.get('PATH')
        self.assertTrue(path)

        path_from_settings = dyna_value('PATH', production_value='Internal path')
        self.assertTrue(path_from_settings)
        self.assertNotEqual(path_from_settings, path)

    def test_environ_var_trump_instance(self):
        """
        Verify that, with a DynaSettings instance registered that sets trump True it behaves
        properly by obtaining the value from the environment variable. Should ignore both the
        production_value and the settings class definition.
        :return:
        """
        _dyna_controller.reset()
        self.assertFalse(_dyna_controller.environ_vars_trump)

        register_dyna_settings(EnvSettingTrue())

        import os

        path = os.environ.get('PATH')
        self.assertTrue(path)
        path_from_settings = dyna_value('PATH', production_value='Internal path')
        self.assertTrue(path_from_settings)
        self.assertEqual(path_from_settings, path)

    def test_environ_var_trump_no_env_var(self):
        """
        Verify that if trump is True but the environment var is not defined we'll still pick
        up the value if the class instance has defined it
        :return:
        """
        _dyna_controller.reset()

        register_dyna_settings(EnvSettingTrue())

        path = dyna_value('AINT_THAR', production_value=None)
        self.assertTrue(path)

    def test_environ_var_trump_fail(self):
        """
        Verifies that if Trump is true, environment doesn't have the variable, production_value doesn't
        define it, and the class does not either, then exception is raised.
        :return:
        """
        _dyna_controller.reset()
        register_dyna_settings(EnvSettingTrue())

        with self.assertRaises(NoMatchingSettingsClass):
            bad = dyna_value('VOODOOUDO', production_value=None)
            print bad


if __name__ == '__main__':
    unittest.main()
