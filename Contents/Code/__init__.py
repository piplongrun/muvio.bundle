import certifi
import requests
import unicodedata

VERSION = '3.1'
SERACH_URL = 'https://muvio.api.tadata.me/v2/?artist=%s'

TYPE_ORDER = ['music_video', 'live_music', 'lyric_video']
TYPE_MAP = {
  "music_video": MusicVideoObject,
  "live_music": LiveMusicVideoObject,
  "lyric_video": LyricMusicVideoObject
}

FILTER_ARTIST = ('various artists')
RE_LIVE_VIDEO = Regex('live (on|at|in|from|for)|\(live|unstaged\)|.*(tour|festival).*', Regex.IGNORECASE)

HTTP_HEADERS = {
  "User-Agent": "MUVIO/%s (%s %s; Plex Media Server %s)" % (VERSION, Platform.OS, Platform.OSVersion, Platform.ServerVersion)
}

####################################################################################################
def Start():

  pass

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
class Muvio(Agent.Artist):

  name = 'MUVIO'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.lastfm', 'com.plexapp.agents.plexmusic']

  def search(self, results, media, lang, manual=False, tree=None):

    artist = ArtistName(tree.title)

    if artist.lower() in FILTER_ARTIST:
      return None

    results.add(SearchResult(
      id = artist,
      score = 100
    ))

  def update(self, metadata, media, lang):

    r = requests.get(SERACH_URL % (String.Quote(metadata.id)), headers=HTTP_HEADERS, verify=certifi.where())

    if 'error' in r.json():
      Log("*** An error occurred: %s ***" % (r.json()['error']))
      return None

    if not 'videos' in r.json():
      return None

    extras = []

    for video in r.json()['videos']:

      if 'lyric video' in video['title'].lower() or 'lyric-video' in video['url'].lower():
        extra_type = 'lyric_video'
      elif RE_LIVE_VIDEO.search(video['title']):
        extra_type = 'live_music'
      else:
        extra_type = 'music_video'

      extras.append({
        'type': extra_type,
        'extra': TYPE_MAP[extra_type](
          url = 'muvio://%s' % (video['url'].split('//')[-1]),
          title = video['title'],
          thumb = video['thumb_url']
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
  contributes_to = ['com.plexapp.agents.lastfm', 'com.plexapp.agents.plexmusic']

  def search(self, results, media, lang, manual=False, tree=None):

    artist = ArtistName(tree.title)

    if artist.lower() in FILTER_ARTIST:
      return None

    results.add(SearchResult(
      id = artist,
      score = 100
    ))

  def update(self, metadata, media, lang):

    r = requests.get(SERACH_URL % (String.Quote(metadata.id)), headers=HTTP_HEADERS, verify=certifi.where())

    if 'error' in r.json():
      Log("*** An error occurred: %s ***" % (r.json()['error']))
      return None

    if not 'videos' in r.json():
      return None

    for index, track in enumerate(media.children):

      for video in r.json()['videos']:

        score = 100 - (10 * abs(String.LevenshteinDistance(track.title.lower(), video['title'].lower())))
        #Log("%s vs %s --> %d" % (track.title.lower(), video['title'].lower(), score))

        if score > 80:

          music_video = MusicVideoObject(
            url = 'muvio://%s' % (video['url'].split('//')[-1]),
            title = video['title'],
            thumb = video['thumb_url']
          )

          # Add the video, and we're done (only one video per track allowed)
          #Log('Adding music video %s to track %s - %s' % (music_video.title, index, track.title))
          metadata.tracks[track.guid].extras.add(music_video)
          break
