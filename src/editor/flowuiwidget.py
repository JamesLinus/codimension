#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Control flow UI widget "

import os.path
import logging
from PyQt4.QtCore import Qt, QSize, QTimer, SIGNAL, QDir, QUrl, QSizeF, QRectF, QPoint
from PyQt4.QtGui import ( QToolBar, QWidget, QGraphicsView, QPainter,
                          QApplication, QGraphicsScene, QHBoxLayout,
                          QLabel, QTransform, QVBoxLayout, QFrame,
                          QSizePolicy, QAction, QFileDialog, QDialog,
                          QMenu, QToolButton, QImage, QMessageBox, QPrinter )
from PyQt4.QtSvg import QSvgGenerator
from cdmcf import getControlFlowFromMemory
from flowui.vcanvas import VirtualCanvas
from flowui.cflowsettings import getDefaultCflowSettings
from flowui.cml import CMLVersion
from utils.pixmapcache import getPixmap, getIcon
from utils.globals import GlobalData
from utils.fileutils import Python3FileType, PythonFileType
from utils.settings import Settings
from ui.fitlabel import FitLabel
from flowuicontextmenus import CFSceneContextMenuMixin
from flowuimouse import CFSceneMouseMixin
from flowuikeyboard import CFSceneKeyboardMixin


IDLE_TIMEOUT = 1500


class CFGraphicsScene( QGraphicsScene,
                       CFSceneContextMenuMixin,
                       CFSceneMouseMixin,
                       CFSceneKeyboardMixin ):
    """ Reimplemented graphics scene """

    def __init__( self, navBar, parent = None ):
        QGraphicsScene.__init__( self, parent )
        CFSceneContextMenuMixin.__init__( self )
        CFSceneMouseMixin.__init__( self )
        CFSceneKeyboardMixin.__init__( self )
        self.__navBar = navBar
        self.selectionChanged.connect( self.selChanged )
        return

    def selChanged( self ):
        items = self.selectedItems()
        count = len( items )
        if count:
            tooltip = []
            for item in items:
                if hasattr( item, "getSelectTooltip" ):
                    tooltip.append( item.getSelectTooltip() )
                else:
                    tooltip.append( str( type( item ) ) )
            self.__navBar.setSelectionLabel( count, "\n".join( tooltip ) )
        else:
            self.__navBar.setSelectionLabel( 0, None )
        return



