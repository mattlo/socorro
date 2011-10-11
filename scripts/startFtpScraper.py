#! /usr/bin/env python
"""
fetchBuilds.py is used to get the primary nightly builds from ftp.mozilla.org, record
the build information and provide that information through the Crash Reporter website.

This script is expected to be run once per day.
"""

import logging
import logging.handlers

try:
  import config.ftpscraperconfig as configModule
except ImportError:
  import ftpscraperconfig as configModule

import socorro.cron.ftpscraper as ftpscraper
import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util as sutil

config = configurationManager.newConfiguration(configurationModule = configModule, applicationName='startFtpScraper.py')
assert "databaseHost" in config, "databaseHost is missing from the configuration"
assert "databaseName" in config, "databaseName is missing from the configuration"
assert "databaseUserName" in config, "databaseUserName is missing from the configuration"
assert "databasePassword" in config, "databasePassword is missing from the configuration"
assert "base_url" in config, "base_url is missing from the configuration"
assert "products" in config, "products is missing from the configuration"

logger = logging.getLogger("ftpscraper")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

config.logger = logger

try:
  ftpscraper.recordBuilds(config)
finally:
  logger.info("Done.")
