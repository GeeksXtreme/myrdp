# -*- coding: utf-8 -*-
from PyQt4.QtCore import pyqtSignal, QObject, Qt, SIGNAL, qDebug
from PyQt4.QtGui import *
#QTabWidget, QWidget, QVBoxLayout, QTextEdit, QFrame, QMenu, QDockWidget
#from PyQt4.QtGui import QTextCursor

class X11Embed(QX11EmbedContainer):
    def __init__(self, parent=None):
        super(X11Embed, self).__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)
#         self.installEventFilter(self)
    #leaveEvent not allways work for e.g when we out from MyRDP trough border, or without mosue
    #so we need, also releaseKeyboard on focusChanged in QApplication
#     def leaveEvent(self, event):
#         self.releaseKeyboard()
#         event.accept()

class PageTab(QWidget):
    widgetClosed = pyqtSignal("QString")
    def __init__(self, parent=None):
        super(PageTab, self).__init__(parent)
        #used for check if process has been stoped
        self.lastState = None
        
        self.layout = QVBoxLayout(self)
        self.layout.setMargin(0)
        
        #bellow each rdesktop instance is text area with stdout/stderr debug
        #if somenthing goes wrong text is visible, but when rdesktop is runnig
        #current display area is covered by rdp.
        #If window is resized, thereis a lot of text, and rdp size is smaller,
        #than display area, you can see the text ;) looks buggy but at this (any:P) time
        #i think that's not important :)

        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setFrameShape(QFrame.NoFrame)
        self.textEdit.setStyleSheet("background-color:transparent;")
        
        self.textEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);
        self.textEdit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);
    
        self.layout.addWidget(self.textEdit)
        
        #to embed rdesktop, if we use QWidget, there is some problems with
        #shortcuts (for e.g. in xfwm4), with QX11EmbedContainer looks good 
        #self.x11 = QX11EmbedContainer(self)
        #self.x11 = QX11EmbedContainer(self)
        self.x11 = X11Embed(self)
        
#    def autoScroll(self):
#        c = self.textEdit.textCursor()
#        c.movePosition(QTextCursor.End)
#        self.textEdit.setTextCursor(c)

    def closeEvent(self, event):
        title = self.windowTitle()
        self.widgetClosed.emit(title)
        event.accept()
        self.deleteLater()


    def setSize(self):
        """ Sets size of QX11EmbedContainer, because QX11 is not in layout, but
            textEdit is. Returns size of textEdit area wich will be used in rdesktop
            geometry (-g) param  
        """
        
        self.x11.setFixedSize(self.textEdit.size())
        return "%sx%s" % (self.textEdit.width(),self.textEdit.height())

    def slotRead(self):
        proc = self.sender() 
        txt = proc.readAllStandardOutput()
        qDebug(txt) 
        self.textEdit.append(txt.data().rstrip('\n'))
#        self.autoScroll()

    def slotStateChanged(self, state):
        #QProcess::NotRunning - 0
        #QProcess::Starting - 1
        #QProcess::Running - 2
        #append text to the text area only when process has been stopped
        if state == 0 and self.lastState == 2:
            self.textEdit.append("<i>Process has been stopped..</i><br />")
        self.lastState = state
        
    def text(self):
        return self.windowTitle()


class MyTabWidget(QTabWidget):
    #to communicate with main window, and send signal with tabName
    tabClosed = pyqtSignal("QString")
    
    def __init__(self):
        super(MyTabWidget, self).__init__()
        self.setTabsClosable(True)
        
        QObject.connect(self, SIGNAL("tabCloseRequested(int)"), self.slotCloseTab)
        self.setStyleSheet("""QTabBar::tab:selected, QTabBar::tab:hover { 
                              background: 
                                qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, 
                                    stop: 0 #fafafa, 
                                    stop: 0.4 #f4f4f4,
                                    stop: 0.5 #e7e7e7,
                                    stop: 1.0 #fafafa); }""")
        self.setMovable(True)
        self.setTab()
        #used when chosing action from menu 
        self.currentTabIdx = None
        
        #list with detached windows
        self.detached = {}
       
    def setTab(self):
        self.tab = self.tabBar()
        self.tab.setContextMenuPolicy(Qt.CustomContextMenu)
        QObject.connect(self.tab, SIGNAL('customContextMenuRequested(const QPoint&)'), self.showContextMenu)
        
        self.popMenu = QMenu(self)
        self.popMenu.addAction("Detach tab", self.detach)
#        self.popMenu.addAction("Reconnect", self.reconnect)
        
    def showContextMenu(self, point):
        self.currentTabIdx = self.tab.tabAt(point)
        self.popMenu.exec_(self.tab.mapToGlobal(point))
        
    def detach(self):
        w = self.widget(self.currentTabIdx)
        w.setParent(None)       
        w.show()
        #temp hack to not delete object, becouse will delete after show
        #todo: do it better
        title = w.windowTitle()
        self.detached[title] = w

#    def reconnect(self):
#        w = self.widget(self.currentTabIdx)
#        print w.text
#        print "reconnect"       
        
    def getTabObjectName(self, item):
        title = item.text()
        return u"p_%s" % title
    
    def createTab(self, item):
        #used for create unique object name (beacause title is unique)
        tabObjectName = self.getTabObjectName(item)
#        tabWidget = self.findChild(QX11EmbedContainer, tabObjectName)
        tabWidget = self.findChild(PageTab, tabObjectName)
        
        for topLevel in QApplication.topLevelWidgets():
            if type(topLevel) == PageTab and topLevel.objectName() == tabObjectName:
                    return topLevel
        
        if tabWidget is None:
            #@todo: maybe we should use scrool area? but why? if size doesn`t fit, just reconnect
            tabTitle = item.text()
            newTab = PageTab(self)
            newTab.setObjectName(tabObjectName)
            tabIdx = self.addTab(newTab, tabTitle)
            newTab.setWindowTitle(tabTitle)
            self.setCurrentIndex(tabIdx)
            return newTab
        else:
            return tabWidget
        
    def activateTab(self, hostId):
        tabName = self.getTabObjectName(hostId)
        tabWidget = self.findChild(PageTab, tabName)
        
        if tabWidget is not None:
            tabIdx = self.indexOf(tabWidget)
            self.setCurrentIndex(tabIdx)
    
    def slotCloseTab(self, tabIdx):
        tabTitle = self.tabText(tabIdx)
        tabWidget = self.widget(tabIdx)
        self.tabClosed.emit(tabTitle)
        self.removeTab(tabIdx)
        tabWidget.deleteLater()

