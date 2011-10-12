
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

from     socorro.unittest.testlib.loggerForTest import TestingLogger
from     socorro.unittest.testlib.testDB import TestDB
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
    # Got trouble?    See what's happening by uncommenting the next three lines
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
        self.config.products = ('PRODUCT1', 'PRODUCT2')
        self.config.base_url = 'http://www.example.com/'

        fake_response_url = "%s%s" % (self.config.base_url, self.config.products[0])
        fake_response_contents = """
             blahblahblahblahblah
             <a href="product1-version1.en-US.platform1.txt">product1-version1.en-US.platform1.txt</a>
             <a href="product1-version1.en-US.platform1.zip">product1-version1.en-US.platform1.zip</a>
             <a href="product2-version2.en-US.platform2.txt">product2-version2.en-US.platform2.txt</a>
             <a href="product2-version2.en-US.platform2.zip">product2-version2.en-US.platform2.zip</a>
             blahblahblahblahblah
        """

        fakeResponse = exp.DummyObjectWithExpectations()
        fakeResponse.code = 200
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('close', (), {})

        fakeUrllib2 = exp.DummyObjectWithExpectations()
        fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)

        actual = ftpscraper.getLinks('http://www.example.com/PRODUCT1', startswith='product1', urllib=fakeUrllib2)
        expected = [u'product1-version1.en-US.platform1.txt', u'product1-version1.en-US.platform1.zip']
        assert actual == expected, "expected %s, got %s" % (expected, actual)

        fakeResponse = exp.DummyObjectWithExpectations()
        fakeResponse.code = 200
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('close', (), {})

        fakeUrllib2 = exp.DummyObjectWithExpectations()
        fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)

        expected = [u'product1-version1.en-US.platform1.zip', u'product2-version2.en-US.platform2.zip']
        actual= ftpscraper.getLinks('http://www.example.com/PRODUCT1', endswith='.zip', urllib=fakeUrllib2)
        assert actual == expected, "expected %s, got %s" % (expected, actual)

    def test_parseInfoFile(self):
        self.config.products = ('PRODUCT1', 'PRODUCT2')
        self.config.base_url = 'http://www.example.com/'

        fake_response_url = "%s%s" % (self.config.base_url, self.config.products[0])
        fake_response_contents = """
            20111011042016
            http://hg.mozilla.org/releases/mozilla-aurora/rev/327f5fdae663
        """

        fakeResponse = exp.DummyObjectWithExpectations()
        fakeResponse.code = 200
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('close', (), {})

        fakeUrllib2 = exp.DummyObjectWithExpectations()
        fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)

        expected = {'buildID': '20111011042016', 'rev': 'http://hg.mozilla.org/releases/mozilla-aurora/rev/327f5fdae663'}
        actual = ftpscraper.parseInfoFile('http://www.example.com/PRODUCT1', nightly=True, urllib=fakeUrllib2)
        assert actual == expected, "expected %s, got %s" % (expected, actual)

        fake_response_contents = """
            buildID=20110705195857
        """

        fakeResponse = exp.DummyObjectWithExpectations()
        fakeResponse.code = 200
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('close', (), {})

        fakeUrllib2 = exp.DummyObjectWithExpectations()
        fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)
        expected = {'buildID': '20110705195857'}
        actual = ftpscraper.parseInfoFile('http://www.example.com/PRODUCT1', nightly=False, urllib=fakeUrllib2)
        assert actual == expected, "expected %s, got %s" % (expected, actual)

