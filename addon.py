# -*- coding: utf-8 -*-
import os
import re
import gzip
import time
import json
import urllib
import urllib2
import cookielib
import captcha
from random import randint
from StringIO import StringIO
from xbmcswift2 import xbmc
from xbmcswift2 import Plugin
from xbmcswift2 import xbmcgui
from xbmcswift2 import xbmcplugin
from zhcnkbd import Keyboard

plugin = Plugin()

@plugin.route('/')
def index():
    item = [
        {'label': '[登入迅雷] - 白金用户',
         'path': plugin.url_for('login')},
        {'label': '[迅雷云播] - 云播空间',
         'path': plugin.url_for('cloudspace')},
        {'label': '[迅雷离线] - 离线空间',
         'path': plugin.url_for('lxspace', page=1)},
        {'label': '[中文搜索] - BTdigg.org',
         'path': plugin.url_for('btdigg', url='search')},
        {'label': '[英文搜索] - TorrentZ.eu',
         'path': plugin.url_for('torrentz', url='search')},
        {'label': '[豆瓣电影] - 分类浏览',
         'path': plugin.url_for('dbmovie')},
        {'label': '[豆瓣影人] - 影人作品搜索',
         'path': plugin.url_for('dbactor', url='search')},
        {'label': '[豆瓣新片] - TOP10',
         'path': plugin.url_for('dbntop')},
        {'label': '[豆瓣电影] - TOP250',
         'path': plugin.url_for('dbtop', page=0)},
    ]

    return item

@plugin.route('/login')
def login():
    plugin.open_settings()
    user = plugin.get_setting('username')
    passwd = plugin.get_setting('password')
    if not (user and passwd):
        return
    xl = HttpClient()
    vfcodeurl = 'http://login.xunlei.com/check?u={0}&cachetime={1}'.format(
        user, cachetime)
    xl.urlopen(vfcodeurl)
    vfcode = xl.getcookieatt('.xunlei.com', 'check_result')[2:]

    if not vfcode:
        vfcode = xl.getvfcode('http://verify.xunlei.com/image?cachetime=')
        if not vfcode:
            return

    if not re.match(r'^[0-9a-f]{32}$', passwd):
        passwd = xl.md5(xl.md5(passwd))

    passwd = xl.md5(passwd+vfcode.upper())

    data = urllib.urlencode(
        {'u': user,
         'p': passwd,
         'verifycode': vfcode,
         'login_enable': '1',
         'login_hour': '720',}
    )

    xl.urlopen('http://login.xunlei.com/sec2login/', data=data)

    xl.userid = xl.getcookieatt('.xunlei.com', 'userid')
    xl.sid = xl.getcookieatt('.xunlei.com', 'sessionid')

    xl.urlopen(
        'http://dynamic.lixian.vip.xunlei.com/login?cachetime=%s' % cachetime)
    urlpre = 'http://dynamic.cloud.vip.xunlei.com/interface/showtask_unfresh'
    rsp = xl.urlopen('%s?type_id=2&tasknum=1&t=%s' % (urlpre, cachetime))
    data = json.loads(rsp[8:-1])
    gdriveid = data['info']['user']['cookie']

    xl.setcookie('.vip.xunlei.com', 'gdriveid', gdriveid)
    xl.setcookie('.vip.xunlei.com', 'pagenum', '100')
    xl.cookiejar.save(cookiefile, ignore_discard=True)

    blogresult = xl.getcookieatt('.xunlei.com', 'blogresult')
    rst = int(blogresult)
    loginmsgs = ['登入成功', '验证码错误', '密码错误', '用户名不存在']
    plugin.notify(msg=loginmsgs[rst] if rst<3 else '未知错误')
    #for ck in xl.cookiejar:
    #    print (ck.name, ck.value)
    return

@plugin.route('/cloudspace')
def cloudspace():
    dhurl = '%s/%s/?type=all&order=create&t=%s' % (
        urlpre, 'req_history_play_list/req_num/200/req_offset/0', cachetime)
    rsp = xl.urlopen(dhurl)
    vods = json.loads(rsp)['resp']['history_play_list']

    menu = [{'label': urllib2.unquote(v['file_name'].encode('utf-8')),
             'path': plugin.url_for('playcloudvideo', vinfo=str((
                 v['src_url'], v['gcid'], v['cid'], v['file_name'])))
             } for v in vods if 'src_url' in v]
    return menu

