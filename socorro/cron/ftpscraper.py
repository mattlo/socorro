#! /usr/bin/env python
"""
ftpscraper.py pulls build information from ftp.mozilla.org for nightly and release builds.
"""
import sys
import urllib2
from BeautifulSoup import BeautifulSoup, SoupStrainer

baseurl = 'http://ftp.mozilla.org/pub/mozilla.org'

def getLinks(url, startswith=None, endswith=None):
    page = urllib2.urlopen(url)
    links = SoupStrainer('a')
    soup = BeautifulSoup(page, parseOnlyThese=links)
    page.close()
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
    contents = infotxt.read().split()
    infotxt.close()
    results = {}
    if nightly:
        results = {'buildID': contents[0], 'rev': contents[1]}
        if len(contents) > 2:
            results['altrev'] = contents[2]
    else:
        for entry in contents:
            (k,v) = entry.split('=')
            results[k] = v

    return results

def getRelease(dirname, url):
    candidate_url = '%s/%s' % (url, dirname)
    builds = getLinks(candidate_url, startswith='build')

    latest_build = builds.pop()
    build_url = '%s/%s' % (candidate_url, latest_build)

    info_files = getLinks(build_url, endswith='_info.txt')

    for f in info_files:
        info_url = '%s/%s' % (build_url, f)
        kvpairs = parseInfoFile(info_url)

        osname = f.split('_info.txt')[0]

        version = dirname.split('-candidates')[0]
        build_number = latest_build.strip('/')

        yield (osname, version, build_number, kvpairs)
  
def getNightly(dirname, url):
    nightly_url = '%s/%s' % (url, dirname)
    info_files = getLinks(nightly_url, endswith='.txt')

    for f in info_files:
        if 'en-US' in f:
            (pv, osname) = f.strip('.txt').split('.en-US.')
            (product, version) = pv.split('-')
            branch = dirname.strip('/')

            info_url = '%s/%s' % (nightly_url, f)
            kvpairs = parseInfoFile(info_url, nightly=True)

            yield (osname, branch, version, kvpairs)

products = ['firefox', 'mobile', 'thunderbird', 'seamonkey', 'camino']

for product in products:
    for dir in ('nightly', 'candidates'):
        prod_url = '%s/%s/' % (baseurl, product)
        if not getLinks(prod_url, startswith=dir):
            print >> sys.stderr, 'Dir %s not found for product %s' % (dir, product)
            continue

        url = '%s/%s/%s/' % (baseurl, product, dir)
        sql = """INSERT INTO releases_raw (product_name, version, platform, build_id, build_type, beta_number)
                 VALUES(%s, %s, %s, %s, %s, %s)"""
    
        try: 
            releases = getLinks(url, endswith='-candidates/')
            for release in releases:
                for info in getRelease(release, url):
                    (osname, version, build_number, kvpairs) = info
                    build_type = 'Release'
                    beta_number = None
                    if 'b' in version:
                        build_type = 'Beta'
                        beta_number = version.split('b')[1]
                    build_id = kvpairs['buildID']
                    print sql % (product, version, osname, build_id, build_type, None)
            
            nightlies = getLinks(url, startswith='latest')
            for nightly in nightlies:
                for info in getNightly(nightly, url):
                    (osname, branch, version, kvpairs) = info
                    build_id = kvpairs['buildID']
                    build_type = 'Nightly'
                    if version.endswith('a2'):
                        build_type = 'Aurora'
                    print sql % (product, version, osname, build_id, build_type, None)

        except urllib2.URLError, e:
            if not hasattr(e, "code"):
                raise
            resp = e
            print >> sys.stderr, 'HTTP code %s for URL %s' % (resp.code, url)
