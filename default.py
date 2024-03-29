#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import requests, requests.utils, pickle
import sys
import time
if sys.version_info[0] == 3:
    import html
    from xbmcvfs import translatePath
    from urllib.parse import quote_plus
    from urllib.parse import urlencode
    from urllib.parse import parse_qs
else:
    import HTMLParser
    html = HTMLParser.HTMLParser()
    from xbmc import translatePath
    from urllib import quote_plus
    from urllib import urlencode
    from urlparse import parse_qs
from contextlib import closing

import xbmcaddon
import xbmcgui
import xbmcplugin

import json
from resources.lib.moviedb import Moviedb
from resources.lib.movie import Movie
from resources.lib.modules.utils import py2_encode, py2_decode

dbProjectCompleted='ProjectCompleted'
dbProjectActual='ProjectActual'

addon = xbmcaddon.Addon(id='plugin.video.animeaddicts')
thisAddonDir = py2_decode(translatePath(addon.getAddonInfo('path')))
sys.path.append(os.path.join(thisAddonDir, 'resources', 'lib'))

userDataDir = py2_decode(translatePath(addon.getAddonInfo('profile')))

appName = 'AnimeAddicts'
logined = False

baseUrl = 'http://animeaddicts.hu/'

felhasznalo = addon.getSetting('felhasznalonev')
jelszo = addon.getSetting('jelszo')
tmpDir = addon.getSetting('tmpdir')
hdVideo = addon.getSetting('hdVideo')
forceDownload = addon.getSetting('forceDownload')
if (felhasznalo == "" or jelszo == "" or tmpDir == ""):
    dialog = xbmcgui.Dialog()
    dialog.ok("Hiba!", "Nem végezted el a beállításokat!")
    addon.openSettings()
    sys.exit()

def newSession():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.6 Safari/537.36',
    })

    if os.path.isfile(userDataDir + '/animeaddicts.cookies'):
        cookieFile = open(userDataDir + '/animeaddicts.cookies', 'rb')
        cookies = requests.utils.cookiejar_from_dict(pickle.load(cookieFile))
        s.cookies = cookies
        cookieFile.close()

    return s

session = newSession()

def doLogin():
    global session
    #postdata = {'login_name':addon.getSetting('felhasznalonev'),
    #            'login_submit':'BELÉPÉS',
    #            'login_password':addon.getSetting('jelszo')
    #            }
    postdata = {'login_name':addon.getSetting('felhasznalonev'),
                'login_password':addon.getSetting('jelszo')
                }

    content = session.post(baseUrl + 'project.php?ongoing').text

    sikeres = re.compile("vagy jelentkezz be", re.MULTILINE|re.DOTALL).findall(py2_encode(content))
    if (len(sikeres) > 0):
        content = session.post(baseUrl + 'log.php?login', data=postdata).text
        content = session.post(baseUrl + 'project.php?ongoing').text

        sikeres = re.compile("vagy jelentkezz be", re.MULTILINE|re.DOTALL).findall(py2_encode(content))
        if (len(sikeres) > 0):
            logined = False
            dialog = xbmcgui.Dialog()
            dialog.ok("Hiba!", "Helytelen felhasználónév, vagy jelszó!\nEsetleg megjelent az I'm not a robot captcha.\nVárj egy ideig, esetleg próbáld meg böngészőből!")
            sys.exit()
        else:
            logined = True
            cookieFile = open(userDataDir + '/animeaddicts.cookies', 'wb')
            pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), cookieFile)
            cookieFile.close();

    return