class CFGraphicsView( QGraphicsView ):
    """ Central widget """

    def __init__( self, parent = None ):
        super( CFGraphicsView, self ).__init__( parent )

        self.__currentFactor = 1.0
        self.setRenderHint( QPainter.Antialiasing )
        self.setRenderHint( QPainter.TextAntialiasing )
        Settings().flowScaleChanged.connect( self.__scaleChanged )
        return

    def wheelEvent( self, event ):
        """ Mouse wheel event """
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            factor = 1.41 ** ( -event.delta() / 240.0 )
            self.__currentFactor *= factor
            self.setTransform( QTransform.fromScale( self.__currentFactor,
                                                     self.__currentFactor ) )
            Settings().flowScale = self.__currentFactor
        else:
            QGraphicsView.wheelEvent( self, event )
        return

    def zoomTo( self, scale ):
        " Zooms to the specific factor "
        self.__currentFactor = scale
        self.setTransform( QTransform.fromScale( self.__currentFactor,
                                                 self.__currentFactor ) )
        return

    def zoomIn( self ):
        ' Mouse event delta is typically 120 '
        factor = 1.41 ** ( 120.0 / 240.0 )
        self.zoomTo( self.__currentFactor * factor  )
        Settings().flowScale = self.__currentFactor
        return

    def zoomOut( self ):
        ' Mouse event delta is typically 120 '
        factor = 1.41 ** ( -120.0 / 240.0 )
        self.zoomTo( self.__currentFactor * factor  )
        Settings().flowScale = self.__currentFactor
        return

    def __scaleChanged( self ):
        " When another window made a change "
        newScale = Settings().flowScale
        if newScale != self.__currentFactor:
            self.zoomTo( newScale )
        return

    def getVisibleRect( self ):
        " Provides the visible rectangle "
        A = self.mapToScene( QPoint( 0, 0 ) )
        B = self.mapToScene( QPoint( self.viewport().width(),
                                     self.viewport().height() ) )
        return QRectF( A, B )

    def scrollTo( self, item ):
        " Scrolls the view to the item "
        if item is None:
            return

        visibleRect = self.getVisibleRect()
        itemRect = item.boundingRect()
        if visibleRect.contains( itemRect ):
            # The item is fully visible
            return

        # The item is fully visible vertically
        if itemRect.topLeft().y() >= visibleRect.topLeft().y() and \
           itemRect.bottomLeft().y() <= visibleRect.bottomLeft().y():
            self.__hScrollToItem( item )
            return

        # The item top left is visible
        if visibleRect.contains( itemRect.topLeft() ):
            # So far scroll the view vertically anyway
            val = ( float( itemRect.topLeft().y() - 15.0 ) ) * self.__currentFactor
            self.verticalScrollBar().setValue( val )
            self.__hScrollToItem( item )
            return

        # Here: the top left is not visible, so the vertical scrolling is
        # required
        val = ( float( itemRect.topLeft().y() - 15.0 ) ) * self.__currentFactor
        self.verticalScrollBar().setValue( val )
        self.__hScrollToItem( item )
        return


    def __hScrollToItem( self, item ):
        " Sets the horizontal scrolling for the item "

        if item is None:
            return

        # There are a few cases here:
        # - the item does not fit the screen width
        # - the item fits the screen width and would be visible if the
        #   scroll is set to 0
        # - the item fits the screen width and would not be visible if the
        #   scroll is set to 0

        visibleRect = self.getVisibleRect()
        itemRect = item.boundingRect()

        if itemRect.width() > visibleRect.width():
            # Does not fit the screen
            val = ( float( itemRect.topLeft().x() ) - 15.0 ) * self.__currentFactor
            self.horizontalScrollBar().setValue( val )
        else:
            if itemRect.topRight().x() < visibleRect.width():
                # Fits the screen if the scroll is 0
                self.horizontalScrollBar().setValue( 0 )
            else:
                val = ( float( itemRect.topLeft().x() ) - 15.0 ) * self.__currentFactor
                self.horizontalScrollBar().setValue( val )
        return



