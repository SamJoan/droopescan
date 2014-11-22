# A CMS Scanning Tool.

Stable versions can be [found here](https://github.com/droope/droopescan/releases).

[![Build Status](https://travis-ci.org/droope/droopescan.svg?branch=master)](https://travis-ci.org/droope/droopescan)

Usage:

<pre>
python droopescan.py scan drupal --url http://localhost/drupal-7.28
python droopescan.py scan silverstripe --url http://localhost/silverstripe
</pre>

You can get a full list of options by running:

<pre>
python droopescan.py --help
python droopescan.py scan --help
</pre>

# Dependencies.

In order to run this tool you need to install a few dependencies. These can be
installed by running the following command:

<pre>
pip install -r requirements.txt
</pre>

# Scan types.

Droopescan aims to be the most aggressive by default, while not overloading the
target server due to excessive requests. Due to this, by default, a large number
of requests will be made with four threads; you can increase this default by
using the `--threads` argument.

This tool is able to perform four kinds of tests:

* Plugin checks: Performs several hundred requests and returns a listing of all
plugins found to be installed in the target host.
* Theme checks: As above, but for themes.
* Version checks: Downloads several files and, based on the checksums of these
files, returns a list of all possible versions. 
* Interesting url checks: Checks for interesting urls (admin panels, readme
files, etc.)

# Authentication.

The application fully supports `.netrc` files and `http_proxy` environment
variables. 

You can set `http_proxy` and `https_proxy` variables. These allow you to
set a parent HTTP proxy, in which you can handle more complex types of
authentication (e.g. Fiddler, ZAP)

<pre>
export http_proxy='localhost:8080'
export https_proxy='localhost:8080'
python droopescan.py drupal --url http://localhost/drupal
</pre>

Another option is to use a .netrc file. An example `~/.netrc` file could look
as follows:

<pre>
machine secret.google.com
    login pedro.worcel@security-assessment.com
    password Winter01
</pre>

*WARNING:* By design, to allow intercepting proxies, this application allows
self-signed or otherwise invalid certificates. ˙ ͜ʟ˙

# Output.

This application supports both "standard output", meant for human consumption,
or JSON, which is more suitable for machine consumption.

This can be controlled with the `--output` flag, and some sample JSON output
would look as follows:

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

Scan types might be missing from the output if they are not scanned. 

This is how multi-site output looks like; each line contains a valid JSON object
as described above.

<pre>
    $ ./droopescan scan drupal -U six_and_above.txt -e v
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

# Stats.

You can get an up to date report on the capabilities of the scanner by running
the following command

<pre>
    ./droopescan stats
</pre>

Some sample output might look as follows:

<pre>
Functionality available for 'Drupal':
    - Enumerate plugins (XXX plugins, last updated X months ago)
    - Enumerate themes (XX themes, last updated X months ago)
    - Enumerate interesting urls (X urls)
    - Enumerate version (up to version X.X.X)

Functionality available for 'SilverStripe':
    - Enumerate plugins (XXX plugins, last updated X months ago)
    - Enumerate themes (XX themes, last updated X months ago)
    - Enumerate interesting urls (X urls)
    - Enumerate version (up to version X.X.X)
</pre>

# Testing.

To run tests, some dependencies can be installed; running the following
commands will result in them being installed and the tests being ran:

<pre>
    apt-get install python-dev libxslt1-dev libxml2-dev
    pip install -r requirements_test.txt
    ./droopescan test
</pre>

Tests which interact with the internet can be ran with the following command:

<pre>
    ./droopescan test -i
</pre>