def load(url, post = None, referer = None):
    global session
    doLogin()

    if referer:
        session.headers.update({
        'Host': 'animeaddicts.hu',
        'Referer': referer
    })

    r = ""
    try:
        if post:
            r = session.post(url, data=post, timeout=10).text
        else:
            if referer:
                contentFile = open(tmpDir + 'videocontent', 'wb')
                with closing(session.get(url, stream = True)) as r2:
                    contentLength = int(r2.headers['content-length'])
                    progress = xbmcgui.DialogProgress()
                    progress.create('Film letöltése')

                    numberOfChunk = 0
                    for chunk in r2.iter_content(chunk_size=(4*1024*1024)):
                        numberOfChunk = numberOfChunk + (4*1024*1024)
                        if chunk:
                            contentFile.write(chunk)
                        if (progress.iscanceled()):
                            return None
                        progress.update((numberOfChunk/(contentLength/100)), 'Fájl hossza: ' + str(contentLength/(1024*1024)) + 'MB')
                contentFile.close();
                return "DONE"
            else:
               r = session.get(url).text

    except AttributeError:
        xbmc.executebuiltin("HIBA: {0}".format(AttributeError.message))
        if post:
            r = session.post(url, data=post, verify=False, timeout=10).text
        else:
            r = session.get(url, verify=False).text

    if referer:
#        sys.stderr.write('return binary')
        return r
    else:
#        sys.stderr.write('return text')
        return py2_encode(r)

def play_videourl(video_url, videoname, thumbnail, referedUrl):
    global session

    if (forceDownload == 'true'):
        retVal = load(baseUrl + video_url, None, referedUrl)
        if retVal:
            videoitem = xbmcgui.ListItem(label=videoname)
            videoitem.setArt({'thumb': baseUrl + thumbnail})
            videoitem.setInfo(type='Video', infoLabels={'Title': videoname})
            xbmc.Player().play(tmpDir + 'videocontent', videoitem)
    else:
        doLogin()

        cookieFile = open(userDataDir + '/animeaddicts.cookies', 'rb')
        tmpCookies = requests.utils.cookiejar_from_dict(pickle.load(cookieFile))
        cookieFile.close()

        cookie = {'AnimeAddicts': tmpCookies.get('AnimeAddicts', ''), 'AnimeAddictsCookieExpire': tmpCookies.get('AnimeAddictsCookieExpire', ''), 'PHPSESSID': tmpCookies.get('PHPSESSID', '')}
        tmpString = "AnimeAddicts=" + tmpCookies.get('AnimeAddicts', '') + ";AnimeAddictsCookieExpire=" + tmpCookies.get('AnimeAddictsCookieExpire', '') + ";PHPSESSID=" + tmpCookies.get('PHPSESSID', '')
        video_url = video_url + "|Cookie=" + quote_plus(tmpString)
        video_url = video_url + "&" + urlencode({'Host' : 'animeaddicts.hu', 'Referer' : referedUrl})
        video_url = video_url + "&verifypeer=false"
        videoitem = xbmcgui.ListItem(label=videoname)
        videoitem.setArt({'thumb': baseUrl + thumbnail})
        videoitem.setInfo(type='Video', infoLabels={'Title': videoname})
        xbmc.Player().play(baseUrl + video_url, videoitem)

    return

