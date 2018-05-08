import certifi
import requests
import unicodedata

VERSION = '3.3'
SERACH_URL = 'https://muvio.api.tadata.me/v2/?artist={}'
RE_FILTER = Regex('Best Of|Hits Collection|Sound ?track|Unknown Artist|Various Artists', Regex.IGNORECASE)
RE_SPLIT_TITLE = Regex(' \(?feat(?:\.|uring) ')

HTTP_HEADERS = {
  "User-Agent": "MUVIO/{} ({} {}; Plex Media Server {})".format(VERSION, Platform.OS, Platform.OSVersion, Platform.ServerVersion)
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

    if RE_FILTER.search(artist):
      return None

    results.add(SearchResult(
      id = artist,
      score = 100
    ))

  def update(self, metadata, media, lang):

    r = requests.get(SERACH_URL.format(String.Quote(metadata.id)), headers=HTTP_HEADERS, verify=certifi.where())

    if 'error' in r.json():
      Log("*** An error occurred: {} ***".format(r.json()['error']))
      return None

    if not 'videos' in r.json():
      return None

    for video in r.json()['videos']:

      metadata.extras.add(
        MusicVideoObject(
          url = 'muvio://{}'.format(video['url'].split('//')[-1]),
          title = video['title'],
          thumb = video['thumb_url']
        )
      )

####################################################################################################
class Muvio(Agent.Album):

  name = 'MUVIO'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.lastfm', 'com.plexapp.agents.plexmusic']

  def search(self, results, media, lang, manual=False, tree=None):

    artist = ArtistName(tree.title)

    if RE_FILTER.search(artist):
      return None

    results.add(SearchResult(
      id = artist,
      score = 100
    ))

  def update(self, metadata, media, lang):

    r = requests.get(SERACH_URL.format(String.Quote(metadata.id)), headers=HTTP_HEADERS, verify=certifi.where())

    if 'error' in r.json():
      Log("*** An error occurred: {} ***".format(r.json()['error']))
      return None

    if not 'videos' in r.json():
      return None

    for index, track in enumerate(media.children):

      for video in r.json()['videos']:

        track_title = RE_SPLIT_TITLE.split(track.title.lower())[0]
        video_title = RE_SPLIT_TITLE.split(video['title'].lower())[0]
        score = 100 - (10 * abs(String.LevenshteinDistance(track_title, video_title)))
        #Log('"{}" vs "{}" --> {}'.format(track_title, video_title, score))

        if score > 80:

          # Add the video, and we're done (only one video per track allowed)
          #Log('Adding music video "{}" to track {} - "{}"'.format(video['title'], index, track.title))
          metadata.tracks[track.guid].extras.add(
            MusicVideoObject(
              url = 'muvio://{}'.format(video['url'].split('//')[-1]),
              title = video['title'],
              thumb = video['thumb_url']
            )
          )

          break
