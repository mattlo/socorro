
import errno
import logging
import os
import urllib2

import psycopg2

import unittest
from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util
import socorro.lib.psycopghelper as psy
import socorro.cron.ftpscraper as ftpscraper
import socorro.database.schema as sch

from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.util as tutil
import socorro.unittest.testlib.expectations as exp

import cronTestconfig as testConfig

def makeBogusBuilds(connection, cursor):
  # (product, version, platform, buildid, changeset, filename, date)
  fakeBuildsData = [ ("PRODUCTNAME1", "VERSIONAME1", "PLATFORMNAME1", "1", "BUILDTYPE1", "1", "REPO1"),
                     ("PRODUCTNAME2", "VERSIONAME2", "PLATFORMNAME2", "2", "BUILDTYPE2", "2", "REPO2"),
                     ("PRODUCTNAME3", "VERSIONAME3", "PLATFORMNAME3", "3", "BUILDTYPE3", "3", "REPO3"),
                     ("PRODUCTNAME4", "VERSIONAME4", "PLATFORMNAME4", "4", "BUILDTYPE4", "4", "REPO4")
                   ]

  for b in fakeBuildsData:
    try:
      cursor.execute("INSERT INTO releases_raw (product_name, version, platform, build_id, build_type, beta_number, repository) values (%s, %s, %s, %s, %s, %s, %s)", b)
      connection.commit()
    except Exception, x:
      print "Exception at makeBogusBuilds() releases_raw insert", type(x),x
      connection.rollback()


class Me:
  """
  I need stuff to be initialized once per module. Rather than having a bazillion globals, lets just have 'me'
  """
  pass
me = None

def setup_module():
  global me
  if me:
    return
  me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing ftpscraper')
  tutil.nosePrintModule(__file__)
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  me.logFilePathname = me.config.logFilePathname
  if not me.logFilePathname:
    me.logFilePathname = 'logs/ftpscraper_test.log'
  logFileDir = os.path.split(me.logFilePathname)[0]
  try:
    os.makedirs(logFileDir)
  except OSError,x:
    if errno.EEXIST == x.errno: pass
    else: raise
  f = open(me.logFilePathname,'w')
  f.close()
  fileLog = logging.FileHandler(me.logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  fileLog.setFormatter(fileLogFormatter)
  me.fileLogger = logging.getLogger("ftpscraper")
  me.fileLogger.addHandler(fileLog)
  # Got trouble?  See what's happening by uncommenting the next three lines
  #stderrLog = logging.StreamHandler()
  #stderrLog.setLevel(10)
  #me.fileLogger.addHandler(stderrLog)

  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)
  me.testDB = TestDB()
  me.testDB.removeDB(me.config,me.fileLogger)
  me.testDB.createDB(me.config,me.fileLogger)
  try:
    me.conn = psycopg2.connect(me.dsn)
    me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
  except Exception, x:
    print "Exception in setup_module() connecting to database ... Error: ",type(x),x
    socorro.lib.util.reportExceptionAndAbort(me.fileLogger)
  makeBogusBuilds(me.conn, me.cur)

def teardown_module():
  global me
  me.testDB.removeDB(me.config,me.fileLogger)
  me.conn.close()
  try:
    os.unlink(me.logFilePathname)
  except:
    pass

