========
Usage
========

To use Dyna Settings in a project:

    import dyna_settings

.. _django-environ: https://github.com/joke2k/django-environ
.. _12-Factor: http://12factor.net/
.. _VirtualBox: https://www.virtualbox.org/wiki/Downloads

Overview
----------------

My first Django project had lines like this in the settings.py file::

	DATABASES = {
	    'default': {
	        'USER': 'me',
	    	'PASSWORD': 'some_secret',
	    	'HOST': '127.0.0.1',  # Production
	    	#'HOST': '192.168.0.37',  # Home
	    	#'HOST': '192.168.56.101',  # Laptop/VM
	    	...
	    }
	}

Were that it was only this one setting! Logging differences, cache differences, and others. Naturally, this offense against nature needed to be remedied. So I wrote my own (as one does). Only later did I discover the popular django-environ_ which complies with "III. Config" of the 12-Factor_ rules. It works, but the annoying bit about requiring setting environment variables, especially when working between Windows, Mac OS X, and Centos is a pain. Not to mention I will often spin up a new VirtualBox_ VM to make sure that some overall feature or integration is going to deploy correctly.

Our configuration now looks like this::

	DATABASES = {
	    'default': {
	    	'USER': dyna_value('DB_USER', production_value=None),
	    	'PASSWORD': dyna_value('DB_PWD', production_value=None),
	    	'HOST': dyna_value('DB_HOST', production_value='127.0.0.1'),
	    	...
	    }
	}

Classes Specify Settings
~~~~~~~~~~~~~~~~~~~~~

Classes that implement the *DynaSettings* contract inspect the environment to determine if they should be used, and provide a dictionary of the settings the want to supply values for.

Two classes, one for Windows and one for OS X, could look like this::

	class MacBookSettings(DynaSettings):
	    """Curtis' MacBookPro dev environment"""
	    def env_detector(self):
	        return os.path.exists('/Users/curtis/dev')
	
	    def value_dict(self):
	        return {
	            'BOTO_DISABLE': True,
	            'DB_HOST': '127.0.0.1',
	            'DB_USER': 'app_user',
	            'DB_PWD': MacBookSettings.db_password,
	            'LOG_FILENAME': '/Users/curtis/dev/logs/some.log',
	            'DEFAULT_LOG_HANDLER': ['to_file'],
	        }
	        
	    @staticmethod
	    def db_password(*args, **kwargs):
	    	"""Load Settings from secret.txt"""
	    	...
	    	return pwd
	    	
There is also a corresponding class for my Windows setup, for a VM, and for production. Each of them has their own method of detecting a match to the environment and their own set of SETTINGS and method for obtaining them. Naturally the tricky part is ensuring that the env_detector correctly matches only the environment it should be used in, and the other classes do not.

Why the Complexity?
~~~~~~~~~~~~~~~~~~~~~

The main goal for me is that once I have defined the settings for my environments I never want to revisit them again. Further, I never want to be momentarily confused as to why something's not working or a test has failed, only to discover that I forgot to switch back to local settings, or change some flag or define an environment variable.

In @pydanny's excellent Django cookiecutter for the equally excellent book Two Scoops of Django he uses django-environ_ to switch between local and production settings. This requires changing manage.py::

	#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
	os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

This breaks my rule of never requiring any change - and that rule (for me) is based on the human nature of forgetting.

"But, then how do you test production setup?" On my dev box, I don't. Ever. I test it on a fully configured production server (er, not in production of course). I git push, git pull and git 'er done on the production server. This avoids the "But it works on my machine!" syndrome and prevents QA from threatening to ship my machine, then.

The other reason is that production is a little more involved obtaining certain configuration values. We've been too tempted to hard-code secrets in the settings.py rather than use the already existing and maintenanced configuration.

Usage Summary
~~~~~~~~~~~~~~~~~~~~~

1. Define 1 or more class that implements DynaSettings::
	
	class MacBookSettings(DynaSettings):
	    def env_detector(self):
	        return some_test()
			
	    def value_dict(self):
	        return my_values
			
2. Register the DynaSettings environment class(es) from the main settings file::
		
	from dyna_settings.dyna_value import register_dyna_settings, dyna_value
	register_dyna_settings(MacBookSettings())

3. Assign settings values with dyna_value::
    
    'PASSWORD': dyna_value('DB_PWD', production_value=None),
    
Two strategies for production are to either specify the default, production values in the setting
assignment with dyna_value, or create a production version of DynaSetting. The advantage of creating
a production DynaSetting class is that more sophisticated code can be used to gather settings,
hiding from the main settings file.

Assigning Settings Values
---------------------------
The dyna_value function requires the name of the setting and an optional default, or production value.::

    def dyna_value(self, setting_name, production_value=None):
    	...

If there are no DynaSettings classes registered the function *dyna_value* will simply return the *production_value*. If the *production_value* is not supplied, or is set to None, however, a *NoMatchingSettingsClass* exception will be thrown. Think of the following as an "abstract setting" that must be implemented, or supplied::
    
    SOME_SETTING = dyna_value("SOME_SETTING", production_value=None)

If the production_value parameter is None (production_value=None, or simply omitted) then one
of the DynaSettings classes *must* supply the value. If the active DynaSettings class
does not supply this value an exception will be thrown.

The production_value parameter may be an atomic type, or a function. The function should return an
object of the correct/expected type.