class ControlFlowNavigationBar( QFrame ):
    " Navigation bar at the top of the flow UI widget "

    STATE_OK_UTD = 0        # Parsed OK, control flow up to date
    STATE_OK_CHN = 1        # Parsed OK, control flow changed
    STATE_BROKEN_UTD = 2    # Parsed with errors, control flow up to date
    STATE_BROKEN_CHN = 3    # Parsed with errors, control flow changed
    STATE_UNKNOWN = 4

    def __init__( self, parent ):
        QFrame.__init__( self, parent )
        self.__infoIcon = None
        self.__warningsIcon = None
        self.__layout = None
        self.__pathLabel = None
        self.__createLayout()
        self.__currentIconState = self.STATE_UNKNOWN
        return

    def __createLayout( self ):
        " Creates the layout "
        self.setFixedHeight( 24 )
        self.__layout = QHBoxLayout( self )
        self.__layout.setMargin( 0 )
        self.__layout.setContentsMargins( 0, 0, 0, 0 )

        # Create info icon
        self.__infoIcon = QLabel()
        self.__infoIcon.setPixmap( getPixmap( 'cfunknown.png' ) )
        self.__layout.addWidget( self.__infoIcon )

        self.__warningsIcon = QLabel()
        self.__warningsIcon.setPixmap( getPixmap( 'cfwarning.png' ) )
        self.__layout.addWidget( self.__warningsIcon )

        self.clearWarnings()

        # Create the path label
        self.__pathLabel = QLabel( self )
        self.__pathLabel.setTextFormat( Qt.PlainText )
        self.__pathLabel.setAlignment( Qt.AlignLeft )
        self.__pathLabel.setWordWrap( False )
        self.__pathLabel.setFrameStyle( QFrame.StyledPanel )
        self.__pathLabel.setTextInteractionFlags( Qt.NoTextInteraction )
        self.__pathLabel.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Fixed )
        self.__layout.addWidget( self.__pathLabel )

        self.__spacer = QWidget()
        self.__spacer.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Fixed )
        self.__spacer.setMinimumWidth( 0 )
        self.__layout.addWidget( self.__spacer )

        # Create the selection label
        self.__selectionLabel = QLabel( self )
        self.__selectionLabel.setTextFormat( Qt.PlainText )
        self.__selectionLabel.setAlignment( Qt.AlignCenter )
        self.__selectionLabel.setWordWrap( False )
        self.__selectionLabel.setFrameStyle( QFrame.StyledPanel )
        self.__selectionLabel.setTextInteractionFlags( Qt.NoTextInteraction )
        self.__selectionLabel.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        self.__selectionLabel.setMinimumWidth( 40 )
        self.__layout.addWidget( self.__selectionLabel )
        self.setSelectionLabel( 0, None )
        return

    def clearWarnings( self ):
        self.__warningsIcon.setVisible( False )
        self.__warningsIcon.setToolTip( "" )
        return

    def setWarnings( self, warnings ):
        self.__warningsIcon.setToolTip( "Control flow parser warnings:\n" +
                                        "\n".join( warnings ) )
        self.__warningsIcon.setVisible( True )
        return

    def clearErrors( self ):
        self.__infoIcon.setToolTip( "" )
        return

    def setErrors( self, errors ):
        self.__infoIcon.setToolTip( "Control flow parser errors:\n" +
                                    "\n".join( errors ) )
        return

    def updateInfoIcon( self, state ):
        " Updates the information icon "
        if state == self.__currentIconState:
            return

        if state == self.STATE_OK_UTD:
            self.__infoIcon.setPixmap( getPixmap( 'cfokutd.png' ) )
            self.__infoIcon.setToolTip( "Control flow is up to date" )
            self.__currentIconState = self.STATE_OK_UTD
        elif state == self.STATE_OK_CHN:
            self.__infoIcon.setPixmap( getPixmap( 'cfokchn.png' ) )
            self.__infoIcon.setToolTip( "Control flow is not up to date; will be updated on idle" )
            self.__currentIconState = self.STATE_OK_CHN
        elif state == self.STATE_BROKEN_UTD:
            self.__infoIcon.setPixmap( getPixmap( 'cfbrokenutd.png' ) )
            self.__infoIcon.setToolTip( "Control flow might be invalid due to invalid python code" )
            self.__currentIconState = self.STATE_BROKEN_UTD
        elif state == self.STATE_BROKEN_CHN:
            self.__infoIcon.setPixmap( getPixmap( 'cfbrokenchn.png' ) )
            self.__infoIcon.setToolTip( "Control flow might be invalid; will be updated on idle" )
            self.__currentIconState = self.STATE_BROKEN_CHN
        else:
            # STATE_UNKNOWN
            self.__infoIcon.setPixmap( getPixmap( 'cfunknown.png' ) )
            self.__infoIcon.setToolTip( "Control flow state is unknown" )
            self.__currentIconState = self.STATE_UNKNOWN
        return

    def getCurrentState( self ):
        return self.__currentIconState

    def setPath( self, txt ):
        " Sets the path label content "
        self.__pathLabel.setText( txt )
        return

    def setPathVisible( self, on ):
        self.__pathLabel.setVisible( on )
        self.__spacer.setVisible( not on )
        return

    def setSelectionLabel( self, text, tooltip ):
        self.__selectionLabel.setText( str( text ) )
        if tooltip:
            self.__selectionLabel.setToolTip( "Selected items:\n" + str( tooltip ) )
        else:
            self.__selectionLabel.setToolTip( "Number of selected items" )
        return

    def resizeEvent( self, event ):
        " Editor has resized "
        QFrame.resizeEvent( self, event )
        return



