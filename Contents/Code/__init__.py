# import urllib2
# from lxml import etree
# import json
# class HTML:
#     @staticmethod
#     def ElementFromURL( url, *args, **kwargs ):
#         return etree.HTML( urllib2.urlopen( url ).read() )
# class HTTP:
#     @staticmethod
#     def Request( url, *args, **kwargs ):
#         class HTTPRequest:
#             content = urllib2.urlopen( url ).read()
#         return HTTPRequest()
# class JSON:
#     @staticmethod
#     def ObjectFromURL( url, *args, **kwargs ):
#         return json.loads( urllib2.urlopen( url ).read() )
# class Part:
#     subtitles = { "he": {} }
#     def __init__( self, f ): self.file = f
# class Language:
#     Hebrew = "he"
#     NoLanguage = ""
# class Locale:
#     Language = Language
# class Media:
#     def __init__( self, *args, **kwargs ): pass
# class Proxy:
#     Media = Media
# class TV_Shows: pass
# class Movies: pass
# class Agent:
#     TV_Shows = TV_Shows
#     Movies = Movies
# def Log( s ): print s


##
import os
import zipfile
import StringIO
HTTP_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36"
URL_SEARCH = "http://subscenter.cinemast.com/he/subtitle/search/"
URL_SUBS = "http://subscenter.cinemast.com/he/cinemast/data/"
URL_DOWNLOAD = "http://subscenter.cinemast.com/subtitle/download/he/"
MAX_TITLES = 4 # maximum top search result titles to review
MAX_RESULTS = 2 # maximum subtitles to download
LEVENSHTEIN_MAX = 0.5 
FORMATS = [ "hdtv", "1080p", "720p", "480p" ]

def search( name, fname, season = None, episode = None ):
    Log( "Search for: " + name )

    fname = fname.lower()
    formats = filter( lambda f: f in fname, FORMATS )
    fmt = formats[ 0 ] if formats else None
    Log( "Using format %s for %s" % ( fmt, name ) )

    url = URL_SEARCH + "?q=" + name.lower().replace( " ", "+" )
    html = HTML.ElementFromURL( url, headers = { "User-Agent": HTTP_USER_AGENT } ) 

    cname = compact( name )
    titles = []
    for r in html.xpath( "//div[@id='processes']//a" ):
        if not r.text.strip(): continue
        title = r.attrib[ "href" ].split( "/" )[ -2 ]
        Log( "Search found: " + title )
        if levenshtein( cname, compact( title ) ) < LEVENSHTEIN_MAX:
            titles.append( title )
        else: Log( "Levenshtein Failed for title: %s" % title )
        if len( titles ) > MAX_TITLES: break # 

    subs = []
    for t in titles:
        subs += get( t, fmt, season, episode )
    Log( "Received %s (Total) subs for %s" % ( len( subs ), name ) )

    # first, try to filter out the non-exact matches (assuming atleast one is found)
    cfname = compact( fname )
    exact = filter( lambda s: compact( s[ "subtitle_version"] ) == cfname, subs )
    if exact: 
        Log( "Exact match found: " + fname )
        subs = exact

    # filter out results that are too far away from the search string
    l = lambda s: levenshtein( cfname, compact( s[ "subtitle_version" ] ) )
    subs = filter( lambda s: l( s ) < LEVENSHTEIN_MAX, subs )

    Log( "Received %s (Filtered) subs for %s" % ( len( subs ), name ) )

    # sort by download count
    subs = sorted( subs, None, lambda s: s[ "downloaded" ], True )

    # return the maximum allowed results
    return subs[ :MAX_RESULTS ]