def build_main_directory():
    localurl = sys.argv[0]+'?mode=changeDir&dirName=Befejezett'
    li = xbmcgui.ListItem('Befejezett')
    li.setArt({'icon': thisAddonDir + '/icon.png', 'fanart': thisAddonDir + '/fanart.jpg'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Aktualis'
    li = xbmcgui.ListItem('Aktuális')
    li.setArt({'icon': thisAddonDir + '/icon.png', 'fanart': thisAddonDir + '/fanart.jpg'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Kategoria'
    li = xbmcgui.ListItem('Kategóriák')
    li.setArt({'icon': thisAddonDir + '/icon.png', 'fanart': thisAddonDir + '/fanart.jpg'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista'
    li = xbmcgui.ListItem('Saját listák')
    li.setArt({'icon': thisAddonDir + '/icon.png', 'fanart': thisAddonDir + '/fanart.jpg'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Kereses'
    li = xbmcgui.ListItem('Keresés')
    li.setArt({'icon': thisAddonDir + '/icon.png', 'fanart': thisAddonDir + '/fanart.jpg'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=ClearDB'
    li = xbmcgui.ListItem('Adatbázis frissítése')
    li.setArt({'icon': thisAddonDir + '/icon.png', 'fanart': thisAddonDir + '/fanart.jpg'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)
    return

def build_sub_directory(subDir, category, animeUrl):
    global myMoviedb

    if (subDir[0] == 'Hasonlo'):
        url_content = load(baseUrl + animeUrl)
        completedList = re.compile("<a href='(.*?)'><img src='./theme/modules/project/review.jpg' alt='Ismertető'", re.MULTILINE).findall(url_content)

        if (len(completedList) > 0):
            url_content = load(baseUrl + completedList[0])
            completedList = re.compile("Hasonlónak jelölt művek:(.*?)</div></tr></table></div>", re.MULTILINE|re.DOTALL).findall(url_content)

            if (len(completedList) > 0):
                completedList2 = re.compile("<a href='(.*?)' class='tool_trigger' title='Empty'.*?src='(.*?)' alt='Főkép'.*?<strong>(.*?)</strong>", re.MULTILINE|re.DOTALL).findall(completedList[0])

                for x in range(0, len(completedList2)):
                    localurl = baseUrl + completedList2[x][0];
                    localurl = "?mode=listMovieParts&" + urlencode({'urlToPlay' : localurl})
                    localurl = sys.argv[0] + localurl

                    thumbnail = str(completedList2[x][1])
                    thumbnail = thumbnail.replace('_normal', '')
                    thumbnail = baseUrl + thumbnail
                    sys.stderr.write('thumbnail: ' + thumbnail)
                    li = xbmcgui.ListItem(completedList2[x][2])
                    li.setArt({'icon': thumbnail, 'thumb': thumbnail, 'poster': thumbnail, 'fanart': thumbnail})
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(addon_handle)
        return

    if (subDir[0] == 'Kapcsolodo'):
        url_content = load(baseUrl + animeUrl)
        completedList = re.compile("<a href='(.*?)'><img src='./theme/modules/project/review.jpg' alt='Ismertető'", re.MULTILINE).findall(url_content)

        if (len(completedList) > 0):
            url_content = load(baseUrl + completedList[0])
            completedList = re.compile("Közvetlenül kapcsolódó művek:</div>(.*?)</td></tr></table></div>", re.MULTILINE|re.DOTALL).findall(url_content)

            if (len(completedList) > 0):
                completedList2 = re.compile("<a href='(.*?)' class='tool_trigger' title='Empty'.*?src='(.*?)' alt='Főkép'.*?<strong>(.*?)</strong>", re.MULTILINE|re.DOTALL).findall(completedList[0])

                for x in range(0, len(completedList2)):
                    localurl = baseUrl + completedList2[x][0];
                    localurl = "?mode=listMovieParts&" + urlencode({'urlToPlay' : localurl})
                    localurl = sys.argv[0] + localurl

                    thumbnail = str(completedList2[x][1])
                    thumbnail = thumbnail.replace('_normal', '')
                    thumbnail = baseUrl + thumbnail
                    sys.stderr.write('thumbnail: ' + thumbnail)
                    li = xbmcgui.ListItem(completedList2[x][2])
                    li.setArt({'icon': thumbnail, 'thumb': thumbnail, 'poster': thumbnail, 'fanart': thumbnail})
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(addon_handle)
        return

    if (subDir[0].startswith('Sajatlista_')):
        url_content = load(baseUrl + '/news.php?news')
        completedList = re.compile("<a href='encyclopedia.php\?mylist.(.*?).anime.saw'", re.MULTILINE|re.DOTALL).findall(url_content)
        if (len(completedList) > 0):
            userID = str(completedList[0])

            if (subDir[0].endswith('Befejezett')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.saw')

            if (subDir[0].endswith('Aktualis')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.watch')

            if (subDir[0].endswith('Tervezett')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.towatch')

            if (subDir[0].endswith('Felfuggesztett')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.stalled')

            if (subDir[0].endswith('Dobott')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.dropped')

            if (subDir[0].endswith('Kedvenc')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.favourite')

            if (subDir[0].endswith('Utalt')):
                url_content = load(baseUrl + 'encyclopedia.php?mylist.' + userID + '.anime.hated')

            completedList = re.compile("<td  style='width:58px;'>.*?<a href='(.*?)'>.*?<img src='(.*?)' alt='(.*?)'", re.MULTILINE|re.DOTALL).findall(url_content)
            for x in range(0, len(completedList)):
                localurl = completedList[x][0];
                localurl = "?mode=listMovieParts&" + urlencode({'urlToPlay' : localurl})
                localurl = sys.argv[0] + localurl

                thumbnail = str(completedList[x][1])
                thumbnail = thumbnail.replace('_thumb', '')
                thumbnail = baseUrl + thumbnail
                li = xbmcgui.ListItem(completedList[x][2])
                li.setArt({'icon': thumbnail, 'thumb': thumbnail, 'poster': thumbnail, 'fanart': thumbnail})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(addon_handle)
        return

    if (subDir[0] == 'Sajatlista'):
        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Befejezett'
        li = xbmcgui.ListItem('Befejezett')
        li.setArt({'icon': thisAddonDir + '/resources/ok_gray_256.png', 'fanart': thisAddonDir + '/fanart.jpg'})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Aktualis'
        li = xbmcgui.ListItem('Aktuális')
        li.setArt({'icon': thisAddonDir + '/resources/watch_256.png', 'fanart': thisAddonDir + '/fanart.jpg'})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Tervezett'
        li = xbmcgui.ListItem('Tervezett')
        li.setArt({'icon': thisAddonDir + '/resources/towatch_256.png', 'fanart': thisAddonDir + '/fanart.jpg'})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Felfuggesztett'
        li = xbmcgui.ListItem('Felfüggesztett')
        li.setArt({'icon': thisAddonDir + '/resources/stalled_256.png', 'fanart': thisAddonDir + '/fanart.jpg'})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Dobott'
        li = xbmcgui.ListItem('Dobott')
        li.setArt({'icon': thisAddonDir + '/resources/dropped_256.png', 'fanart': thisAddonDir + '/fanart.jpg'})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Kedvenc'
        li = xbmcgui.ListItem('Kedvenc')
        li.setArt({'icon': thisAddonDir + '/resources/favourite_256.png', 'fanart': thisAddonDir + '/fanart.jpg'})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        localurl = sys.argv[0]+'?mode=changeDir&dirName=Sajatlista_Utalt'
        li = xbmcgui.ListItem('Utált')
        li.setArt({'icon': thisAddonDir + '/resources/hated_256.png', 'fanart': thisAddonDir + '/fanart.jpg'})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(addon_handle)
        return

    if (subDir[0] == 'Kereses'):
        kb=xbmc.Keyboard('', 'Keresés', False)
        kb.doModal()
        if (kb.isConfirmed()):
            searchText = kb.getText()
            for movie in myMoviedb.movies:
                if re.search(py2_decode(searchText), movie.name, re.IGNORECASE):
                    li = xbmcgui.ListItem(movie.name)
                    info = {
                        'genre': movie.genre,
                        'year': movie.year,
                        'title': movie.title,
                    }
                    li.setInfo('video', info)
                    li.setArt({'icon': baseUrl + movie.thumbnailurl, 'thumb': baseUrl + movie.thumbnailurl, 'poster': baseUrl + movie.thumbnailurl, 'fanart': baseUrl + movie.thumbnailurl})
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+movie.url, listitem=li, isFolder=True)
            xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'Kategoria'):
        categories = set()
        for movie in myMoviedb.movies:
            for cat in movie.categories:
                categories.add(cat)

        categories = sorted(categories)
        for cat in categories:
            localurl = sys.argv[0]+'?mode=changeDir&dirName=KategorianBelul&' + urlencode({'category' : py2_encode(cat)}) 
            li = xbmcgui.ListItem(cat)
            li.setArt({'icon': thisAddonDir + '/icon.png', 'fanart': thisAddonDir + '/fanart.jpg'})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(addon_handle)
        return 

    if (subDir[0] == 'KategorianBelul'):
        for movie in myMoviedb.movies:
            for cat in movie.categories:
                if cat == py2_decode(category[0]):
                    li = xbmcgui.ListItem(movie.name)
                    info = {
                        'genre': movie.genre,
                        'year': movie.year,
                        'title': movie.title,
                    }
                    li.setInfo('video', info)
                    li.setArt({'icon': baseUrl + movie.thumbnailurl, 'thumb': baseUrl + movie.thumbnailurl, 'poster': baseUrl + movie.thumbnailurl, 'fanart': baseUrl + movie.thumbnailurl})
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+movie.url, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle)
        return

    if (subDir[0] == 'ClearDB'):
        myMoviedb = Moviedb()
        update_movie_db(baseUrl + 'project.php?completed.jap', dbProjectCompleted)
        update_movie_db(baseUrl + 'project.php?ongoing.jap', dbProjectActual)
        fetch_movie_db()
        return

    if (subDir[0] == 'Befejezett'):
        for movie in myMoviedb.movies:
            if movie.projectstatus == py2_decode(dbProjectCompleted):
                li = xbmcgui.ListItem(movie.name)
                info = {
                    'genre': movie.genre,
                    'year': movie.year,
                    'title': movie.title,
                }
                li.setInfo('video', info)
                li.setArt({'icon': baseUrl + movie.thumbnailurl, 'thumb': baseUrl + movie.thumbnailurl, 'poster': baseUrl + movie.thumbnailurl, 'fanart': baseUrl + movie.thumbnailurl})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+movie.url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(addon_handle)
        return

    if (subDir[0] == 'Aktualis'):
        for movie in myMoviedb.movies:
            if movie.projectstatus == py2_decode(dbProjectActual):
                li = xbmcgui.ListItem(movie.name)
                info = {
                    'genre': movie.genre,
                    'year': movie.year,
                    'title': movie.title,
                }
                li.setInfo('video', info)
                li.setArt({'icon': baseUrl + movie.thumbnailurl, 'thumb': baseUrl + movie.thumbnailurl, 'poster': baseUrl + movie.thumbnailurl, 'fanart': baseUrl + movie.thumbnailurl})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+movie.url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(addon_handle)
        return
    return

def build_url_sub_directory(urlToPlay):
    global session

    if (urlToPlay.find('encyclopedia.php') > -1):
        url_content = load(urlToPlay)
        completedList = re.compile("<a href='(.*?)'.*?>videó").findall(url_content)
        if (len(completedList) > 0):
            urlToPlay = str(completedList[0])

    url_content = load(baseUrl + urlToPlay)
    completedList = re.compile("<div style='width:100px;height:75px;background:#000 url[(](.*?)[)].*?<h1 style='margin-bottom:5px;'>(.*?)</h1>.*?<a href='(.*?)'><img src=.*?<a href='(.*?)'.*?<a href='(.*?)'", re.MULTILINE|re.DOTALL).findall(url_content)

    if (len(completedList) > 0):
        for x in range(0, len(completedList)):
            li = xbmcgui.ListItem(html.unescape(py2_decode(completedList[x][1])))
            li.setArt({'icon': baseUrl + completedList[x][0]})
            a = completedList[x][2].find('.html5')

            movieUrl = completedList[x][2]
            if (a > -1):
                movieUrl = movieUrl[:a]
            movieUrl = movieUrl.replace('view', 'request')
            if (hdVideo == 'FHD'):
                fhdUrl = completedList[x][3]
                sys.stderr.write('fhdUrl: ' + fhdUrl)
                if (fhdUrl.find('.FD') > -1):
                    movieUrl = movieUrl + '.FD'
            if (hdVideo == 'SD'):
                movieUrl = movieUrl + '.SD'

            xbmcplugin.addDirectoryItem(handle=addon_handle, url=sys.argv[0]+"?mode=playUrl&" + urlencode({'urlToPlay' : movieUrl}) + "&" + urlencode({'referedUrl' : baseUrl + urlToPlay}) + "&" + urlencode({'videoName' : completedList[x][1]}) + "&" + urlencode({'videoThumbnail' : completedList[x][0]}), listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Kapcsolodo&' + urlencode({'urlToPlay' : urlToPlay})
    li = xbmcgui.ListItem('Közvetlenül kapcsolódó művek')
    li.setArt({'icon': thisAddonDir + '/icon.png', 'fanart': thisAddonDir + '/fanart.jpg'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    localurl = sys.argv[0]+'?mode=changeDir&dirName=Hasonlo&' + urlencode({'urlToPlay' : urlToPlay})
    li = xbmcgui.ListItem('Hasonlónak jelölt művek',)
    li.setArt({'icon': thisAddonDir + '/icon.png', 'fanart': thisAddonDir + '/fanart.jpg'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localurl, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)

    return


def update_movie_db(url, projectStatus):
    global myMoviedb

    url_content = load(url)
    completedList = re.compile("<h1><a href='(.*?)'>(.*?)</a></h1>.*?<img src='(.*?)'.*?<strong>(Frissítve|Befejezve):</strong>(.*?)<.*?<span style='font-size:.*?;'>(.*?)<", re.MULTILINE|re.DOTALL).findall(url_content)

    if (len(completedList) > 0):
        for x in range(0, len(completedList)):
            name = html.unescape(py2_decode(completedList[x][1]))
            url = completedList[x][0];
            a = url.find('\'')
            if (a > -1):
                url = url[:a]

            url = "?mode=listMovieParts&" + urlencode({'urlToPlay' : url})
            url = sys.argv[0] + url

            genre = py2_decode(completedList[x][5])
            year = py2_decode(completedList[x][4].strip()[:4])
            thumburl = completedList[x][2]

            myMovie = Movie(name, url, genre, year, '', thumburl, projectStatus)

            categories = genre.split(',')
            if (len(categories) > 0):
                for y in range(0, len(categories)):
                    category = categories[y].strip()
                    if (len(category) > 0):
                        myMovie.addCategory(category)

            myMoviedb.addMovie(myMovie)
    return

def fetch_movie_db():
    global myMoviedb

    sys.stderr.write('Refresh animeaddicts database...')

    try:
        os.remove(userDataDir + '/animeaddicts.db')
    except:
        pass

    try:
        dbFile = open(userDataDir + '/animeaddicts.db', 'wb')
        pickle.dump(myMoviedb, dbFile)
        dbFile.close()
    except:
        pass

# main...
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'movies')

mode = args.get('mode', None)
subDir = args.get('dirName', None)
category = args.get('category', None)
urlToPlay = args.get('urlToPlay', None)
referedUrl = args.get('referedUrl', None)
videoName = args.get('videoName', None)
videoThumbnail = args.get('videoThumbnail', None)

myMoviedb = Moviedb()
try:
    dbFile = open(userDataDir + '/animeaddicts.db', 'rb')
    myMoviedb = pickle.load(dbFile)
    dbFile.close()
except:
    pass


if myMoviedb.isSyncNeed():
    myMoviedb = Moviedb()
    update_movie_db(baseUrl + 'project.php?completed.jap', dbProjectCompleted)
    update_movie_db(baseUrl + 'project.php?ongoing.jap', dbProjectActual)
    fetch_movie_db()

if mode is None:
    doLogin()
    build_main_directory()
elif mode[0] == 'changeDir':
    if (urlToPlay is None):
        build_sub_directory(subDir, category, '')
    else:
        build_sub_directory(subDir, category, urlToPlay[0])
elif mode[0] == 'listMovieParts':
    build_url_sub_directory(urlToPlay[0])
elif mode[0] == 'openSetup':
    addon.openSettings()
elif mode[0] == 'playUrl':
    play_videourl(urlToPlay[0], videoName[0], videoThumbnail[0], referedUrl[0])
