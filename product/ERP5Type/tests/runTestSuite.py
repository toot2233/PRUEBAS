#!/usr/bin/env python2.7
from __future__ import print_function
from __future__ import absolute_import
import argparse, sys, os, textwrap
from erp5.util import taskdistribution

# XXX: This import is required, just to populate sys.modules['test_suite'].
# Even if it's not used in this file. Yuck.
from . import ERP5TypeTestSuite

def _parsingErrorHandler(data, _):
  print('Error parsing data:', repr(data), file=sys.stderr)
taskdistribution.patchRPCParser(_parsingErrorHandler)

def makeSuite(
    node_quantity=None,
    test_suite=None,
    revision=None,
    db_list=None,
    zserver_address_list=None,
    zserver_frontend_url_list=None,
    **kwargs):
  # BBB tests (plural form) is only checked for backward compatibility
  for k in list(sys.modules.keys()):
    if k in ('tests', 'test',) or k.startswith('tests.') or k.startswith('test.'):
      del sys.modules[k]
  singular_succeed = True
  while True:
    module_name, class_name = ('%s.%s' % (singular_succeed and 'test' or 'tests',
                                          test_suite)).rsplit('.', 1)
    try:
      suite_class = getattr(__import__(module_name, None, None, [class_name]),
                            class_name)
    except (AttributeError, ImportError):
      if not singular_succeed:
        raise
      singular_succeed = False
    else:
      break
  suite = suite_class(revision=revision,
                      max_instance_count=node_quantity,
                      mysql_db_list=db_list.split(','),
                      zserver_address_list=zserver_address_list,
                      zserver_frontend_url_list=zserver_frontend_url_list,
                      **kwargs)
  return suite

def main():
  parser = argparse.ArgumentParser(
      description='Run a test suite.',
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog=textwrap.dedent('''
      Tips:

        Running a full test suite on a development machine can be achieved with:

          %(prog)s --node_quantity=3 --test_suite=ERP5 --xvfb_bin=/path/to/Xvfb --firefox_bin=/path/to/firefox
      '''))

  # Parameters included in wrappers generated by SlapOS ERP5 software release.
  # To handle backward compatibity, we prefer that the generated wrapper pass
  # these parameters as environment variables. This way, if SlapOS SR is more
  # recent, the parameter will be ignored by ERP5.
  slapos_wrapper_group = parser.add_argument_group(
      'SlapOS wrapper arguments',
      description='Arguments passed automatically by SlapOS generated wrapper')
  slapos_wrapper_group.add_argument('--db_list', help='A list of comma separated sql connection strings')
  slapos_wrapper_group.add_argument('--conversion_server_url', default=None)
  slapos_wrapper_group.add_argument('--conversion_server_retry_count', default=None)
  slapos_wrapper_group.add_argument('--conversion_server_hostname', default=None)
  slapos_wrapper_group.add_argument('--conversion_server_port', default=None)
  slapos_wrapper_group.add_argument('--volatile_memcached_server_hostname', default=None)
  slapos_wrapper_group.add_argument('--volatile_memcached_server_port', default=None)
  slapos_wrapper_group.add_argument('--persistent_memcached_server_hostname', default=None)
  slapos_wrapper_group.add_argument('--persistent_memcached_server_port', default=None)
  slapos_wrapper_group.add_argument('--bt5_path', default=None)
  slapos_wrapper_group.add_argument(
      '--zserver_address_list',
      help='A list of comma seperated host:port for ZServer.\n'
      'Also taken from zserver_address_list environment variable.',
      default=os.getenv('zserver_address_list', ''))
  slapos_wrapper_group.add_argument(
      '--zserver_frontend_url_list',
      help='A list of comma seperated frontend URLs, one for each of zserver_address_list,'
      'in the same order.\nAlso taken from zserver_frontend_url_list environment variable',
      default=os.getenv('zserver_frontend_url_list', ''))

  # Parameters passed by test node
  testnode_group = parser.add_argument_group(
      'test node arguments',
      description='Arguments passed by testnode')
  testnode_group.add_argument('--test_suite', help='The test suite name')
  testnode_group.add_argument('--test_suite_title', help='The test suite title',
                      default=None)
  testnode_group.add_argument('--test_node_title', help='The test node title',
                      default=None)
  testnode_group.add_argument('--project_title', help='The project title',
                      default=None)
  testnode_group.add_argument('--revision', help='The revision to test',
                      default='dummy_revision')
  testnode_group.add_argument('--node_quantity', help='Number of parallel tests to run',
                      default=1, type=int)
  testnode_group.add_argument('--master_url',
                      help='The Url of Master controling many suites',
                      default=None)
  testnode_group.add_argument("--xvfb_bin", default=None)
  testnode_group.add_argument("--firefox_bin", default=None)
  testnode_group.add_argument("--log_directory", default=None)

  args = parser.parse_args()
  if args.bt5_path is not None:
    sys.path[0:0] = args.bt5_path.split(",")
  master = taskdistribution.TaskDistributor(args.master_url)
  test_suite_title = args.test_suite_title or args.test_suite
  revision = args.revision

  args.zserver_address_list = (
      args.zserver_address_list.split(',') if args.zserver_address_list else ())
  args.zserver_frontend_url_list = (
      args.zserver_frontend_url_list.split(',') if args.zserver_frontend_url_list else ())

  if args.zserver_address_list and len(args.zserver_address_list) < args.node_quantity:
    print('Not enough zserver address/frontends for node quantity %s (%r)' % (
        args.node_quantity, args.zserver_address_list), file=sys.stderr)
    sys.exit(1)

  # sanity check
  assert len(args.zserver_address_list) == len(args.zserver_frontend_url_list)

  suite = makeSuite(test_suite=args.test_suite,
                    node_quantity=args.node_quantity,
                    revision=revision,
                    db_list=args.db_list,
                    zserver_address_list=args.zserver_address_list,
                    zserver_frontend_url_list=args.zserver_frontend_url_list,
                    bt5_path=args.bt5_path,
                    firefox_bin=args.firefox_bin,
                    xvfb_bin=args.xvfb_bin,
                    log_directory=args.log_directory)
  test_result = master.createTestResult(revision, suite.getTestList(),
    args.test_node_title, suite.allow_restart, test_suite_title,
    args.project_title)
  if test_result is not None:
    assert revision == test_result.revision, (revision, test_result.revision)
    while suite.acquire():
      test = test_result.start(list(suite.running.keys()))
      if test is not None:
        suite.start(test.name, lambda status_dict, __test=test:
          __test.stop(**status_dict))
      elif not suite.running:
        break