@plugin.route('/lxspace/<page>')
def lxspace(page):
    '''
    http://dynamic.cloud.vip.xunlei.com/interface/showtask_unfresh?
    callback=jsonp1392830614727&t=Thu%20Feb%2020%202014%2001:23:35%
    20GMT+0800%20(CST)&type_id=4&page=1&tasknum=30&p=1&interfrom=task
    '''
    urlpre = 'http://dynamic.cloud.vip.xunlei.com/interface/showtask_unfresh'
    rsp = xl.urlopen('%s?t=%s&type_id=4&page=%s&tasknum=30&p=1' % (
        urlpre, cachetime, page))
    data = json.loads(rsp[8:-1])

    menus = [{'label': '[{0}%][{1}]{2}'.format(i['progress'],
                                               i['openformat'],
                                               i['taskname'].encode('utf-8')),
              'path': plugin.url_for(
                  'playlxtid',
                  magnet=i['cid'],
                  lxurl=i['lixian_url'] if i['lixian_url'] else 'bt',
                  title=i['taskname'].encode('utf-8'),
                  taskid=i['id']),
              } for i in data['info']['tasks']]

    total = int(data['info']['user']['total_num'])
    totalpgs = (total+29) // 30
    page = int(page)
    if page-1 > 0:
        menus.append({'label': '上一页',
                      'path': plugin.url_for('lxspace', page=page-1)})
    if page < totalpgs:
        menus.append({'label': '下一页',
                      'path': plugin.url_for('lxspace', page=page+1)})
    menus.insert(0, {'label': '【第%s页/共%s页】返回上级菜单' % (page, totalpgs),
                     'path': plugin.url_for('index')})
    return menus

@plugin.route('/playcloudvideo/<vinfo>')
def playcloudvideo(vinfo):
    protocol = vinfo[:10]
    if 'bt' in protocol or 'magnet' in protocol:
        if 'magnet' in vinfo:
            ihash = addbt(vinfo)
        else:
            _vinfo = eval(vinfo)
            ihash = _vinfo[0][5:]

        subbt = '%s/req_subBT/info_hash/%s/req_num/500/req_offset/0' % (
            urlpre, ihash)
        rsp = xl.urlopen(subbt)
        vfinfo = json.loads(rsp)
        videos = vfinfo['resp']['subfile_list']
        if len(videos) > 1:
            selitem = dialog.select('播放选择',
                                    [urllib2.unquote(v['name'].encode('utf-8'))
                                     for v in videos])
            if selitem is -1: return
            video = videos[selitem]
        else:
            video = videos[0]
        gcid = video['gcid']
        cid = video['cid']
        title = urllib2.quote(video['name'].encode('utf-8'))
    elif 'http' in protocol or 'thunder' in protocol or 'ed2k' in protocol:
        _vinfo = eval(vinfo)
        gcid = _vinfo[1]
        cid = _vinfo[2]
        title = urllib2.quote(_vinfo[3].encode('utf-8'))
    else: return

    dl = '{0}/vod_dl_all?userid={1}&gcid={2}&filename={3}&t={4}'.format(
        urlpre ,xl.userid, gcid, title, cachetime)
    rsp = xl.urlopen(dl)
    vturls = json.loads(rsp)
    typ = {'Full_HD':'1080P', 'HD':'720P', 'SD':'标清'}
    vtyps = [(typ[k], v['url']) for (k, v) in vturls.iteritems() if 'url' in v]

    if not vtyps:
        plugin.notify(msg='视频转码进行中，请稍候尝试从云播空间菜单进入播放')
        return
    if len(vtyps)>1:
        selitem = dialog.select('清晰度', [v[0] for v in vtyps])
        if selitem is -1: return
        vtyp = vtyps[selitem]
    else:
        vtyp = vtyps[0]

    player(vtyp[1], gcid, cid, title)

@plugin.route('/playlxvideo/<magnet>', name='playlxmagnet')
@plugin.route('/playlxvideo/<magnet>/<taskid>/<lxurl>/<title>',
              name='playlxtid')
