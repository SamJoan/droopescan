import common.functions as f
import os.path
import subprocess

CHANGELOG = '../CHANGELOG'
TEST_RUNS_BASE = ['../droopescan']
TEST_RUNS_APPEND = ['-n', '100', '-t', '2']
TEST_RUNS = [['scan', 'drupal', '--url', 'https://www.drupal.org'],
        ['scan', 'silverstripe', '--url', 'http://demo.silverstripe.org']]

def test_all(skip_external):
    """
        Runs several tests (unit, integration, and sanity checks.)
        @param skip_external whether to run external tests.
        @raises RuntimeError if tests fail.
    """
    test_internal()
    if not skip_external:
        test_external()

    test_human()

def test_internal():
    """
        Runs unit tests.
    """
    tests_passed = subprocess.call(['../droopescan', 'test']) == 0
    if not tests_passed:
        f.error("Unit tests failed... abort.")

def test_external():
    """
        Runs tests against known sites. Only exits on catastrophic failure.
    """
    external_passed = _scan_external()
    if not external_passed:
        f.error("External scans failed... abort.")

def test_human():
    """
        Final human sanity check.
    """
    human_approves = confirm("Does that look OK for you?")
    if not human_approves:
        f.error("Cancelled by user.")

def confirm(self, question):
    sys.stdout.write('%s [y/n]\n' % question)
    while True:
        try:
            user_input = raw_input().lower()
            return strtobool(user_input)
        except ValueError:
            sys.stdout.write('Please respond with \'y\' or \'n\'.\n')

def _scan_external():
    for run in TEST_RUNS:
        args = TEST_RUNS_BASE + run + TEST_RUNS_APPEND
        ret_code = subprocess.call(args)
        if ret_code != 0:
            return False

    return True

def check_pypirc():
    pypirc = os.path.expanduser("~/.pypirc")
    if not os.path.isfile(pypirc):
        f.error('File "%s" does not exist.' % pypirc)

def read_first_line(file):
    print(__name__)
    with open(file, 'r') as f:
      first_line = f.readline()

    return first_line.strip()

def changelog(self, version):
    header = '%s\n%s\n\n*' % (version, ('='*len(version)))
    with tempfile.NamedTemporaryFile(suffix=".tmp") as temp:
      temp.write(header)
      temp.flush()
      call(['vim', temp.name])

      return header + temp.read() + "\n"

def changelog_modify():
    prev_version_nb = read_first_line(CHANGELOG)
    version_nb = self.get_input("Version number (prev %s):" %
            prev_version_nb)

    final = self.changelog(version_nb).strip() + "\n\n"

    print("The following will be prepended to the CHANGELOG:\n---\n%s---" % final)

    ok = self.confirm("Is that OK?")
    if ok:
        self.prepend_to_file(CHANGELOG, final)
    else:
        f.error("Cancelled by user.")
