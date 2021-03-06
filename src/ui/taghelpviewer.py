#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2011  Sergey Satskiy <sergey.satskiy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# $Id$
#

""" The tag help viewer implementation """

from PyQt4.QtCore import Qt, QSize
from PyQt4.QtGui import ( QPlainTextEdit, QMenu, QPalette, QApplication,
                          QCursor, QHBoxLayout, QWidget, QAction, QToolBar,
                          QSizePolicy, QLabel, QVBoxLayout, QFrame, QFont )
from utils.pixmapcache import PixmapCache
from utils.globals import GlobalData


class TagHelpViewer( QWidget ):
    """ The tag help viewer widget """

    def __init__( self, parent = None ):
        QWidget.__init__( self, parent )

        self.__isEmpty = True
        self.__copyAvailable = False
        self.__clearButton = None
        self.__textEdit = None
        self.__header = None
        self.__copyButton = None
        self.__selectAllButton = None
        self.__createLayout( parent )

        # create the context menu
        self.__menu = QMenu( self )
        self.__selectAllMenuItem = self.__menu.addAction(
                            PixmapCache().getIcon( 'selectall.png' ),
                            'Select All', self.__textEdit.selectAll )
        self.__copyMenuItem = self.__menu.addAction(
                            PixmapCache().getIcon( 'copytoclipboard.png' ),
                            'Copy', self.__textEdit.copy )
        self.__menu.addSeparator()
        self.__clearMenuItem = self.__menu.addAction(
                            PixmapCache().getIcon( 'trash.png' ),
                            'Clear', self.__clear )

        self.__textEdit.setContextMenuPolicy( Qt.CustomContextMenu )
        self.__textEdit.customContextMenuRequested.connect(
                                                self.__handleShowContextMenu )
        self.__textEdit.copyAvailable.connect( self.__onCopyAvailable )

        self.__updateToolbarButtons()
        return

    def __createLayout( self, parent ):
        " Helper to create the viewer layout "

        # __textEdit list area
        self.__textEdit = QPlainTextEdit( parent )
        self.__textEdit.setLineWrapMode( QPlainTextEdit.NoWrap )
        self.__textEdit.setFont( QFont( GlobalData().skin.baseMonoFontFace ) )
        self.__textEdit.setReadOnly( True )

        # Default font size is good enough for most of the systems.
        # 12.0 might be good only in case of the XServer on PC (Xming).
        # self.__textEdit.setFontPointSize( 12.0 )

        # Buttons
        self.__selectAllButton = QAction(
            PixmapCache().getIcon( 'selectall.png' ),
            'Select all', self )
        self.__selectAllButton.triggered.connect(self.__textEdit.selectAll )
        self.__copyButton = QAction(
            PixmapCache().getIcon( 'copytoclipboard.png' ),
            'Copy to clipboard', self )
        self.__copyButton.triggered.connect( self.__textEdit.copy )
        spacer = QWidget()
        spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.__clearButton = QAction(
            PixmapCache().getIcon( 'trash.png' ),
            'Clear all', self )
        self.__clearButton.triggered.connect( self.__clear )

        # Toolbar
        toolbar = QToolBar()
        toolbar.setOrientation( Qt.Vertical )
        toolbar.setMovable( False )
        toolbar.setAllowedAreas( Qt.LeftToolBarArea )
        toolbar.setIconSize( QSize( 16, 16 ) )
        toolbar.setFixedWidth( 28 )
        toolbar.setContentsMargins( 0, 0, 0, 0 )
        toolbar.addAction( self.__selectAllButton )
        toolbar.addAction( self.__copyButton )
        toolbar.addWidget( spacer )
        toolbar.addAction( self.__clearButton )

        self.__header = QLabel( "Signature: none" )
        self.__header.setFrameStyle( QFrame.StyledPanel )
        self.__header.setSizePolicy( QSizePolicy.Ignored, QSizePolicy.Fixed )
        self.__header.setAutoFillBackground( True )
        headerPalette = self.__header.palette()
        headerBackground = headerPalette.color( QPalette.Background )
        headerBackground.setRgb( min( headerBackground.red() + 30, 255 ),
                                 min( headerBackground.green() + 30, 255 ),
                                 min( headerBackground.blue() + 30, 255 ) )
        headerPalette.setColor( QPalette.Background, headerBackground )
        self.__header.setPalette( headerPalette )
        verticalLayout = QVBoxLayout()
        verticalLayout.setContentsMargins( 2, 2, 2, 2 )
        verticalLayout.setSpacing( 2 )
        verticalLayout.addWidget( self.__header )
        verticalLayout.addWidget( self.__textEdit )

        # layout
        layout = QHBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.setSpacing( 0 )
        layout.addWidget( toolbar )
        layout.addLayout( verticalLayout )

        self.setLayout( layout )
        return

    def __handleShowContextMenu( self, coord ):
        """ Show the context menu """

        self.__selectAllMenuItem.setEnabled( not self.__isEmpty )
        self.__copyMenuItem.setEnabled( self.__copyAvailable )
        self.__clearMenuItem.setEnabled( not self.__isEmpty )

        self.__menu.popup( QCursor.pos() )
        return

    def __calltipDisplayable( self, calltip ):
        " True if calltip is displayable "
        if calltip is None:
            return False
        if calltip.strip() == "":
            return False
        return True

    def __docstringDisplayable( self, docstring ):
        " True if docstring is displayable "
        if docstring is None:
            return False
        if isinstance( docstring, dict ):
            if docstring[ "docstring" ].strip() == "":
                return False
            return True
        if docstring.strip() == "":
            return False
        return True

    def display( self, calltip, docstring ):
        " Displays the given help information "

        calltipDisplayable = self.__calltipDisplayable( calltip )
        docstringDisplayable = self.__docstringDisplayable( docstring )
        self.__isEmpty = True
        if calltipDisplayable or docstringDisplayable:
            self.__isEmpty = False

        if calltipDisplayable:
            if '\n' in calltip:
                calltip = calltip.split( '\n' )[ 0 ]
            self.__header.setText( "Signature: " + calltip.strip() )
        else:
            self.__header.setText( "Signature: n/a" )

        self.__textEdit.clear()
        if docstringDisplayable:
            if isinstance( docstring, dict ):
                docstring = docstring[ "docstring" ]
            self.__textEdit.insertPlainText( docstring )

        self.__updateToolbarButtons()
        QApplication.processEvents()
        return

    def __updateToolbarButtons( self ):
        " Contextually updates toolbar buttons "

        self.__selectAllButton.setEnabled( not self.__isEmpty )
        self.__copyButton.setEnabled( self.__copyAvailable )
        self.__clearButton.setEnabled( not self.__isEmpty )
        return

    def __clear( self ):
        " Triggers when the clear function is selected "
        self.__isEmpty = True
        self.__copyAvailable = False
        self.__header.setText( "Signature: none" )
        self.__textEdit.clear()
        self.__updateToolbarButtons()
        return

    def __onCopyAvailable( self, isAvailable ):
        " Triggers on the copyAvailable signal "
        self.__copyAvailable = isAvailable
        self.__updateToolbarButtons()
        return

