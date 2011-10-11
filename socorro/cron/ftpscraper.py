#! /usr/bin/env python
"""
ftpscraper.py pulls build information from ftp.mozilla.org for nightly and release builds.
"""
import sys
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

def scrape(links, parser):
    results = {}
    for l in links:
        for info in parser(l, url):
            osname = info.keys()[0]
            if osname in results:
                kvpairs = info[osname].keys()[0]
                results[osname][kvpairs] = info[osname][kvpairs]
            else:
                results[osname] = info[osname]
    return results

products = ['firefox', 'mobile', 'thunderbird', 'seamonkey', 'camino']

results = {}
for product in products:
    for dir in ('nightly', 'candidates'):
        prod_url = '%s/%s/' % (baseurl, product)
        if not getLinks(prod_url, startswith=dir):
            print >> sys.stderr, 'Dir %s not found for product %s' % (dir, product)
            continue

        url = '%s/%s/%s/' % (baseurl, product, dir)
    
        try: 
            releases = getLinks(url, endswith='-candidates/')
            release_results = scrape(releases, getRelease)
            
            nightlies = getLinks(url, startswith='latest')
            nightly_results = scrape(nightlies, getNightly)

            result = {
                product: {
                    'releases': release_results,
                    'nightlies': nightly_results,
                }
            }
            results = dict(results.items() + result.items())
        except urllib2.URLError, e:
            if not hasattr(e, "code"):
                raise
            resp = e
            print >> sys.stderr, 'HTTP code %s for URL %s' % (resp.code, url)

print json.dumps(results)