class TestBuilds(unittest.TestCase):
  def setUp(self):
    global me
    self.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing ftpscraper')

    myDir = os.path.split(__file__)[0]
    if not myDir: myDir = '.'
    replDict = {'testDir':'%s'%myDir}
    for i in self.config:
      try:
        self.config[i] = self.config.get(i)%(replDict)
      except:
        pass
    self.logger = TestingLogger(me.fileLogger)

    self.testConfig = configurationManager.Config([('t','testPath', True, './TEST-BUILDS', ''),
                                                   ('f','testFileName', True, 'lastrun.pickle', ''),
                                                  ])
    self.testConfig["persistentDataPathname"] = os.path.join(self.testConfig.testPath, self.testConfig.testFileName)


  def tearDown(self):
    self.logger.clear()

  def do_buildExists(self, d, correct):
    me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
    me.cur.setLogger(me.fileLogger)

    actual = ftpscraper.buildExists(me.cur, d[0], d[1], d[2], d[3], d[4], d[5], d[6])
    assert actual == correct, "expected %s, got %s " % (correct, actual)
    print actual, correct
    print 'here1'

  def test_buildExists(self):
    d = ( "failfailfail", "VERSIONAME1", "PLATFORMNAME1", "1", "BUILDTYPE1", "1", "REPO1")
    self.do_buildExists(d, False)
    r = ( "PRODUCTNAME1", "VERSIONAME1", "PLATFORMNAME1", "1", "BUILDTYPE1", "1", "REPO1")
    self.do_buildExists(r, True)

  def test_insertBuild(self):
    me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
    me.cur.setLogger(me.fileLogger)

    me.cur.execute("DELETE FROM releases_raw WHERE product_name = 'PRODUCTNAME5'")
    me.cur.connection.commit()

    try:
      ftpscraper.insertBuild(me.cur, 'PRODUCTNAME5', 'VERSIONAME5', 'PLATFORMNAME5', '5', 'BUILDTYPE5', '5', 'REPO5')
      actual = ftpscraper.buildExists(me.cur, 'PRODUCTNAME5', 'VERSIONAME5', 'PLATFORMNAME5', '5', 'BUILDTYPE5', '5', 'REPO5')
      assert actual == 1, "expected 1, got %s" % (actual)
    except Exception, x:
      print "Exception in do_insertBuild() ... Error: ",type(x),x
      socorro.lib.util.reportExceptionAndAbort(me.fileLogger)

    me.cur.connection.rollback()

  def test_getLinks(self):
    print ftpscraper.getLinks('http://')
    assert True == False

  def test_parseInfoFile(self):
    print ftpscraper.parseInfoFile('http://', nightly=True)

  def test_getRelease(self):
    print ftpscraper.parseRelease('dir', 'http://')

  def test_getNightly(self):
    print ftpscraper.getNightly('dir', 'http://')

  def test_getNightly(self):
    print ftpscraper.getNightly('dir', 'http://')

  def test_recordBuilds(self):
    print ftpscraper.recordBuilds(me.config)

  def test_scrape(self):
    self.config.products = ('PRODUCT1', 'PRODUCT2')
    self.config.base_url = 'http://www.example.com/'
    print ftpscraper.scrape(self.config, me.cur)

#  def test_fetchTextFiles(self):
#    self.config.base_url = 'http://www.example.com/'
#    self.config.platforms = ('platform1', 'platform2')
#    fake_product_uri = 'firefox/nightly/latest-mozilla-1.9.1/'
#
#    fake_response_url = "%s%s" % (self.config.base_url, fake_product_uri)
#    fake_response_contents = """
#       blahblahblahblahblah
#       <a href="product1-version1.en-US.platform1.txt">product1-version1.en-US.platform1.txt</a>
#       <a href="product1-version1.en-US.platform1.zip">product1-version1.en-US.platform1.zip</a>
#       <a href="product2-version2.en-US.platform2.txt">product2-version2.en-US.platform2.txt</a>
#       <a href="product2-version2.en-US.platform2.zip">product2-version2.en-US.platform2.zip</a>
#       blahblahblahblahblah
#    """
#    fake_response_success_1 = {'platform':'platform1', 'product':'product1', 'version':'version1', 'filename':'product1-version1.en-US.platform1.txt'}
#    fake_response_success_2 = {'platform':'platform2', 'product':'product2', 'version':'version2', 'filename':'product2-version2.en-US.platform2.txt'}
#    fake_response_successes = (fake_response_success_1, fake_response_success_2)
#
#    fakeResponse = exp.DummyObjectWithExpectations()
#    fakeResponse.code = 200
#    fakeResponse.expect('read', (), {}, fake_response_contents)
#    fakeResponse.expect('close', (), {})
#
#    fakeUrllib2 = exp.DummyObjectWithExpectations()
#    fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)
#
#    try:
#      actual = ftpscraper.fetchTextFiles(self.config, fake_product_uri, self.config.platforms, ftpscraper.buildParser(), fakeUrllib2)
#      assert actual['url'] == fake_response_url, "expected %s, got %s " % (fake_response_url, actual['url'])
#      assert actual['builds'][0] == fake_response_success_1, "expected %s, got %s " % (fake_response_success_1, actual['builds'][0])
#      assert actual['builds'][1] == fake_response_success_2, "expected %s, got %s " % (fake_response_success_2, actual['builds'][1])
#    except Exception, x:
#      print "Exception in test_fetchTextFiles() ... Error: ",type(x),x
#      socorro.lib.util.reportExceptionAndAbort(me.fileLogger)


if __name__ == "__main__":
  unittest.main()