def playlxvideo(magnet, taskid=None, lxurl=None, title=None):
    '''
    (i['title'], i['size'], i['percent'], i['cid'],
               re.sub(r'.*?&g=', '', i['downurl'])[:40], i['downurl'])
    '''
    urlpre ='http://dynamic.cloud.vip.xunlei.com/interface'
    if taskid:
        sel = dialog.select('选项', ['播放', '删除'])
        if sel is -1:
            return
        if sel is 0:
            pass
        if sel is 1:
            data = {'taskids': taskid+',', 'databases': '0,'}
            print data
            url = '%s/task_delete?callback=jsonp%s&t=%s' % (
                urlpre, cachetime, cachetime)
            rsp = xl.urlopen(url, data=urllib.urlencode(data))
            if 'result":1' in rsp:
                plugin.notify(msg='删除任务成功')
                from itertools import imap
                imap(lambda x: magnets.pop(x),
                     [k for k, v in magnets.iteritems() if taskid in v])
            else:
                plugin.notify(msg='删除任务失败,请稍候重试')
            return

    if lxurl and len(lxurl) > 2:
        cid = magnet
        gcid= re.sub(r'.*?&g=', '', lxurl)[:40]
        title = title
        video = getcloudvideourl(gcid, lxurl, title)
        if not video: return
        player(video[1], gcid, cid, title)
        return
    if magnet and len(magnet)>40:
        tid = gettaskid(magnet)
        infoid = magnet[-40:]
    else:
        infoid = magnet
        tid = taskid
    url = '%s/%s&tid=%s&infoid=%s&g_net=1&p=1&uid=%s&noCacheIE=%s' % (
        urlpre, 'fill_bt_list?callback=fill_bt_list', tid, infoid,
        xl.userid, cachetime)

    rsp = xl.urlopen(url)
    if not xl.getcookieatt('dynamic.cloud.vip.xunlei.com', 'PHPSESSID'):
        xl.cookiejar.save(cookiefile, ignore_discard=True)

    try:
        data = json.loads(rsp[13:-1])
    except ValueError:
        magnets.pop(magnet)
        plugin.notify('该离线任务已删除,请重新添加')
        return

    mitems = [
        (i['title'],
         i['size'],
         i['percent'],
         i['cid'],
         re.sub(r'.*?&g=', '', i['downurl'])[:40],
         i['downurl']
     ) for i in data['Result']['Record']
        if 'movie' in i['openformat'] and i['percent']==100]

    if not mitems:
        plugin.notify('离线下载进行中，请稍候从离线空间播放')
        return

    if len(mitems) > 1:
        sel = dialog.select(
            '播放选择',['[%s]%s[%s]' % (i[2], i[0], i[1])
                        for i in mitems])
        if sel is -1: return
        mov = mitems[sel]
    else:
        mov = mitems[0]

    (name, _, _, cid, gcid, downurl) = mov
    video = getcloudvideourl(gcid, downurl, name.encode('utf-8'))
    if not video: return
    player(video[1], gcid, cid, name)

def player(url, gcid, cid, title):
    rsp = xl.urlopen(url, redirect=False)
    #cks = dict((ck.name, ck.value) for ck in xl.cookiejar)
    cks = ['%s=%s' % (ck.name, ck.value) for ck in xl.cookiejar]
    movurl = '%s|%s&Cookie=%s' % (
        rsp, urllib.urlencode(xl.headers), urllib2.quote('; '.join(cks)))

    #for ck in xl.cookiejar:
    #    print ck.name, ck.value
    listitem=xbmcgui.ListItem(label= title)
    listitem.setInfo(type="Video", infoLabels={'Title': title})
    player = xbmc.Player()
    player.play(movurl, listitem)

    surl = ''
    subtinfo = '{0}/subtitle/list?gcid={1}&cid={2}&userid={3}&t={4}'.format(
        urlpre, gcid, cid, xl.userid, cachetime)
    subtinfo = '%s|%s&Cookie=%s' % (
        subtinfo, urllib.urlencode(xl.headers), urllib2.quote('; '.join(cks)))
    subtitle = xl.urlopen(subtinfo)
    sinfos = json.loads(subtitle)
    surls = ''
    if 'sublist' in sinfos and len(sinfos['sublist']):
        surls = [sinfo['surl'] for sinfo in sinfos['sublist']]
    if surls:
        for _ in xrange(30):
            if player.isPlaying():
                break
            time.sleep(1)
        else:
            raise Exception('No video playing. Aborted after 30 seconds.')
        xl.headers.pop('Accept-encoding')
        for surl in surls:
            player.setSubtitles('%s|%s&Cookie=%s' % (
                surl, urllib.urlencode(xl.headers),
                urllib2.quote('; '.join(cks))))

    #xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

