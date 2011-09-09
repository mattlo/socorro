try:
  import json
except ImportError:
  import simplejson as json
import logging
import web

import socorro.lib.util as util
import socorro.database.database as db
import socorro.storage.crashstorage as cs

logger = logging.getLogger("webapi")

#-----------------------------------------------------------------------------------------------------------------
def typeConversion (listOfTypeConverters, listOfValuesToConvert):
  return (t(v) for t, v in zip(listOfTypeConverters, listOfValuesToConvert))

#=================================================================================================================
class Unimplemented(Exception):
  pass

class Timeout(web.webapi.HTTPError):
    """'408 Request Timeout' Error"""
    message = "item currently unavailable"
    def __init__ (self):
        status = "408 Request Timeout"
        headers = {'Content-Type': 'text/html'}
        web.webapi.HTTPError.__init__(self, status, headers, self.message)
        

#=================================================================================================================
class JsonServiceBase (object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config):
    try:
      self.context = config
      self.database = db.Database(config)
      self.crashStoragePool = cs.CrashStoragePool(config,
                                                  storageClass=config.hbaseStorageClass)
    except (AttributeError, KeyError):
      util.reportExceptionAndContinue(logger)

  #-----------------------------------------------------------------------------------------------------------------
  def GET(self, *args):
    try:
      result = self.get(*args)
      if type(result) is tuple:
        web.header('Content-Type', result[1])
        return result[0]
      return json.dumps(result)
    except web.webapi.HTTPError:
      raise
    except Exception, x:
      stringLogger = util.StringLogger()
      util.reportExceptionAndContinue(stringLogger)
      try:
        util.reportExceptionAndContinue(self.context.logger)
      except (AttributeError, KeyError):
        pass
      raise Exception(stringLogger.getMessages())

  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    raise Unimplemented("the GET function has not been implemented for %s" % args)

  #-----------------------------------------------------------------------------------------------------------------
  def POST(self, *args):
    try:
      result = self.post(*args)
      if type(result) is tuple:
        web.header('Content-Type', result[1])
        return result[0]
      return json.dumps(result)
    except web.HTTPError:
      raise
    except Exception:
      util.reportExceptionAndContinue(self.context.logger)
      raise

  #-----------------------------------------------------------------------------------------------------------------
  def post(self, *args):
    raise Unimplemented("the POST function has not been implemented.")

