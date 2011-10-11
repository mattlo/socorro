#! /usr/bin/env python
"""
ftpscraper.py pulls build information from ftp.mozilla.org for nightly and release builds.
"""
import urllib2
import json
from BeautifulSoup import BeautifulSoup, SoupStrainer

baseurl = 'http://ftp.mozilla.org/pub/mozilla.org/firefox/nightly/'

def getLinks(url, startswith=None, endswith=None):
    page = urllib2.urlopen(url)
    links = SoupStrainer('a')
    soup = BeautifulSoup(page, parseOnlyThese=links)
    results = []
    for tag in soup:
        link = tag.contents[0]
        if startswith:
            if link.startswith(startswith):
                results.append(link)
        elif endswith:
            if link.endswith(endswith):
                results.append(link)
    return results

def parseInfoFile(url):
    infotxt = urllib2.urlopen(url)
    k, v = infotxt.read().strip().split('=')
    return {k:v}

def getRelease(dirname):
    candidate_url = '%s/%s' % (baseurl, dirname)
    builds = getLinks(candidate_url, startswith='build')
    latest_build = builds.pop()
    build_url = '%s/%s' % (candidate_url, latest_build)
    info_files = getLinks(build_url, endswith='_info.txt')
    build_data = []
    for f in info_files:
        info_url = '%s/%s' % (build_url, f)
        kvpairs = parseInfoFile(info_url)

        os = f.split('_info.txt')[0]

        version = dirname.split('-candidates')[0]
        build_number = latest_build.strip('/')

        build_data.append({
            os: {
                version: {
                    build_number: kvpairs
                }
            }
        })
  
    return build_data

def getNightly(dirname):
    pass

releases = getLinks(baseurl, endswith='-candidates/')
nightlies = getLinks(baseurl, startswith='latest')

release_info = {}
for r in releases:
    for info in getRelease(r):
        os = info.keys()[0]
        if os in release_info:
            version = info[os].keys()[0]
            release_info[os][version] = info[os][version]
        else:
            release_info[os] = info[os]

print json.dumps(release_info)

for n in nightlies:
    pass