@plugin.route('/btdigg/<url>')
@plugin.route('/btdigg/<url>/<mstr>', name='btsearch')
def btdigg(url, mstr=''):
    if url in 'search':
        url = 'http://btdigg.org/search?q='
        if not mstr:
            kb = Keyboard('',u'请输入搜索关键字')
            kb.doModal()
            if not kb.isConfirmed(): return
            mstr = kb.getText()
            if not mstr: return
        url = url + urllib2.quote(mstr)
    else:
        url = 'http://btdigg.org' + url

    rsp = hc.urlopen(url)
    rpat = re.compile(
        r'"idx">.*?>([^<]+)</a>.*?href="(magnet.*?)".*?Size:.*?">(.*?)<')
    items = rpat.findall(rsp)

    menus = [
        {'label': '%d.%s[%s]' % (s+1, v[0], v[2].replace('&nbsp;', '')),
         'path': plugin.url_for('playlxmagnet', magnet=v[1])}
        for s, v in enumerate(items)]
    ppat = re.compile(r'%s%s' % (
        'class="pager".*?(?:href="(/search.*?)")?>←.*?>',
        '(\d+/\d+).*?(?:href="(/search.*?)")?>Next'))

    pgs = ppat.findall(rsp)

    for s, p in enumerate((pgs[0][0], pgs[0][2])):
        if p:
            menus.append({'label': '上一页' if not s else '下一页',
                          'path': plugin.url_for('btdigg', url=p)})
    menus.insert(0, {'label': '[当前页%s页总共]返回上级目录' % pgs[0][1],
                     'path': plugin.url_for('index')})
    return menus

@plugin.route('/torrentz/<url>')
def torrentz(url):
    if 'p=' not in url:
        url = 'http://torrentz.eu/search?f='
        sel = dialog.select('选择节目类型', ('电影', '电视'))
        if sel is -1: return
        typ = 'shows:' if sel else 'movies:'
        kb = Keyboard('',u'请输入搜索关键字')
        kb.doModal()
        if not kb.isConfirmed(): return
        mstr = kb.getText()
        if not mstr: return
        #stxt = '%s%s' % (typ, mstr.replace(' ', '+'))
        url = '%s%s%s&p=0' % (
            'https://torrentz.eu/search?f=', typ, urllib.quote_plus(mstr))
    print url
    rsp = hc.urlopen(url)
    mitems = re.findall(
        r'"/([0-9a-z]{40})">(.*?)</a>.*?class="s">([^>]+)<', rsp, re.S)

    menus = [{'label': '%s[%s]' % (re.sub(r'<.*?>', '', i[1]), i[2]),
              'path': plugin.url_for('playlxmagnet',
                                     magnet='magnet:?xt=urn:btih:%s' % i[0])
              } for i in mitems]

    cnt = re.findall(r'<h2 style="border-bottom: none">([,0-9]+) Torrents', rsp)
    if cnt:
        cnt = int(cnt[0].replace(',', ''))
        pages = (cnt + 49) // 50
        currpg = int(url.split('=')[-1])
        urlpre = '='.join(url.split('=')[:-1])
        if currpg > 0:
            menus.append({'label': '上一页',
                          'path': plugin.url_for(
                              'torrentz', url='%s=%s' % (urlpre, currpg-1))})
        if (currpg+1) < pages:
            menus.append({'label': '下一页',
                          'path': plugin.url_for(
                              'torrentz', url='%s=%s' % (urlpre, currpg+1))})
        menus.insert(0, {'label':
                         '【第%s页/共%s页】返回上级菜单' % (currpg+1, pages),
                         'path': plugin.url_for('index')})
    return menus

def addbt(magnetid):
    '''
    GET /req_del_list?flag=0&sessionid=sid&t=cachetime&info_hash=ihash
    Host: i.vod.xunlei.com
    '''
    urlpre = 'http://i.vod.xunlei.com'
    data = {"urls":[{"id":0,"url":magnetid}]}
    reqvideo = '%s/req_video_name?from=vlist&platform=0' % urlpre
    rsp = xl.urlopen(reqvideo, data=data)
    minfo = json.loads(rsp)
    acdt = minfo['resp']['res'][0]
    data = {"urls":
            [{'id': acdt['id'], "url": acdt['url'], "name": acdt['name']},]
    }

    addvideo = '{0}/req_add_record?userid={1}&sessionid={2}&{3}'.format(
        urlpre, xl.userid, xl.sid, 'folder_id=0&from=vlist&platform=0')
    rsp = xl.urlopen(addvideo, data=data)
    acinfo = json.loads(rsp)
    ihash = acinfo['resp']['res'][0]['url'][5:]
    return ihash

