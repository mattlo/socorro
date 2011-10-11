#! /usr/bin/env python
"""
ftpscraper.py pulls build information from ftp.mozilla.org for nightly and release builds.
"""
import urllib2
import json
from BeautifulSoup import BeautifulSoup, SoupStrainer

baseurl = 'http://ftp.mozilla.org/pub/mozilla.org'

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

def parseInfoFile(url, nightly=False):
    infotxt = urllib2.urlopen(url)
    if nightly:
        kv = infotxt.read().split('\n')
        k = kv[0]
        v = kv[1]
    else:
        k, v = infotxt.read().strip().split('=')
    return {k:v}

def getRelease(dirname, url):
    candidate_url = '%s/%s' % (url, dirname)
    builds = getLinks(candidate_url, startswith='build')

    latest_build = builds.pop()
    build_url = '%s/%s' % (candidate_url, latest_build)

    info_files = getLinks(build_url, endswith='_info.txt')

    build_data = []
    for f in info_files:
        info_url = '%s/%s' % (build_url, f)
        kvpairs = parseInfoFile(info_url)

        osname = f.split('_info.txt')[0]

        version = dirname.split('-candidates')[0]
        build_number = latest_build.strip('/')

        build_data.append({
            osname: {
                version: {
                    build_number: kvpairs
                }
            }
        })
  
    return build_data

def getNightly(dirname, url):
    nightly_url = '%s/%s' % (url, dirname)
    info_files = getLinks(nightly_url, endswith='.txt')

    build_data = []
    for f in info_files:
        if 'en-US' in f:
            (pv, osname) = f.strip('.txt').split('.en-US.')
            (product, version) = pv.split('-')
            branch = dirname.strip('/')

            info_url = '%s/%s' % (nightly_url, f)
            kvpairs = parseInfoFile(info_url, nightly=True)

            build_data.append({
                osname: {
                    branch: {
                        version: kvpairs
                    }
                }
            })

    return build_data

products = ['firefox', 'mobile', 'thunderbird', 'seamonkey', 'camino']

for p in products:
    for d in ('nightly', 'candidates'):
        url = '%s/%s/%s/' % (baseurl, p, d)
        print url
    
        try: 
            releases = getLinks(url, endswith='-candidates/')
            release_info = {}
    
            for r in releases:
                for info in getRelease(r, url):
                    osname = info.keys()[0]
                    if osname in release_info:
                        version = info[osname].keys()[0]
                        release_info[osname][version] = info[osname][version]
                    else:
                        release_info[osname] = info[osname]
            print json.dumps(release_info)
            
            nightlies = getLinks(url, startswith='latest')
            nightly_info = {}
            for n in nightlies:
                for info in getNightly(n, url):
                    osname = info.keys()[0]
                    if osname in nightly_info:
                        branch = info[osname].keys()[0]
                        nightly_info[osname][branch] = info[osname][branch]
                    else:
                        nightly_info[osname] = info[osname]
            print json.dumps(nightly_info)
        except urllib2.HTTPError:
            print '404 for %s, continuing...' % url

