# -*- coding: utf-8 -*-
import os
import time
import urllib2
import xbmcgui
from xbmcswift2 import Plugin

plugin = Plugin()
pgpath = plugin.addon.getAddonInfo('path')
DEFAULT_CAPTCHA = os.path.join(pgpath, 'resources', 'images', 'noimage.gif')

ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_CONTEXT_MENU = 117

CTRL_ID_BACK = 8
CTRL_ID_SPACE = 32
CTRL_ID_RETN = 300
CTRL_ID_MAYS = 302
CTRL_ID_CAPS = 303
CTRL_ID_SYMB = 304
CTRL_ID_IP = 307
CTRL_ID_TEXT = 310
CTRL_ID_HEAD = 311
CTRL_ID_HZLIST = 402

CTRL_ID_CAPTCHA = 4002


class InputWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.totalpage = 1
        self.nowpage = 0
        self.words = ''
        self.url = kwargs.get("url")
        self.inputString = kwargs.get("default") or ""
        self.heading = kwargs.get("heading") or ""
        # self.captcha = kwargs.get( "captcha" ) or ""
        self.captcha, self.verify_key = self.initializeImage()
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def initializeImage(self):
        try:
            capimg = os.path.join(pgpath, 'resources', 'images', 'captcha.png')
            url = '%s=%s' % (self.url, int(time.time()*1000))
            rsp = urllib2.urlopen(url)
            cookie = rsp.info()['Set-Cookie']
            localfile = open(capimg, "wb")
            localfile.write(rsp.read())
            rsp.close()
            localfile.close()
            print cookie
            return capimg, cookie
        except:
            import sys
            for line in sys.exc_info():
                print line

    def onInit(self):
        self.setKeyOnKeyboard()
        self.getControl(CTRL_ID_HEAD).setLabel(self.heading)
        self.getControl(CTRL_ID_TEXT).setLabel(self.inputString)
        self.getControl(CTRL_ID_CAPTCHA).setImage(self.captcha)
        self.confirmed = False

    def onFocus(self, controlId):
        self.controlId = controlId

    def onClick(self, controlID):
        if controlID == CTRL_ID_CAPS:  # big
            self.getControl(CTRL_ID_SYMB).setSelected(False)
            if self.getControl(CTRL_ID_CAPS).isSelected():
                self.getControl(CTRL_ID_MAYS).setSelected(False)
            self.setKeyOnKeyboard()
        elif controlID == CTRL_ID_IP:  # ip
            diaimg, self.verify_key = self.initializeImage()
            img_control = self.getControl(CTRL_ID_CAPTCHA)
            img_control.setImage('')
            img_control.setImage(diaimg)
            self.getControl(CTRL_ID_TEXT).setLabel('')
        elif controlID == CTRL_ID_SYMB:  # num
            self.getControl(CTRL_ID_MAYS).setSelected(False)
            self.getControl(CTRL_ID_CAPS).setSelected(False)
            self.setKeyOnKeyboard()
        elif controlID == CTRL_ID_MAYS:
            self.getControl(CTRL_ID_SYMB).setSelected(False)
            if self.getControl(CTRL_ID_MAYS).isSelected():
                self.getControl(CTRL_ID_CAPS).setSelected(False)
            self.setKeyOnKeyboard()
        elif controlID == CTRL_ID_BACK:  # back
            self.getControl(CTRL_ID_TEXT).setLabel(
                self.getControl(CTRL_ID_TEXT).getLabel().decode("utf-8")[0:-1])
        elif controlID == CTRL_ID_RETN:  # enter
            newText = self.getControl(CTRL_ID_TEXT).getLabel()
            if not newText:
                return
            self.inputString = newText
            self.confirmed = True
            self.close()
        elif controlID == CTRL_ID_SPACE:  # space
            self.getControl(CTRL_ID_TEXT).setLabel(
                self.getControl(CTRL_ID_TEXT).getLabel() + ' ')
            self.disableMayus()
        else:
            self.getControl(CTRL_ID_TEXT).setLabel('{0}{1}'.format(
                self.getControl(CTRL_ID_TEXT).getLabel(),
                self.getControl(controlID).getLabel().encode('utf-8')))
            self.disableMayus()

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()
        else:
            # id = action.getId()
            keycode = action.getButtonCode()
            if keycode >= 61505 and keycode <= 61530:
                if self.getControl(CTRL_ID_CAPS).isSelected() or \
                   self.getControl(CTRL_ID_MAYS).isSelected():
                    keychar = chr(keycode - 61505 + ord('A'))
                else:
                    keychar = chr(keycode - 61505 + ord('a'))
                self.getControl(CTRL_ID_TEXT).setLabel(
                    self.getControl(CTRL_ID_TEXT).getLabel()+keychar)
                self.disableMayus()

            elif keycode >= 192577 and keycode <= 192602:
                if self.getControl(CTRL_ID_CAPS).isSelected() or \
                   self.getControl(CTRL_ID_MAYS).isSelected():
                    keychar = chr(keycode - 192577 + ord('a'))
                else:
                    keychar = chr(keycode - 192577 + ord('A'))
                self.getControl(CTRL_ID_TEXT).setLabel(
                    self.getControl(CTRL_ID_TEXT).getLabel()+keychar)
                self.disableMayus()

            elif keycode >= 61488 and keycode <= 61497:
                self.onClick(keycode-61488+48)
            elif keycode == 61472:
                self.onClick(CTRL_ID_SPACE)
            elif keycode == 61448:
                self.onClick(CTRL_ID_BACK)
            elif keycode != 0:
                pass
                # s = "Unattended keycode: " + str(action.getButtonCode())

    def disableMayus(self):
        if self.getControl(CTRL_ID_MAYS).isSelected():
                self.getControl(CTRL_ID_MAYS).setSelected(False)
                self.setKeyOnKeyboard()

    def setKeyOnKeyboard(self):
        if self.getControl(CTRL_ID_SYMB).isSelected():
            # if self.getControl(CTRL_ID_LANG).isSelected():
            #    pass
            # else:
                i = 48
                for c in ')!@#$%^&*(':
                    self.getControl(i).setLabel(c)
                    i += 1
                    if i > 57:
                        break
                i = 65
                for c in '[]{}-_=+;:\'",.<>/?\\|`~':
                    self.getControl(i).setLabel(c)
                    i += 1
                    if i > 90:
                        break
                for j in range(i, 90+1):
                    self.getControl(j).setLabel('')
        else:
            for i in range(48, 57+1):
                keychar = chr(i - 48 + ord('0'))
                self.getControl(i).setLabel(keychar)
            if self.getControl(CTRL_ID_CAPS).isSelected() or \
               self.getControl(CTRL_ID_MAYS).isSelected():
                for i in range(65, 90+1):
                    keychar = chr(i - 65 + ord('A'))
                    self.getControl(i).setLabel(keychar)
            else:
                for i in range(65, 90+1):
                    keychar = chr(i - 65 + ord('a'))
                    self.getControl(i).setLabel(keychar)

    def isConfirmed(self):
        return self.confirmed

    def getText(self):
        return self.inputString + '||' + self.verify_key


class CaptchaDialog(object):
    def __init__(self, url, default='', heading=''):
        self.confirmed = False
        self.inputString = default
        self.heading = heading
        self.url = url

    def doModal(self):
        self.win = InputWindow(
            'Captcha.xml', pgpath, defaultSkin='Default', heading=self.heading,
            default=self.inputString, url=self.url)
        self.win.doModal()
        self.confirmed = self.win.isConfirmed()
        self.inputString = self.win.getText()
        del self.win

    def setHeading(self, heading):
        self.heading = heading

    def isConfirmed(self):
        return self.confirmed

    def getText(self):
        return self.inputString