def gettaskid(magnet):
    '''
    http://verify.xunlei.com/image?t=MVA&cachetime=1392381968052
    '''
    urlpre ='http://dynamic.cloud.vip.xunlei.com/interface'
    if magnet not in magnets:
        url = '%s/url_query?callback=queryUrl&u=%s&random=%s&tcache=%s' % (
            urlpre, urllib2.quote(magnet), random, cachetime)

        rsp = xl.urlopen(url)
        success = re.search(r'queryUrl(\(1,.*\))\s*$', rsp, re.S)
        if not success:
            already_exists = re.search(r"queryUrl\(-1,'([^']{40})", rsp, re.S)
            if already_exists:
                return already_exists.group(1)
            raise NotImplementedError(repr(rsp))
        args = success.group(1).decode('utf-8')
        args = eval(args.replace('new Array', ''))
        _, cid, tsize, btname, _, names, sizes_, sizes, _, types, \
            findexes, timestamp, _ = args
        def toList(x):
            if type(x) in (list, tuple):
                return x
            else:
                return [x]
        data = {'uid':xl.userid, 'btname':btname, 'cid':cid, 'tsize':tsize,
                'findex':''.join(x+'_' for x in toList(findexes)),
                'size':''.join(x+'_' for x in toList(sizes)),
                'from':'0'}
        jsonp = 'jsonp%s' % cachetime
        commiturl = '%s/bt_task_commit?callback=%s' % (urlpre, jsonp)
        rsp = xl.urlopen(commiturl, data=urllib.urlencode(data))
        while '"progress":-11' in rsp or '"progress":-12' in rsp:
            vfcode = xl.getvfcode(
                'http://verify2.xunlei.com/image?t=MVA&cachetime')
            if not vfcode: return
            data['verify_code'] = vfcode
            rsp = xl.urlopen(commiturl, data=urllib.urlencode(data))
        tids = re.findall(r'"id":"(\d+)"', rsp)
        if not tids: return
        magnets[magnet] = tids[0]
    tid = magnets[magnet]
    return tid

def getcloudvideourl(gcid, surl, title):
    dl = '{0}/vod_dl_all?userid={1}&gcid={2}&filename={3}&t={4}'.format(
        'http://i.vod.xunlei.com', xl.userid, gcid,
        urllib2.quote(title), cachetime)
    rsp = xl.urlopen(dl)
    vturls = json.loads(rsp)
    typ = {'Full_HD':'1080P', 'HD':'720P', 'SD':'标清'}
    vtyps = [(typ[k], v['url']) for (k, v) in vturls.iteritems() if 'url' in v]
    vtyps.insert(0, ('源码', surl))
    selitem = dialog.select('清晰度', [v[0] for v in vtyps])
    if selitem is -1: return
    vtyp = vtyps[selitem]
    return vtyp

@plugin.route('/dbmovie')
def dbmovie():
    if '类型' not in filters:
        rsp = hc.urlopen('http://movie.douban.com/category/')
        fts = re.findall(
            r'class="label">([^>]+?)</h4>\s+<ul>(.*?)</ul>', rsp, re.S)
        typpatt = re.compile(r'<a href="#">([^>]+?)</a>')
        for ft in fts:
            typs = typpatt.findall(ft[1])
            if '类型' not in ft[0]:
                typs.insert(0, '不限')
            filters[ft[0]] =  tuple(typs)
    typs = filters['类型']
    menus = [{'label': t,
              'path': plugin.url_for(
                  'dbcate', typ=str({'types[]':t,}), page=1),
              } for t in typs]
    return menus

