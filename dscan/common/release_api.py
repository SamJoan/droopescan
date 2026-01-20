from __future__ import print_function

def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are: y, yes, t, true, on, 1
    False values are: n, no, f, false, off, 0
    Raises ValueError if 'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))
import dscan.common.functions as f
import dscan
import os.path
import subprocess
import sys
import tempfile

CHANGELOG = './CHANGELOG'
TEST_RUNS_BASE = ['./droopescan']
TEST_RUNS_APPEND = ['-n', '100']
TEST_RUNS = [
        ['scan', 'drupal', '--url', 'https://www.arse'+'nal.com', '-t', '30'],
        ['scan', 'silverstripe', '--url', 'https://www.opens'+ 'tack.org/', '-t', '2'],
        ['scan', 'wordpress', '--url', 'http://wordpress.org/', '-t', '30'],
        ['scan', 'joomla', '--url', 'http://www.joomla.org/', '-t', '30'],
        ['scan', 'moodle', '--url', 'http://2016mini.im' + 'oot.org/', '-t', '10']
    ]

def test_all(skip_external):
    """
    Runs several tests (unit, integration, and sanity checks.)
    @param skip_external: whether to run external tests.
    @raises RuntimeError: if tests fail.
    """
    test_internal()
    if not skip_external:
        test_external()

    test_human()

def test_internal():
    """
    Runs unit tests.
    """
    tests_passed = subprocess.call(['./droopescan', 'test']) == 0
    if not tests_passed:
        f.error("Unit tests failed... abort.")

def test_external():
    """
    Runs tests against known sites. Only exits on catastrophic failure.
    """
    external_passed = _scan_external()
    if not external_passed:
        f.error("External scans failed... abort.")

def _scan_external():
    for run in TEST_RUNS:
        args = TEST_RUNS_BASE + run + TEST_RUNS_APPEND
        ret_code = subprocess.call(args)
        if ret_code != 0:
            return False

    return True

def test_human():
    """
    Final human sanity check.
    """
    human_approves = confirm("Does that look OK for you?")
    if not human_approves:
        f.error("Cancelled by user.")

def changelog(version):
    header = '%s\n%s\n\n*' % (version, ('='*len(version)))
    with tempfile.NamedTemporaryFile(mode='w+t', suffix=".tmp") as temp:
      temp.write(header)

      temp.flush()
      subprocess.call(['vim', temp.name])

      return header + temp.read()

def changelog_modify():
    prev_version_nb = read_first_line(CHANGELOG)
    version_nb = get_input("Version number (prev %s):" %
            prev_version_nb)

    final = changelog(version_nb).strip() + "\n\n"

    print("The following will be prepended to the CHANGELOG:\n---\n%s---" % final)

    ok = confirm("Is that OK?")
    if ok:
        prepend_to_file(CHANGELOG, final)
        return version_nb
    else:
        f.error("Cancelled by user.")

def get_input(question):
    print(question, end=' ')
    try:
        inp =  raw_input()
    except NameError:
        inp = input()

    return inp

def confirm(question):
    sys.stdout.write('%s [y/n]\n' % question)
    while True:
        try:
            try:
                user_input = raw_input().lower()
            except NameError:
                user_input = input().lower()

            return strtobool(user_input)
        except ValueError:
            sys.stdout.write('Please respond with \'y\' or \'n\'.\n')

def check_pypirc():
    pypirc = os.path.expanduser("~/.pypirc")
    if not os.path.isfile(pypirc):
        f.error('File "%s" does not exist.' % pypirc)

def read_first_line(file):
    with open(file, 'r') as f:
      first_line = f.readline()

    return first_line.strip()

def prepend_to_file(filename, prepend_text):
    f = open(filename, 'r')
    temp = f.read()
    f.close()

    f = open(filename, 'w')
    f.write(prepend_text)

    f.write(temp)
    f.close()
