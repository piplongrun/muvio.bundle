import unicodedata

AUTH_URL = 'http://www.vevo.com/auth'
ARTIST_SEARCH_URL = 'http://apiv2.vevo.com/search?artistsLimit=1&page=1&size=50&skippedVideos=0&q=%s'
ARTIST_VIDEOS_URL = 'http://apiv2.vevo.com/artist/%s/videos?page=1&size=50&sort=MostRecent'
VIDEO_URL = 'muvio://www.vevo.com/watch/%s'

TYPE_ORDER = ['music_video', 'live_music', 'lyric_video']
TYPE_MAP = {
  'music_video': MusicVideoObject,
  'live_music': LiveMusicVideoObject,
  'lyric_video': LyricMusicVideoObject
}

####################################################################################################
def Start():

  HTTP.CacheTime = CACHE_1WEEK
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/602.1.50 (KHTML, like Gecko) Version/10.0 Safari/602.1.50'

  if 'access_token' not in Dict or Dict['access_token'] is None:
    UpdateToken()

####################################################################################################
def ArtistName(artist):

  try:
    artist = unicodedata.normalize('NFKD', artist.decode('utf-8'))
  except UnicodeError:
    artist = unicodedata.normalize('NFKD', artist)

  # Strip diacritics
  stripped = u''

  for i in range(len(artist)):
    point = artist[i]

    if not unicodedata.combining(point):
      stripped += point

  return stripped

####################################################################################################
def UpdateToken():

  try:
    json = JSON.ObjectFromURL(AUTH_URL, method='POST')

    Log(' *** Successfully got an access token.')
    Dict['access_token'] = json['access_token']
    Dict['expires'] = json['expires']

  except:
    Log(' *** Failed to get an access token.')
    Dict['access_token'] = None
    Dict['expires'] = 0

  Dict.Save()

####################################################################################################
class Muvio(Agent.Artist):

  name = 'MUVIO'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.lastfm']

  def search(self, results, media, lang):

    results.Append(MetadataSearchResult(
      id = ArtistName(media.primary_metadata.title),
      score = 100
    ))

  def update(self, metadata, media, lang):

    if Dict['expires'] < int(Datetime.TimestampFromDatetime(Datetime.Now()) - 3600):
      UpdateToken()

    # Do not keep hammering the service if we did not get a valid access token
    if not Dict['access_token']:
      return None

    # Lookup artist
    try:
      json = JSON.ObjectFromURL(ARTIST_SEARCH_URL % (String.Quote(metadata.id, usePlus=True)), headers={'Authorization': 'Bearer %s' % (Dict['access_token'])})
    except:
      Log(' *** Artist lookup failed.')
      return None

    score = 99
    best_match = None

    for artist in json['artists']:

      artist_score = abs(String.LevenshteinDistance(metadata.id, artist['name']))

      if artist_score < score:

        score = artist_score
        best_match = artist['urlSafeName']

    try:
      json = JSON.ObjectFromURL(ARTIST_VIDEOS_URL % (best_match), headers={'Authorization': 'Bearer %s' % (Dict['access_token'])})
    except:
      Log(' *** Video lookup failed.')
      return None

    extras = []

    for video in json['videos']:

      if 'Shows and Interviews' in video['categories'] or 'Audio' in video['categories']:
        continue

      if 'Lyrics' in video['categories']:
        extra_type = 'lyric_video'
      elif 'Live Performance' in video['categories']:
        extra_type = 'live_music'
      else:
        extra_type = 'music_video'

      extras.append({
        'type': extra_type,
        'extra': TYPE_MAP[extra_type](
          url = VIDEO_URL % (video['isrc']),
          title = video['title'],
          thumb = video['thumbnailUrl']
        )
      })

    extras.sort(key=lambda e: TYPE_ORDER.index(e['type']))

    for extra in extras:
      metadata.extras.add(extra['extra'])

####################################################################################################
class Muvio(Agent.Album):

  name = 'MUVIO'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.lastfm']

  def search(self, results, media, lang):

    artist = ArtistName(String.Unquote(media.primary_metadata.id.split('/')[0])) # Album object doesn't have artist information(?). Grab it from the metadata id instead.

    results.Append(MetadataSearchResult(
      id = artist,
      score = 100
    ))

  def update(self, metadata, media, lang):

    if Dict['expires'] < int(Datetime.TimestampFromDatetime(Datetime.Now()) - 3600):
      UpdateToken()

    # Do not keep hammering the service if we did not get a valid access token
    if not Dict['access_token']:
      return None

    # Lookup artist
    try:
      json = JSON.ObjectFromURL(ARTIST_SEARCH_URL % (String.Quote(metadata.id, usePlus=True)), headers={'Authorization': 'Bearer %s' % (Dict['access_token'])})
    except:
      Log(' *** Artist lookup failed.')
      return None

    score = 99
    best_match = None

    for artist in json['artists']:

      artist_score = abs(String.LevenshteinDistance(metadata.id, artist['name']))

      if artist_score < score:

        score = artist_score
        best_match = artist['urlSafeName']

    try:
      json = JSON.ObjectFromURL(ARTIST_VIDEOS_URL % (best_match), headers={'Authorization': 'Bearer %s' % (Dict['access_token'])})
    except:
      Log(' *** Video lookup failed.')
      return None

    for index, track in enumerate(media.children):

      for video in json['videos']:

        score = 100 - (10 * abs(String.LevenshteinDistance(track.title.lower(), video['title'].lower())))
        #Log("%s vs %s --> %d" % (track.title.lower(), video['title'].lower(), score))

        if score > 80:

          music_video = MusicVideoObject(
            url = VIDEO_URL % (video['isrc']),
            title = video['title'],
            thumb = video['thumbnailUrl']
          )

          # Add the video, and we're done (only one video per track allowed)
          #Log('Adding music video %s to track %s - %s' % (music_video.title, index, track.title))
          metadata.tracks[track.guid].extras.add(music_video)
          break