@plugin.route('/dbcate/<typ>/<page>')
def dbcate(typ, page):
    params  = {'district': '', 'era': '', 'category': 'all',
               'unwatched': 'false', 'available': 'false', 'sortBy': 'score',
               'page': page, 'ck': 'null', 'types[]': ''}
    typ = eval(typ)
    if 'district' in typ and not typ['district']:
        sel = dialog.select('地区', filters['地区'])
        if sel is -1: return
        typ['district'] = filters['地区'][sel]
    if 'era' in typ and not typ['era']:
        sel = dialog.select('年代', filters['年代'])
        if sel is -1: return
        typ['era'] = filters['年代'][sel]
    params.update(typ)
    data = urllib.urlencode(params)
    rsp = hc.urlopen('http://movie.douban.com/category/q',
                data=data.replace(urllib2.quote('不限'), ''))
    minfo = json.loads(rsp)
    print minfo
    menus = [{'label': '[%s].%s[%s][%s]' % (m['release_year'], m['title'],
                                           m['rate'], m['abstract']),
              'path': plugin.url_for(
                  'btsearch', url='search',
                  mstr=m['title'].split(' ')[0].encode('utf-8')),
              'thumbnail': m['poster'],
              } for m in minfo['subjects']]
    if not menus: return
    if int(page) > 1:
        menus.append({'label': '上一页', 'path': plugin.url_for(
            'dbcate', typ=str(typ), page=int(page)-1)})
    menus.append({'label': '下一页', 'path': plugin.url_for(
        'dbcate', typ=str(typ), page=int(page)+1)})
    ntyp = typ.copy()
    ntyp.update({'district': '', 'era': ''})
    menus.insert(0, {
        'label': '【按照条件过滤】【地区】【年代】选择',
        'path': plugin.url_for('dbcate', page=1, typ=str(ntyp)),}
    )
    return menus

@plugin.route('/dbactor/<url>')
def dbactor(url):
    if 'search_text' not in url:
        urlpre = 'http://movie.douban.com/subject_search'
        kb = Keyboard('',u'请输入搜索关键字')
        kb.doModal()
        if not kb.isConfirmed(): return
        sstr = kb.getText()
        url = '%s/?search_text=%s&start=0' % (urlpre ,sstr)
    rsp = hc.urlopen(url)
    rtxt = r'%s%s' % ('tr class="item".*?nbg".*?src="(.*?)" alt="(.*?)"',
                      '.*?class="pl">(.*?)</p>.*?rating_nums">(.*?)<')
    patt = re.compile(rtxt, re.S)
    mitems = patt.findall(rsp)
    if not mitems: return
    menus = [{'label': '{0}. {1}[{2}][{3}]'.format(s, i[1], i[3], i[2]),
             'path': plugin.url_for('btsearch', url='search', mstr=i[1]),
             'thumbnail': i[0],
         } for s, i in enumerate(mitems)]

    cnt = re.findall(r'class="count">.*?(\d+).*?</span>', rsp)
    if cnt:
        cnt = int(cnt[0])
        pages = (cnt + 14) // 15
        curpg = int(url.split('=')[-1]) // 15
        urlpre = '='.join(url.split('=')[:-1])
        if curpg > 0:
            menus.append({'label': '上一页',
                          'path': plugin.url_for(
                              'dbactor', url='%s=%s' % (urlpre, (curpg-1)*15))})
        if (curpg+1) < pages:
            menus.append({'label': '下一页',
                          'path': plugin.url_for(
                              'dbactor', url='%s=%s' % (urlpre, (curpg+1)*15))})
        menus.insert(0, {'label':
                         '【第%s页/共%s页】返回上级菜单' % (curpg+1, pages),
                         'path': plugin.url_for('index')})
    return menus

@plugin.route('/dbntop')
def dbntop():
    '''
    img, title, info, rate
    '''
    rsp = hc.urlopen('http://movie.douban.com/chart')
    mstr = r'%s%s' % ('nbg".*?src="(.*?)" alt="(.*?)"',
                      '.*?class="pl">(.*?)</p>.*?rating_nums">(.*?)<')
    mpatt = re.compile(mstr, re.S)
    mitems = mpatt.findall(rsp)
    menus = [{'label': '{0}. {1}[{2}][{3}]'.format(s, i[1], i[3], i[2]),
             'path': plugin.url_for('btsearch', url='search', mstr=i[1]),
             'thumbnail': i[0],
         } for s, i in enumerate(mitems)]
    return menus