class FlowUIWidget( QWidget ):
    " The widget which goes along with the text editor "

    def __init__( self, editor, parent ):
        QWidget.__init__( self, parent )

        # It is always not visible at the beginning because there is no
        # editor content at the start
        self.setVisible( False )

        self.__editor = editor
        self.__parentWidget = parent
        self.__connected = False
        self.__needPathUpdate = False

        self.cflowSettings = getDefaultCflowSettings( self )

        hLayout = QHBoxLayout()
        hLayout.setContentsMargins( 0, 0, 0, 0 )
        hLayout.setSpacing( 0 )

        vLayout = QVBoxLayout()
        vLayout.setContentsMargins( 0, 0, 0, 0 )
        vLayout.setSpacing( 0 )

        # Make pylint happy
        self.__toolbar = None
        self.__navBar = None
        self.__cf = None

        # Create the update timer
        self.__updateTimer = QTimer( self )
        self.__updateTimer.setSingleShot( True )
        self.__updateTimer.timeout.connect( self.process )

        vLayout.addWidget( self.__createNavigationBar() )
        vLayout.addWidget( self.__createGraphicsView() )

        hLayout.addLayout( vLayout )
        hLayout.addWidget( self.__createToolbar() )
        self.setLayout( hLayout )

        self.updateSettings()

        # Connect to the change file type signal
        mainWindow = GlobalData().mainWindow
        editorsManager = mainWindow.editorsManagerWidget.editorsManager
        self.connect( editorsManager, SIGNAL( 'fileTypeChanged' ),
                      self.__onFileTypeChanged )
        return

    def __createToolbar( self ):
        " Creates the toolbar "
        self.__toolbar = QToolBar( self )
        self.__toolbar.setOrientation( Qt.Vertical )
        self.__toolbar.setMovable( False )
        self.__toolbar.setAllowedAreas( Qt.RightToolBarArea )
        self.__toolbar.setIconSize( QSize( 16, 16 ) )
        self.__toolbar.setFixedWidth( 28 )
        self.__toolbar.setContentsMargins( 0, 0, 0, 0 )

        # Buttons
        saveAsMenu = QMenu( self )
        saveAsSVGAct = saveAsMenu.addAction( getIcon( 'filesvg.png' ),
                                             'Save as SVG...' )
        saveAsSVGAct.triggered.connect( self.onSaveAsSVG )

        saveAsPDFAct = saveAsMenu.addAction( getIcon( 'filepdf.png' ),
                                             'Save as PDF...' )
        saveAsPDFAct.triggered.connect( self.onSaveAsPDF )
        saveAsPNGAct = saveAsMenu.addAction( getIcon( 'filepixmap.png' ),
                                             'Save as PNG...' )
        saveAsPNGAct.triggered.connect( self.onSaveAsPNG )
        saveAsMenu.addSeparator()
        saveAsCopyToClipboardAct = saveAsMenu.addAction( getIcon( 'copymenu.png' ),
                                                         'Copy to clipboard' )
        saveAsCopyToClipboardAct.triggered.connect( self.copyToClipboard )


        self.__saveAsButton = QToolButton( self )
        self.__saveAsButton.setIcon( getIcon( 'saveasmenu.png' ) )
        self.__saveAsButton.setToolTip( 'Save as' )
        self.__saveAsButton.setPopupMode( QToolButton.InstantPopup )
        self.__saveAsButton.setMenu( saveAsMenu )
        self.__saveAsButton.setFocusPolicy( Qt.NoFocus )

        self.__toolbar.addWidget( self.__saveAsButton )
        return self.__toolbar

    def __createNavigationBar( self ):
        " Creates the navigation bar "
        self.__navBar = ControlFlowNavigationBar( self )
        return self.__navBar

    def __createGraphicsView( self ):
        """ Creates the graphics view """
        self.scene = CFGraphicsScene( self.__navBar, self )
        self.view = CFGraphicsView( self )
        self.view.setScene( self.scene )
        self.view.zoomTo( Settings().flowScale )
        return self.view

    def process( self ):
        """ Parses the content and displays the results """

        if not self.__connected:
            self.__connectEditorSignals()

        content = self.__editor.text()
        cf = getControlFlowFromMemory( content )
        if cf.errors:
            self.__navBar.updateInfoIcon( self.__navBar.STATE_BROKEN_UTD )
            errors = []
            for err in cf.errors:
                if err[ 0 ] == -1 and err[ 1 ] == -1:
                    errors.append( err[ 2 ] )
                elif err[ 1 ] == -1:
                    errors.append( "[" + str( err[0] ) + ":] " + err[ 2 ] )
                elif err[ 0 ] == -1:
                    errors.append( "[:" + str( err[1] ) + "] " + err[ 2 ] )
                else:
                    errors.append( "[" + str( err[0] ) + ":" + str( err[1] ) + "] " + err[ 2 ] )
            self.__navBar.setErrors( errors )
            return
        self.__cf = cf

        # Validate CML comments
        cmlWarnings = CMLVersion.validateCMLComments( self.__cf )
        if cmlWarnings:
            self.__cf.warnings += cmlWarnings

        # That will clear the error tooltip as well
        self.__navBar.updateInfoIcon( self.__navBar.STATE_OK_UTD )

        if self.__cf.warnings:
            warnings = []
            for warn in self.__cf.warnings:
                if warn[ 0 ] == -1 and warn[ 1 ] == -1:
                    warnings.append( warn[ 2 ] )
                elif warn[ 1 ] == -1:
                    warnings.append( "[" + str( warn[0] ) + ":] " + warn[ 2 ] )
                elif warn[ 0 ] == -1:
                    warnings.append( "[:" + str( warn[1] ) + "] " + warn[ 2 ] )
                else:
                    warnings.append( "[" + str( warn[0] ) + ":" + str( warn[1] ) + "] " + warn[ 2 ] )
            self.__navBar.setWarnings( warnings )
        else:
            self.__navBar.clearWarnings()

        self.scene.clear()
        try:
            # Top level canvas has no adress and no parent canvas
            canvas = VirtualCanvas( self.cflowSettings, None, None, None )
            canvas.layoutModule( self.__cf )
            canvas.setEditor( self.__editor )
            width, height = canvas.render()
            self.scene.setSceneRect( 0, 0, width, height )
            canvas.draw( self.scene, 0, 0 )
        except Exception, exc:
            logging.error( str( exc ) )
            raise
        return

    def __onFileTypeChanged( self, fileName, uuid, newFileType ):
        " Triggered when a buffer content type has changed "

        if self.__parentWidget.getUUID() != uuid:
            return

        if newFileType not in [ Python3FileType, PythonFileType ]:
            self.__disconnectEditorSignals()
            self.__updateTimer.stop()
            self.__cf = None
            self.setVisible( False )
            self.__navBar.updateInfoIcon( self.__navBar.STATE_UNKNOWN )
            return

        # Update the bar and show it
        self.setVisible( True )
        self.process()

        # The buffer type change event comes when the content is loaded first
        # time. So this is a good point to restore the position
        _, _, _, cflowHPos, cflowVPos = Settings().filePositions.getPosition( fileName )
        self.setScrollbarPositions( cflowHPos, cflowVPos )
        return

    def __connectEditorSignals( self ):
        " When it is a python file - connect to the editor signals "
        if not self.__connected:
            self.__editor.cursorPositionChanged.connect( self.__cursorPositionChanged )
            self.__editor.SCEN_CHANGE.connect( self.__onBufferChanged )
            self.__connected = True
        return

    def __disconnectEditorSignals( self ):
        " Disconnect the editor signals when the file is not a python one "
        if self.__connected:
            self.__editor.cursorPositionChanged.disconnect( self.__cursorPositionChanged )
            self.__editor.SCEN_CHANGE.disconnect( self.__onBufferChanged )
            self.__connected = False
        return

    def __cursorPositionChanged( self, line, pos ):
        " Cursor position changed "
        # The timer should be reset only in case if the redrawing was delayed
        if self.__updateTimer.isActive():
            self.__updateTimer.stop()
            self.__updateTimer.start( IDLE_TIMEOUT )
        return

    def __onBufferChanged( self ):
        " Triggered to update status icon and to restart the timer "
        self.__updateTimer.stop()
        if self.__navBar.getCurrentState() in [ self.__navBar.STATE_OK_UTD,
                                                self.__navBar.STATE_OK_CHN,
                                                self.__navBar.STATE_UNKNOWN ]:
            self.__navBar.updateInfoIcon( self.__navBar.STATE_OK_CHN )
        else:
            self.__navBar.updateInfoIcon( self.__navBar.STATE_BROKEN_CHN )
        self.__updateTimer.start( IDLE_TIMEOUT )
        return

    def updateNavigationToolbar( self, text ):
        " Updates the toolbar text "
        if self.__needPathUpdate:
            self.__navBar.setPath( text )
        return

    def updateSettings( self ):
        " Updates settings "
        s = Settings()
        self.__needPathUpdate = s.showCFNavigationBar
        self.__navBar.setPathVisible( self.__needPathUpdate )
        self.__navBar.setPath( "" )
        return

    def highlightAtAbsPos( self, absPos, line, pos ):
        """ Scrolls the view to the item closest to absPos and selects it.
            line and pos are 1-based """
        item, distance = self.scene.getNearestItem( absPos, line, pos )
        if item:
            self.scene.clearSelection()
            item.setSelected( True )
            self.view.scrollTo( item )
            self.setFocus()
        return

    def setFocus( self ):
        self.view.setFocus()
        return

    def __getDefaultSaveDir( self ):
        " Provides the default directory to save files to "
        project = GlobalData().project
        if project.isLoaded():
            return project.getProjectDir()
        return QDir.currentPath()

    def __selectFile( self, extension ):
        " Picks a file of a certain extension "
        dialog = QFileDialog( self, 'Save flowchart as' )
        dialog.setFileMode( QFileDialog.AnyFile )
        dialog.setLabelText( QFileDialog.Accept, "Save" )
        dialog.setNameFilter( extension.upper() + " files (*." +
                              extension.lower() + ")" )
        urls = []
        for dname in QDir.drives():
            urls.append( QUrl.fromLocalFile( dname.absoluteFilePath() ) )
        urls.append( QUrl.fromLocalFile( QDir.homePath() ) )
        project = GlobalData().project
        if project.isLoaded():
            urls.append( QUrl.fromLocalFile( project.getProjectDir() ) )
        dialog.setSidebarUrls( urls )

        suggestedFName = self.__parentWidget.getFileName()
        if '.' in suggestedFName:
            dotIndex = suggestedFName.rindex( '.' )
            suggestedFName = suggestedFName[ : dotIndex ]

        dialog.setDirectory( self.__getDefaultSaveDir() )
        dialog.selectFile( suggestedFName + "." + extension.lower() )
        dialog.setOption( QFileDialog.DontConfirmOverwrite, False )
        if dialog.exec_() != QDialog.Accepted:
            return None

        fileNames = dialog.selectedFiles()
        fileName = os.path.abspath( str( fileNames[0] ) )
        if os.path.isdir( fileName ):
            logging.error( "A file must be selected" )
            return None

        if "." not in fileName:
            fileName += "." + extension.lower()

        # Check permissions to write into the file or to a directory
        if os.path.exists( fileName ):
            # Check write permissions for the file
            if not os.access( fileName, os.W_OK ):
                logging.error( "There is no write permissions for " + fileName )
                return None
        else:
            # Check write permissions to the directory
            dirName = os.path.dirname( fileName )
            if not os.access( dirName, os.W_OK ):
                logging.error( "There is no write permissions for the "
                               "directory " + dirName )
                return None

        if os.path.exists( fileName ):
            res = QMessageBox.warning( self, "Save flowchart as",
                    "<p>The file <b>" + fileName + "</b> already exists.</p>",
                    QMessageBox.StandardButtons( QMessageBox.Abort |
                                                 QMessageBox.Save ),
                    QMessageBox.Abort )
            if res == QMessageBox.Abort or res == QMessageBox.Cancel:
                return None

        # All prerequisites are checked, return a file name
        return fileName


    def onSaveAsSVG( self ):
        " Triggered on the 'Save as SVG' button "
        fileName = self.__selectFile( "svg" )
        if fileName is None:
            return False

        try:
            self.__saveAsSVG( fileName )
        except Exception, excpt:
            logging.error( str( excpt ) )
            return False
        return True

    def __saveAsSVG( self, fileName ):
        " Saves the flowchart as an SVG file "
        generator = QSvgGenerator()
        generator.setFileName( fileName )
        generator.setSize( QSize( self.scene.width(), self.scene.height() ) )
        painter = QPainter( generator )
        self.scene.render( painter )
        painter.end()
        return

    def onSaveAsPDF( self ):
        " Triggered on the 'Save as PDF' button "
        fileName = self.__selectFile( "pdf" )
        if fileName is None:
            return False

        try:
            self.__saveAsPDF( fileName )
        except Exception, excpt:
            logging.error( str( excpt ) )
            return False
        return True

    def __saveAsPDF( self, fileName ):
        " Saves the flowchart as an PDF file "
        printer = QPrinter()
        printer.setOutputFormat( QPrinter.PdfFormat )
        printer.setPaperSize( QSizeF( self.scene.width(),
                                      self.scene.height() ), QPrinter.Point )
        printer.setFullPage( True )
        printer.setOutputFileName( fileName )

        painter = QPainter( printer )
        self.scene.render( painter )
        painter.end()
        return

    def onSaveAsPNG( self ):
        " Triggered on the 'Save as PNG' button "
        fileName = self.__selectFile( "png" )
        if fileName is None:
            return False

        try:
            self.__saveAsPNG( fileName )
        except Exception, excpt:
            logging.error( str( excpt ) )
            return False
        return True

    def __getPNG( self ):
        " Renders the scene as PNG "
        image = QImage( self.scene.width(), self.scene.height(),
                        QImage.Format_ARGB32_Premultiplied )
        painter = QPainter( image )
        # It seems that the better results are without antialiasing
        # painter.setRenderHint( QPainter.Antialiasing )
        self.scene.render( painter )
        painter.end()
        return image

    def __saveAsPNG( self, fileName ):
        " Saves the flowchart as an PNG file "
        image = self.__getPNG()
        image.save( fileName, "PNG" )
        return

    def copyToClipboard( self ):
        " Copies the rendered scene to the clipboard as an image "
        image = self.__getPNG()
        clip = QApplication.clipboard()
        clip.setImage( image )
        return

    def getScrollbarPositions( self ):
        " Provides the scrollbar positions "
        hScrollBar = self.view.horizontalScrollBar()
        vScrollBar = self.view.verticalScrollBar()
        return hScrollBar.value(), vScrollBar.value()

    def setScrollbarPositions( self, hPos, vPos ):
        " Sets the scrollbar positions for the view "
        self.view.horizontalScrollBar().setValue( hPos )
        self.view.verticalScrollBar().setValue( vPos )
        return


