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
# def Log( s ): print s


##
HTTP_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36"
URL_SEARCH = "http://subscenter.cinemast.com/he/subtitle/search/"
URL_SUBS = "http://subscenter.cinemast.com/he/cinemast/data/"
URL_DOWNLOAD = "http://subscenter.cinemast.com/subtitle/download/he/"
MAX_TITLES = 4 # maximum top search result titles to review
MAX_RESULTS = 4 # maximum subtitles to download
FORMATS = [ "hdtv", "480p", "720p", "1080p" ]

def search( name, fname, fmt, season = None, episode = None ):
    Log( "Search for: " + name )
    url = URL_SEARCH + "?q=" + name.lower().replace( " ", "+" )
    html = HTML.ElementFromURL( url, headers = { "User-Agent": HTTP_USER_AGENT } ) 

    titles = []
    for r in html.xpath( "//div[@id='processes']//a" ):
        if not r.text.strip(): continue
        name = r.attrib[ "href" ].split( "/" )[ -2 ]
        Log( "Search found: " + name )
        titles.append( name )
        if len( titles ) > MAX_TITLES: break # 

    subs = []
    for t in titles:
        subs += get( t, fmt, season, episode )
    Log( "Received %s (Total) subs for %s" % ( len( subs ), name ) )
    subs = sorted( subs, cmpstr( fname ) )
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
        result = results[ p ].get( fmt, {} )
        for sub in result:
            subs.append( result[ sub ] )
    Log( "Get found %s subtitles for %s" % ( len( subs ), name ) )
    return subs


def download( sub ):
    v = sub[ "subtitle_version" ]
    k = sub[ "key" ]
    url = URL_DOWNLOAD + "%s/?v=%s&key=%s" % ( sub[ "id" ], v, k )
    Log( "Downloading subtitle: " + url )
    try:
        return HTTP.Request( url, headers = { "User-Agent": HTTP_USER_AGENT } ).content
    except Exception as e:
        Log( "ERROR downloading: " + url )
        Log( e )

def compact( s ):
    return s.lower().strip().replace( ".", "" ).replace( "-", "" ).replace( "_", "" )

def cmpstr( name ):
    name = compact( name )
    def compare( s, t ):
        if compact( s[ "subtitle_version" ] ) == name: return -1
        elif compact( t[ "subtitle_version" ] ) == name: return 1
        else: return cmp( s[ "downloaded" ], t[ "downloaded" ] )
    return compare


def update( part, name, season = None, episode = None ):
    fname = part.file.lower()
    formats = filter( lambda f: f in fname, FORMATS )
    if not formats: 
        return Log( "Failed to find format for: " + fname )

    locale = Locale.Language.Unknown
    subs = search( name, fname, formats[ 0 ], season, episode )
    for sub in subs:
        v = sub[ "subtitle_version" ]
        sub = download( sub )
        if sub:
            part.subtitles[ locale ][ v ] = Proxy.Media( sub, ext = "srt" )


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