@plugin.route('/dbtop/<page>')
def dbtop(page):
    '''
    title, img, info
    '''
    page = int(page)
    pc = page * 25
    rsp = hc.urlopen('http://movie.douban.com/top250?start={0}'.format(pc))
    mstr = r'class="item".*?alt="(.*?)" src="(.*?)".*?<p class="">\s+(.*?)</p>'
    mpatt = re.compile(mstr, re.S)
    mitems = mpatt.findall(rsp)
    menus = [{'label': '{0}. {1}[{2}]'.format(s+pc+1, i[0], ''.join(
        i[2].replace('&nbsp;', ' ').replace('<br>', ' ').replace(
            '\n', ' ').split(' '))),
              'path': plugin.url_for('btsearch', url='search', mstr=i[0]),
              'thumbnail': i[1],
         } for s, i in enumerate(mitems)]
    if  page != 0:
        menus.append({'label': '上一页',
                      'path': plugin.url_for('dbtop', page=page-1)})
    if page != 10:
        menus.append({'label': '下一页',
                      'path': plugin.url_for('dbtop', page=page+1)})
    return menus


class HttpClient(object):
    def __init__(self, cookiefile = None):
        self.cookiejar = cookielib.LWPCookieJar()
        if cookiefile and os.path.exists(cookiefile):
            self.cookiejar.load(
                cookiefile, ignore_discard=True, ignore_expires=True)
        self.userid = self.getcookieatt('.xunlei.com', 'userid')
        self.sid = self.getcookieatt('.xunlei.com', 'sessionid')
        self.opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self.cookiejar))

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/28.0.1500.71 Safari/537.36',
            'Accept-encoding': 'gzip,deflate',
        }

    class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            infourl = urllib.addinfourl(fp, headers, req.get_full_url())
            infourl.status = code
            infourl.code = code
            return infourl
        http_error_301 = http_error_303 = http_error_307 = http_error_302

    def urlopen(self, url, redirect=True, **args):
        if 'data' in args and type(args['data']) == dict:
            args['data'] = json.dumps(args['data'])
            #arg['data'] = urllib.urlencode(args['data'])
            self.headers['Content-Type'] = 'application/json'
        if not redirect:
            self.opener = urllib2.build_opener(
                self.SmartRedirectHandler(),
                urllib2.HTTPCookieProcessor(self.cookiejar))
        rs = self.opener.open(
            urllib2.Request(url, headers=self.headers, **args), timeout=30)
        if 'Location' in rs.headers:
            return rs.headers.get('Location', '')
        if rs.headers.get('content-encoding', '') == 'gzip':
            content = gzip.GzipFile(fileobj=StringIO(rs.read())).read()
        else:
            content = rs.read()
        return content

    def getcookieatt(self, domain, attr):
        if domain in self.cookiejar._cookies and attr in \
           self.cookiejar._cookies[domain]['/']:
            return self.cookiejar._cookies[domain]['/'][attr].value

    def getvfcode(self, url):
        cdg = captcha.CaptchaDialog(url)
        cdg.doModal()
        confirmed = cdg.isConfirmed()
        if not confirmed:
            return
        info = cdg.getText()
        #del cdg
        vfcode, vfcookie = info.split('||')
        k, v = vfcookie.split('; ')[0].split('=')
        self.setcookie('.xunlei.com', k, v)
        return vfcode

    def setcookie(self, domain, k, v):
        c = cookielib.Cookie(
            version=0, name=k, value=v, comment_url=None, port_specified=False,
            domain=domain, domain_specified=True, path='/', secure=False,
            domain_initial_dot=True, path_specified=True, expires=None,
            discard=True, comment=None, port=None, rest={}, rfc2109=False)
        self.cookiejar.set_cookie(c)
        self.cookiejar.save(cookiefile, ignore_discard=True)

    def md5(self, s):
        import hashlib
        return hashlib.md5(s).hexdigest().lower()

dialog = xbmcgui.Dialog()
ppath = plugin.addon.getAddonInfo('path')
cookiefile = os.path.join(ppath, 'cookie.dat')
xl = HttpClient(cookiefile)
hc = HttpClient()
urlpre = 'http://i.vod.xunlei.com'
cachetime = int(time.time()*1000)
random = '%s%06d.%s' % (cachetime, randint(0, 999999),
                        randint(100000000, 9999999999))
filters = plugin.get_storage('ftcache', TTL=1440)
magnets = plugin.get_storage('ftcache')

if __name__ == '__main__':
    plugin.run()
