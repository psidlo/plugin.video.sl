# -*- coding: utf-8 -*-
# Author: cache
# Created on: 11.4.2019
import sys
import inputstreamhelper
import logger
import requests
import skylink
import exports
import xbmc
import xbmcaddon
import xbmcgui
import urlparse
import urllib
import xbmcplugin
import datetime

_url = sys.argv[0]
_handle = int(sys.argv[1])
_addon = xbmcaddon.Addon()

LOGO_BASE = 'https://koperfieldcz.github.io/skylink-livetv-logos/' #TODO - settings?
REPLAY_GAP = 5 #gap after program ends til it shows in replay

def get_url(**kwargs):
	return '{0}?{1}'.format(_url, urllib.urlencode(kwargs, 'utf-8'))

def channels(sl):
    try:
        channels = sl.channels(True)
    except skylink.TooManyDevicesException as e:
        if _addon.getSetting('reuse_last_device') == 'true':
            device = get_last_used_device(e.devices)
        else:
            device = select_device(e.devices)

        if device != '':
            logger.log.info('reconnecting as: ' + device)
            sl.reconnect(device)
            channels = sl.channels(True)
    except requests.exceptions.ConnectionError:
        dialog = xbmcgui.Dialog()
        dialog.ok(_addon.getAddonInfo('name'), _addon.getLocalizedString(30506))

    xbmcplugin.setPluginCategory(_handle, _addon.getLocalizedString(30600))
    xbmcplugin.setContent(_handle, 'videos')
    if channels:
        for channel in channels:
            logo_id = exports.logo_id(channel['title'])
            list_item = xbmcgui.ListItem(label=channel['title'])
            list_item.setInfo('video', {'title': channel['title']}) #TODO - genre?
            list_item.setArt({'thumb': LOGO_BASE + logo_id + '.png',
                                'icon': LOGO_BASE + logo_id + '.png'})
            link = get_url(replay='days', stationid=channel['stationid'], channel=channel['title'])
            is_folder = True
            xbmcplugin.addDirectoryItem(_handle, link, list_item, is_folder)
    xbmcplugin.endOfDirectory(_handle)

def days(sl, stationid, channel):
    now = datetime.datetime.now()
    xbmcplugin.setPluginCategory(_handle, _addon.getLocalizedString(30600) + ' / ' + channel)
    xbmcplugin.setContent(_handle, 'videos')
    for day in range (0,7):
        d = now - datetime.timedelta(days=day) if day > 0 else now
        title = _addon.getLocalizedString(30601) if day == 0 else _addon.getLocalizedString(30602) if day == 1 else d.strftime('%d. %m.').decode('UTF-8')
        title = _addon.getLocalizedString(int('3061' + str(d.weekday()))) + ', ' + title
        list_item = xbmcgui.ListItem(label=title)
        link = get_url(replay='programs', stationid=stationid, channel=channel, day=day, first=True)
        is_folder = True
        xbmcplugin.addDirectoryItem(_handle, link, list_item, is_folder)
    xbmcplugin.endOfDirectory(_handle)

def programs(sl, stationid, channel, day=0, first=False):
    today = day == 0
    if today:
        now = datetime.datetime.now()
    try:
        epg = sl.epg([{'stationid':stationid}], None, day, True)
    except skylink.TooManyDevicesException as e:
        if _addon.getSetting('reuse_last_device') == 'true':
            device = get_last_used_device(e.devices)
        else:
            device = select_device(e.devices)

        if device != '':
            logger.log.info('reconnecting as: ' + device)
            sl.reconnect(device)
            epg = sl.epg([{'stationid':stationid}], None, day, True)
    except requests.exceptions.ConnectionError:
        dialog = xbmcgui.Dialog()
        dialog.ok(_addon.getAddonInfo('name'), _addon.getLocalizedString(30506))

    xbmcplugin.setPluginCategory(_handle, _addon.getLocalizedString(30600) + ' / ' + channel)
    xbmcplugin.setContent(_handle, 'videos')
    if day < 6:
        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30604))
        link = get_url(replay='programs', stationid=stationid, channel=channel, day=day+1)
        is_folder = True
        xbmcplugin.addDirectoryItem(_handle, link, list_item, is_folder)
    if epg:
        for program in epg[0][stationid]:
            start = datetime.datetime.fromtimestamp(program['start'])
            show_item = not today or start + datetime.timedelta(minutes=program['duration']+REPLAY_GAP) < now
            if show_item:
                title = start.strftime('%H:%M').decode('UTF-8')
                title = title[1:] if title.startswith('0') else title
                title = title + ' - ' + program['title']
                list_item = xbmcgui.ListItem(label=title)
                list_item.setInfo('video', {
                    'title': program['title'],
                    'duration': program['duration'] * 60
                })
                if 'cover' in program:
                    cover = sl.getUrl() + "/" + program['cover']
                    list_item.setArt({'thumb': cover, 'icon': cover})
                
                link = get_url(replay='replay', locId=program['locId'])
                is_folder = False
                list_item.setProperty('IsPlayable','true')
                xbmcplugin.addDirectoryItem(_handle, link, list_item, is_folder)
    if day > 0:
        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30603))
        link = get_url(replay='programs', stationid=stationid, channel=channel, day=day-1)
        is_folder = True
        xbmcplugin.addDirectoryItem(_handle, link, list_item, is_folder)

    xbmcplugin.endOfDirectory(_handle, updateListing=not first)

def replay(sl, locId):
    try:
        info = sl.replay_info(locId)
    except skylink.TooManyDevicesException as e:
        if _addon.getSetting('reuse_last_device') == 'true':
            device = get_last_used_device(e.devices)
        else:
            device = select_device(e.devices)

        if device != '':
            logger.log.info('reconnecting as: ' + device)
            sl.reconnect(device)
            info = sl.replay_info(locId)
    except requests.exceptions.ConnectionError:
        dialog = xbmcgui.Dialog()
        dialog.ok(_addon.getAddonInfo('name'), _addon.getLocalizedString(30506))

    if info:
        is_helper = inputstreamhelper.Helper(info['protocol'], drm=info['drm'])
        if is_helper.check_inputstream():
            playitem = xbmcgui.ListItem(path=info['path'])
            playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
            playitem.setProperty('inputstream.adaptive.manifest_type', info['protocol'])
            playitem.setProperty('inputstream.adaptive.license_type', info['drm'])
            playitem.setProperty('inputstream.adaptive.license_key', info['key'])
            xbmcplugin.setResolvedUrl(_handle, True, playitem)


def router(args, sl):
    if args:
        if args['replay'][0] == 'programs':
            programs(sl, args['stationid'][0], args['channel'][0], int(args['day'][0]) if 'day' in args else 0, 'first' in args)
        elif args['replay'][0] == 'replay':
            replay(sl, args['locId'][0])
        elif args['replay'][0] == 'days':
            days(sl, args['stationid'][0], args['channel'][0])
        else:
            channels(sl)
    else:
        channels(sl)