Examples::

    ADMIN_LOGIN = dyna_value('ADMIN_LOGIN', production_value=None)
    DB_SERVER = dyna_value('DB_SERVER', production_value='127.0.0.1')
    REMOTE_PORT = dyna_value('DB_SERVER', production_value=80)

Registering DynaSettings Classes
---------------------------------
Once a DynaSetting implementation(s) are created they must be registered. 
::

	register_dyna_settings(MacBookSettings())

register_dyna_settings will call the instance's *env_detector()* method. If this method returns true - and if there is not already another DynaSetting implementation that has returned true from its env_detector() - then this *DynaSettings* instance
becomes the one-and-only active override class used resolving the value of settings.

It is not an error if none of the registered classes matches the environment. All settings will simply take the production_value parameter value.

If a second DynaSetting implementation returns true for env_detector() a MultipleSettingsClassMatch
exception is raised. For example, if two DynaSettings implementations both return True
for env_detector() call, registering the second class raises an exception.

The name supplied to register_dyna_settings() may be a type or instance. I recommend that this is an
instance especially if the ''__init__'' requires parameters.
::

    register_dyna_settings(MacBookSettings())
    
or::

    register_dyna_settings(MacBookSettings)

Defining DynaSettings Classes
------------------------------

DynaSettings implementations are the providers of variable values and overrides at runtime. They may be used as
the sole-provider of a setting, or to override the default setting, for a specific [type of] environment.

The only two required methods that must be implemented are:
* env_detector()
* value_dict()

::

    class MacBookSettings(DynaSettings):
	"""Curtis' MacBookPro dev environment"""
	def env_detector(self):
	    return os.path.exists('/Users/curtis/dev')
	
	def value_dict(self):
	    return {
	        'BOTO_DISABLE': True,
	        'DB_HOST': '127.0.0.1',
	        'DB_USER': 'app_user',
	        'DB_PWD': MacBookSettings.db_password,
	        'LOG_FILENAME': '/Users/curtis/dev/logs/some.log',
	        'DEFAULT_LOG_HANDLER': ['to_file'],
	    }
	        
env_detector()
~~~~~~~~~~~~~~

This is called during the registration process to determine if this class instance should be used for settings or ignored. If ignored it is added to the list of registered classes, but - well, ignored.

If this method returns True then this class will be set active. [1]_ All subsequent calls to dyna_value() will use the value supplied by this class if present.

If you are paranoid, as the author has learned to be, you might implement this for your development class as such::

    def env_detector(self):
        if not ProductionSettings().env_detector():
            ...
            return result
        else:
            return False
            
It tends to be just a tad embarrassing to have some admin raise the question, "Why is the production server trying to load settings from "C:\\Users\\Curtis\\settings_override.json"? Especially since we're running on Centos. You just don't ever live that one down! :)

value_dict()
~~~~~~~~~~~~
    **Note Change** This is now only called on registration and not used dynamically. It will be called only once.

Once this class is selected as the active settings class this method is called to ask for a list of the settings. The return is a simple dictionary with the name of the setting as key, and the desired value.

It is safe to have this method call access external resources, but it is generally discouraged to import any Django classes. Currently, for one production system, the author loads XML, JSON, text files production along with hardcoded overrides for dev environments.

Environ Variable Precedence
----------------------------

I learned long ago to loath environment variables. I realize it's a very "Un*x" thing, yet it's a hidden influencer much like the special interest groups in Washington, DC.

Yet sometimes it is valuable, or even critical to reference them if they are defined. Also keep in mind that there is nothing preventing your DynaSettings class implementation from referencing os.environ.

As a convenience, you may set a flag indicating that, if defined, an environment variable takes precedence over both the value supplied for *production_value=* and as returned by the DynaSettings value_dict() method.

There are two ways to indicate this:
1. Set self._environ_vars_trump = True in your DynaSettings class implementation. The nice bit of this is you could decide to check a certain "magic" environment variable signaling that they should override and only set this for a specific implementation.
2. Set the flag globally with DynaSettingsController.set_environ_vars_trump(flag=True)

Results:

===== ============ ================ ============ ======
Trump Env Variable production_value DynaSettings Result
===== ============ ================ ============ ====== 
False   n/a          None           None         (NoMatchingSettingsClass)
True  Vulcan         None           None         Vulcan
False   n/a          None           Romulan      Romulan
False Vulcan         Klingon        Romulan      Romulan
False   n/a          Klingon        n/a          Klingon
True  Vulcan         Klingon        Romulan      Vulcan
===== ============ ================ ============ ======

From this you can see what the various combinations will produce. One nice feature is that you might *require* that a particular setting/secret is only set in an environment variable and never in source controlled text or in a file.
::

    EXPENSIVE_SERVICE_PASSWORD = dyna_settings('NSA_PASSWORD', production_value=None)

Then you could define a Production(DynaSettings) implementation, **not set the value** but set the self._environ_vars_trump = True. Then, in your development version of the class you could just either reference hard-coded values or load from a file (since those won't be against production...right? Right?) On startup if the environment variable "NAS_PASSWORD" is not defined a NoMatchingSettingsClass is thrown, service doesn't start and the admin can more easily debug the "why".

Tips & Tricks
--------------

Todo





**Footnotes**:

.. [1] Note that being the "active" class does not mean that the class will be called actively during run-time. It is simply the class that was used to obtain the settings overrides or value. The first, pre-module, version held a reference to the DynaSettings class and actively asked it for settings. This caused some file access to be performed repeatedly. Now the class in queried only once for settings.