def get( name, fmt, season = None, episode = None ):
    category = "movie"
    url = name + "/"
    if season and episode: 
        category = "series"
        url += str( season ) + "/" + str( episode ) + "/"
    url = URL_SUBS + category + "/sb/" + url + "?_=1398212416"
    Log( "Getting " + name + ": " + url )
    try:
        results = JSON.ObjectFromURL( url, headers = { "User-Agent": HTTP_USER_AGENT } )
    except Exception as e:
        Log( "ERROR getting: " + url )
        Log( e )
        results = {}
    results = results.get( "he", {} )

    subs = []
    for p in results:
        for f in results[ p ]:
            if fmt in [ None, f ]:
                result = results[ p ][ f ]
                for sub in result:
                    subs.append( result[ sub ] )
    Log( "Get found %s subtitles for %s" % ( len( subs ), name ) )
    return subs


def download( sub ):
    v = sub[ "subtitle_version" ]
    k = sub[ "key" ]
    url = URL_DOWNLOAD + "%s/?v=%s&key=%s" % ( sub[ "id" ], v, k )
    Log( "Downloading subtitle: %s" % url )

    sub = HTTP.Request( url, headers = { "User-Agent": HTTP_USER_AGENT } )
    sub = StringIO.StringIO( sub.content )
    zsub = zipfile.ZipFile( sub )

    fnames = zsub.namelist()
    if not fnames: return None

    sub = zsub.read( fnames[ 0 ] )
    Log( "Downloaded and unzipped: %s" % url )
    return sub


def compact( s ):
    return s.lower().strip().replace( ".", "" ).replace( "-", "" ).replace( "_", "" ).replace( " ", "" ).replace( ":", "" )

# compute the levenshtein distance between the two strings
# recursive implementation with memoization for efficiency
def levenshtein( s, t ):
    if len( s ) == 0: return 1 # 100% difference
    m = {}
    def do( si, ti ):
        if si == 0: return ti
        if ti == 0: return si
        if ( si, ti ) in m: return m[ si, ti ] # memoized

        cost = 0 if s[ si - 1 ] == t[ ti - 1 ] else 1
        m[ si, ti ] = min( 
            do( si - 1, ti ) + 1, # deletion
            do( si, ti - 1 ) + 1, # insertion
            do( si - 1, ti - 1 ) + cost # substitution
        )
        return m[ si, ti ]
    result = do( len( s ), len( t ) ) / float( len( s ) ) # can't be zero division
    Log( "Levenshtein %s ( %s, %s )" % ( result, s, t ) )
    return result

def update( part, name, season = None, episode = None ):
    locale = Locale.Language.Hebrew
    fname = os.path.split( part.file )[ -1 ]
    fname = ".".join( fname.split( "." )[ :-1 ] )
    subs = search( name, fname, season, episode )
    for sub in subs:
        v = sub[ "subtitle_version" ]
        sub = download( sub )
        if sub:
            part.subtitles[ locale ][ v ] = Proxy.Media( sub, ext = "srt" )
            Log( "Subtitle saved for: " + v )


class SubcenterTV( Agent.TV_Shows ):
    name = "Subcenter.org"
    languages = [ Locale.Language.NoLanguage ]
    primary_provider = False
    contributes_to = [ "com.plexapp.agents.thetvdb" ]

    def search( self, results, media, lang ):
        results.Append( MetadataSearchResult(
            id    = "null",
            score = 100
        ))

    def update( self, metadata, media, lang ):
        for s in media.seasons:
            if int( s ) > 1900: continue
            for e in media.seasons[ s ].episodes:
                for i in media.seasons[ s ].episodes[ e ].items:
                    for part in i.parts:
                        update( part, media.title, s, e )


class SubcenterMovies( Agent.Movies ):
    name = "Subcenter.org"
    languages = [ Locale.Language.NoLanguage ]
    primary_provider = False
    contributes_to = [ "com.plexapp.agents.imdb" ]
  
    def search(self, results, media, lang):
        results.Append( MetadataSearchResult(
            id    = "null",
            score = 100
        ))
    
    def update( self, metadata, media, lang ):
        for i in media.items:
            for part in i.parts:
                update( part, media.title )



# test
# update( Part( "AboutTime.2013.720p.BrRip.x264.YIFY" ), "About Time" )
