# droopescan.

[![Build Status](https://api.travis-ci.org/droope/droopescan.svg?branch=master)](https://travis-ci.org/droope/droopescan) [![PyPI version](https://img.shields.io/pypi/v/droopescan.svg)](https://pypi.python.org/pypi/droopescan)

A plugin-based scanner that aids security researchers in identifying issues with
several CMS:

* Drupal.
* SilverStripe.
* Wordpress.

Partial functionality for:

* Joomla (version enumeration and interesting URLs only).
* Moodle (plugin & theme very limited, watch out)

<pre>
computer:~/droopescan$ droopescan scan drupal -u http://example.org/ -t 8
[+] No themes found.

[+] Possible interesting urls found:
    Default changelog file - https://www.example.org/CHANGELOG.txt
    Default admin - https://www.example.org/user/login

[+] Possible version(s):
    7.34

[+] Plugins found:
    views https://www.example.org/sites/all/modules/views/
        https://www.example.org/sites/all/modules/views/README.txt
        https://www.example.org/sites/all/modules/views/LICENSE.txt
    token https://www.example.org/sites/all/modules/token/
        https://www.example.org/sites/all/modules/token/README.txt
        https://www.example.org/sites/all/modules/token/LICENSE.txt
    pathauto https://www.example.org/sites/all/modules/pathauto/
        https://www.example.org/sites/all/modules/pathauto/README.txt
        https://www.example.org/sites/all/modules/pathauto/LICENSE.txt
        https://www.example.org/sites/all/modules/pathauto/API.txt
    libraries https://www.example.org/sites/all/modules/libraries/
        https://www.example.org/sites/all/modules/libraries/CHANGELOG.txt
        https://www.example.org/sites/all/modules/libraries/README.txt
        https://www.example.org/sites/all/modules/libraries/LICENSE.txt
    entity https://www.example.org/sites/all/modules/entity/
        https://www.example.org/sites/all/modules/entity/README.txt
        https://www.example.org/sites/all/modules/entity/LICENSE.txt
    google_analytics https://www.example.org/sites/all/modules/google_analytics/
        https://www.example.org/sites/all/modules/google_analytics/README.txt
        https://www.example.org/sites/all/modules/google_analytics/LICENSE.txt
    ctools https://www.example.org/sites/all/modules/ctools/
        https://www.example.org/sites/all/modules/ctools/CHANGELOG.txt
        https://www.example.org/sites/all/modules/ctools/LICENSE.txt
        https://www.example.org/sites/all/modules/ctools/API.txt
    features https://www.example.org/sites/all/modules/features/
        https://www.example.org/sites/all/modules/features/CHANGELOG.txt
        https://www.example.org/sites/all/modules/features/README.txt
        https://www.example.org/sites/all/modules/features/LICENSE.txt
        https://www.example.org/sites/all/modules/features/API.txt
    [... snip for README ...]

[+] Scan finished (0:04:59.502427 elapsed)
</pre>

You can get a full list of options by running:

<pre>
droopescan --help
droopescan scan --help
</pre>

# Why not X?

Because droopescan:

* is fast
* is stable
* is up to date
* allows simultaneous scanning of multiple sites
* is 100% python

# Installation

Installation is easy using pip:

<pre>
apt-get install python-pip
pip install droopescan
</pre>

Manual installation is as follows:

<pre>
git clone https://github.com/droope/droopescan.git
cd droopescan
pip install -r requirements.txt
./droopescan scan --help
</pre>

The master branch corresponds to the latest release (what is in pypi).
Development branch is unstable and all pull requests must be made against it.
More notes regarding installation can be [found here](https://droope.github.io/droopescan-docs/_build/html/installation.html).

# Features
## Scan types.

Droopescan aims to be the most accurate by default, while not overloading the
target server due to excessive concurrent requests. Due to this, by default, a
large number of requests will be made with four threads; change these settings
by using the `--number` and `--threads` arguments respectively.

This tool is able to perform four kinds of tests. By default all tests are ran,
but you can specify one of the following with the `-e` or `--enumerate` flag:

* p -- *Plugin checks*: Performs several thousand HTTP requests and returns a
listing of all plugins found to be installed in the target host.
* t -- *Theme checks*: As above, but for themes.
* v -- *Version checks*: Downloads several files and, based on the checksums of these
files, returns a list of all possible versions.
* i -- *Interesting url checks*: Checks for interesting urls (admin panels, readme
files, etc.)

More notes regarding scanning can be [found here](https://droope.github.io/droopescan-docs/_build/html/intro.html).

## Target specification.

You can specify a particular host to scan by passing the `-u` or `--url`
parameter:

<pre>
    droopescan scan drupal -u example.org
</pre>

You can also omit the `drupal` argument. This will trigger “CMS identification”, like so:

<pre>
    droopescan scan -u example.org
</pre>

Multiple URLs may be scanned utilising the `-U` or `--url-file` parameter. This
parameter should be set to the path of a file which contains a list of URLs. 

<pre>
    droopescan scan drupal -U list_of_urls.txt
</pre>

The `drupal` parameter may also be ommited in this example. For each site, it
will make several GET requests in order to perform CMS identification, and if
the site is deemed to be a supported CMS, it is scanned and added to the output
list. This can be useful, for example, to run `droopescan` across all your
organisation's sites.

<pre>
    droopescan scan -U list_of_urls.txt
</pre>

The code block below contains an example list of URLs, one per line:

<pre>
http://localhost/drupal/6.0/
http://localhost/drupal/6.1/
http://localhost/drupal/6.10/
http://localhost/drupal/6.11/
http://localhost/drupal/6.12/
</pre>

A file containing URLs and a value to override the default host header with
separated by tabs or spaces is also OK for URL files. This can be handy when
conducting a scan through a large range of hosts and you want to prevent
unnecessary DNS queries. To clarify, an example below:

<pre>
192.168.1.1	example.org
http://192.168.1.1/	example.org
http://192.168.1.2/drupal/	example.org
</pre>

It is quite tempting to test whether the scanner works for a particular CMS
by scanning the official site (e.g. `wordpress.org` for wordpress), but the
official sites rarely run vainilla installations of their respective CMS or do
unorthodox things. For example, `wordpress.org` runs the bleeding edge version of
wordpress, which will not be identified as wordpress by `droopescan` at all
because the checksums do not match any known wordpress version.

## Authentication.

The application fully supports `.netrc` files and `http_proxy` environment
variables.

Use a .netrc file for basic authentication. An example [netrc](https://www.gnu.org/software/inetutils/manual/html_node/The-_002enetrc-file.html) (a file named
`.netrc` placed in your root home directory) file could look as follows:

<pre>
machine secret.google.com
    login admin@google.com
    password Winter01
</pre>

You can set the `http_proxy` and `https_proxy` variables. These allow you to
set a parent HTTP proxy, in which you can handle more complex types of
authentication (e.g. Fiddler, ZAP, Burp)

<pre>
export http_proxy='user:password@localhost:8080'
export https_proxy='user:password@localhost:8080'
droopescan scan drupal --url http://localhost/drupal
</pre>

*WARNING:* By design, to allow intercepting proxies and the testing of
applications with bad SSL, droopescan allows self-signed or otherwise invalid
certificates. ˙ ͜ʟ˙

## Output.

This application supports both "standard output", meant for human consumption,
or JSON, which is more suitable for machine consumption. This output is stable
between major versions.

This can be controlled with the `--output` flag. Some sample JSON output would
look as follows (minus the excessive whitespace):

<pre>
{
  "themes": {
    "is_empty": true,
    "finds": [

    ]
  },
  "interesting urls": {
    "is_empty": false,
    "finds": [
      {
        "url": "https:\/\/www.drupal.org\/CHANGELOG.txt",
        "description": "Default changelog file."
      },
      {
        "url": "https:\/\/www.drupal.org\/user\/login",
        "description": "Default admin."
      }
    ]
  },
  "version": {
    "is_empty": false,
    "finds": [
      "7.29",
      "7.30",
      "7.31"
    ]
  },
  "plugins": {
    "is_empty": false,
    "finds": [
      {
        "url": "https:\/\/www.drupal.org\/sites\/all\/modules\/views\/",
        "name": "views"
      },
      [...snip...]
    ]
  }
}
</pre>

Some attributes might be missing from the JSON object if parts of the scan are
not ran.

This is how multi-site output looks like; each line contains a valid JSON object
as shown above.

<pre>
    $ droopescan scan drupal -U six_and_above.txt -e v
    {"host": "http://localhost/drupal-7.6/", "version": {"is_empty": false, "finds": ["7.6"]}}
    {"host": "http://localhost/drupal-7.7/", "version": {"is_empty": false, "finds": ["7.7"]}}
    {"host": "http://localhost/drupal-7.8/", "version": {"is_empty": false, "finds": ["7.8"]}}
    {"host": "http://localhost/drupal-7.9/", "version": {"is_empty": false, "finds": ["7.9"]}}
    {"host": "http://localhost/drupal-7.10/", "version": {"is_empty": false, "finds": ["7.10"]}}
    {"host": "http://localhost/drupal-7.11/", "version": {"is_empty": false, "finds": ["7.11"]}}
    {"host": "http://localhost/drupal-7.12/", "version": {"is_empty": false, "finds": ["7.12"]}}
    {"host": "http://localhost/drupal-7.13/", "version": {"is_empty": false, "finds": ["7.13"]}}
    {"host": "http://localhost/drupal-7.14/", "version": {"is_empty": false, "finds": ["7.14"]}}
    {"host": "http://localhost/drupal-7.15/", "version": {"is_empty": false, "finds": ["7.15"]}}
    {"host": "http://localhost/drupal-7.16/", "version": {"is_empty": false, "finds": ["7.16"]}}
    {"host": "http://localhost/drupal-7.17/", "version": {"is_empty": false, "finds": ["7.17"]}}
    {"host": "http://localhost/drupal-7.18/", "version": {"is_empty": false, "finds": ["7.18"]}}
    {"host": "http://localhost/drupal-7.19/", "version": {"is_empty": false, "finds": ["7.19"]}}
    {"host": "http://localhost/drupal-7.20/", "version": {"is_empty": false, "finds": ["7.20"]}}
    {"host": "http://localhost/drupal-7.21/", "version": {"is_empty": false, "finds": ["7.21"]}}
    {"host": "http://localhost/drupal-7.22/", "version": {"is_empty": false, "finds": ["7.22"]}}
    {"host": "http://localhost/drupal-7.23/", "version": {"is_empty": false, "finds": ["7.23"]}}
    {"host": "http://localhost/drupal-7.24/", "version": {"is_empty": false, "finds": ["7.24"]}}
    {"host": "http://localhost/drupal-7.25/", "version": {"is_empty": false, "finds": ["7.25"]}}
    {"host": "http://localhost/drupal-7.26/", "version": {"is_empty": false, "finds": ["7.26"]}}
    {"host": "http://localhost/drupal-7.27/", "version": {"is_empty": false, "finds": ["7.27"]}}
    {"host": "http://localhost/drupal-7.28/", "version": {"is_empty": false, "finds": ["7.28"]}}
    {"host": "http://localhost/drupal-7.29/", "version": {"is_empty": false, "finds": ["7.29"]}}
    {"host": "http://localhost/drupal-7.30/", "version": {"is_empty": false, "finds": ["7.30"]}}
    {"host": "http://localhost/drupal-7.31/", "version": {"is_empty": false, "finds": ["7.31"]}}
    {"host": "http://localhost/drupal-7.32/", "version": {"is_empty": false, "finds": ["7.32"]}}
    {"host": "http://localhost/drupal-7.33/", "version": {"is_empty": false, "finds": ["7.33"]}}
    {"host": "http://localhost/drupal-7.34/", "version": {"is_empty": false, "finds": ["7.34"]}}
</pre>

## Debug.

When things are not going exactly your way, you can check why by using the
`--debug-requests` command.

Some output might look like this:

<pre>
computer:~/droopescan# droopescan scan silverstripe -u http://localhost -n 10 -e p --debug-requests
[head] http://localhost/framework/... 403
[head] http://localhost/cms/css/layout.css... 404
[head] http://localhost/framework/css/UploadField.css... 200
[head] http://localhost/misc/test/error/404/ispresent.html... 404
[head] http://localhost/widgetextensions/... 404
[head] http://localhost/orbit/... 404
[head] http://localhost/sitemap/... 404
[head] http://localhost/simplestspam/... 404
[head] http://localhost/ecommerce_modifier_example/... 404
[head] http://localhost/silverstripe-hashpath/... 404
[head] http://localhost/timeline/... 404
[head] http://localhost/silverstripe-hiddenfields/... 404
[head] http://localhost/addressable/... 404
[head] http://localhost/silverstripe-description/... 404
[+] No plugins found.

[+] Scan finished (0:00:00.058422 elapsed)
</pre>

The `--debug` paramter also exists and may be used to debug application internals.

## Stats.

You can get an up to date report on the capabilities of the scanner by running
the following command

<pre>
    droopescan stats
</pre>

Some sample output might look as follows:

<pre>
Functionality available for ‘drupal’:
- Enumerate plugins (XXXX plugins.)
- Enumerate themes (XXXX themes.)
- Enumerate interesting urls (X urls.)
- Enumerate version (up to version X.X.X-alphaXX, X.XX, X.XX.)
Functionality available for ‘joomla’:
- Enumerate interesting urls (X urls.)
- Enumerate version (up to version XX.X, X.X.X, X.X.XX.rcX.)
Functionality available for ‘wordpress’:
- Enumerate interesting urls (X urls.)
- Enumerate version (up to version X.X.X, X.X.X, X.X.X.)
Functionality available for ‘silverstripe’:
- Enumerate plugins (XXX plugins.)
- Enumerate themes (XX themes.)
- Enumerate interesting urls (X urls.)
- Enumerate version (up to version X.X.XX, X.X.XX, X.X.XX.)
</pre>

It is important to verify that the latest version available for the CMS
installation is available within `droopescan`, as otherwise results may be
inaccurate.

# Contribute.

## Create your own plugin.

You can add suport for your favourite CMS. The process is actually quite
simple, and a lot of information can be glimpsed by viewing the example.py file
in the plugins/ folder.

This file should serve well as a base for your implementation.

You can create your own plugin for `Joomla` and enable it as follows:

<pre>
$ cp plugins/example.py plugins/joomla.py
$ cp plugins.d/example.conf plugins.d/joomla.conf
</pre>

You then need to go to `plugins/joomla.py` and change a few things:

- The class name needs to be Joomla.
- The plugin label (located at Meta.label) needs to be changed to joomla.
- At the end of the file, the register call needs to be modified to reflect the
  correct class name.
- The exposed function, 'example', needs to be renamed to joomla.

<pre>
    @controller.expose(help='example scanner')
    def joomla(self):
        self.plugin_init()
</pre>

We also need to change the `plugins.d/joomla.conf` file, and change it to the
following:

<pre>
[joomla]
enable_plugin = true
</pre>

We should now be in a state which looks as follows:

<pre>
$ droopescan scan joomla
[+] --url parameter is required.
</pre>

Your next step would be to generate a valid plugin wordlist, a valid theme
wordlist, a
[versions.xml](https://github.com/droope/droopescan/blob/development/plugins/drupal/versions.xml)
file, and optionally a list of interesting URLs, as well as replace all variables
that are in joomla.py with values that are correct for your implementation.

The plugin needs to update automatically in order for a pull request to be
accepted. Further documentation may be later made available, but for now, keep
in mind that the update_version_check, update_version, update_plugins_check and
update_plugins need to be implemented. For reference, please review the
`drupal.py` file. This is required in order to ensure plugins are kept to date.

## Issues & Pull Requests.

Pull requests that create new plugins are welcome provided that maintenance for
those plugins is done automatically.

Please remember to make your pull requests against the develoment branch
rather than the master. Issues can be raised on the issue tracker here
on GitHub.

To run tests, some dependencies must be installed. Running the following
commands will result in them being installed and the tests being ran:

<pre>
    apt-get install libxslt1-dev libxml2-dev zlib1g-dev python python-pip python-dev python3 python3-pip python3-dev
    pip install -r requirements.txt -r requirements_test.txt
    pip3 install -r requirements.txt -r requirements_test.txt
    ./droopescan test
</pre>

You can run individual tests with the `-s` flag.

<pre>
./droopescan test -s test_integration_drupal
</pre>

# License.

The project is licensed under the AGPL license.
