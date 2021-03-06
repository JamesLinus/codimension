# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2015  Sergey Satskiy <sergey.satskiy@gmail.com>
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

" Auxiliary items on a canvas which do not derive from CellElement "

from sys import maxint
from PyQt4.QtCore import Qt
from PyQt4.QtGui import ( QPen, QBrush, QGraphicsRectItem, QGraphicsPathItem,
                          QPainterPath, QGraphicsSimpleTextItem )
from PyQt4.QtSvg import QGraphicsSvgItem
import os.path




class SVGItem( QGraphicsSvgItem ):
    " Wrapper for an SVG items on the control flow "

    def __init__( self, fName, ref ):
        self.__fName = fName
        QGraphicsSvgItem.__init__( self, self.__getPath( fName ) )
        self.__scale = 0
        self.ref = ref
        return

    def __getPath( self, fName ):
        " Tries to resolve the given file name "
        try:
            from utils.pixmapcache import PixmapCache
            path = PixmapCache().getSearchPath() + fName
            if os.path.exists( path ):
                return path
        except:
            pass

        if os.path.exists( fName ):
            return fName
        return ""

    def setHeight( self, height ):
        " Scales the svg item to the required height "
        rectHeight = float( self.boundingRect().height() )
        if rectHeight != 0.0:
            self.__scale = float( height ) / rectHeight
            self.setScale( self.__scale )
        return

    def setWidth( self, width ):
        " Scales the svg item to the required width "
        rectWidth = float( self.boundingRect().width() )
        if rectWidth != 0.0:
            self.__scale = float( width ) / rectWidth
            self.setScale( self.__scale )
        return

    def height( self ):
        return self.boundingRect().height() * self.__scale

    def width( self ):
        return self.boundingRect().width() * self.__scale

    def getSelectTooltip( self ):
        return "SVG item for " + self.__fName

    def isProxyItem( self ):
        return True

    def getProxiedItem( self ):
        return self.ref

    def isComment( self ):
        return False


class CMLLabel( SVGItem ):
    " Represents the CML label for an item "

    def __init__( self, ref = None ):
        SVGItem.__init__( self, "cmllabel.svgz", ref )
        self.setWidth( 6 )
        self.setToolTip( "CML hint is used" )
        return


class BadgeItem( QGraphicsRectItem ):
    " Serves the scope badges "

    def __init__( self, ref, text ):
        QGraphicsRectItem.__init__( self )
        self.ref = ref
        self.__text = text

        self.__textRect = ref.canvas.settings.badgeFontMetrics.boundingRect(
                                                0, 0,  maxint, maxint, 0, text )
        self.__hSpacing = 2
        self.__vSpacing = 1
        self.__radius = 2

        self.__width = self.__textRect.width() + 2 * self.__hSpacing
        self.__height = self.__textRect.height() + 2 * self.__vSpacing

        self.__bgColor = ref.canvas.settings.badgeBGColor
        self.__fgColor = ref.canvas.settings.badgeFGColor
        self.__frameColor = ref.canvas.settings.badgeLineColor
        self.__font = ref.canvas.settings.badgeFont
        self.__needRect = True
        return

    def setBGColor( self, bgColor ):
        self.__bgColor = bgColor
    def setFGColor( self, fgColor ):
        self.__fgColor = fgColor
    def setFrameColor( self, frameColor ):
        self.__frameColor = framecolor
    def setNeedRectangle( self, value ):
        self.__needRect = value
    def setFont( self, font ):
        self.__font = font
    def width( self ):
        return self.__width
    def height( self ):
        return self.__height
    def text( self ):
        return self.__text
    def moveTo( self, x, y ):
        # This is a mistery. I do not understand why I need to divide by 2.0
        # however this works. I tried various combinations of initialization,
        # setting the position and mapping. Nothing works but ../2.0. Sick!
        self.setPos( float(x)/2.0, float(y)/2.0 )
        self.setRect( float(x)/2.0, float(y)/2.0, self.__width, self.__height )
    def withinHeader( self ):
        if self.ref.kind in [ self.ref.ELSE_SCOPE,
                              self.ref.FINALLY_SCOPE,
                              self.ref.TRY_SCOPE ]:
            return True
        if self.ref.kind == self.ref.EXCEPT_SCOPE:
            return self.ref.ref.clause is None
        return False

    def paint( self, painter, option, widget ):
        " Paints the scope item "
        s = self.ref.canvas.settings

        if self.__needRect:
            pen = QPen( self.__frameColor )
            pen.setWidth( s.badgeLineWidth )
            painter.setPen( pen )
            brush = QBrush( self.__bgColor )
            painter.setBrush( brush )
            painter.drawRoundedRect( self.x(), self.y(),
                                     self.__width, self.__height,
                                     self.__radius, self.__radius )

        pen = QPen( self.__fgColor )
        painter.setPen( pen )
        painter.setFont( self.__font )
        painter.drawText( self.x() + self.__hSpacing, self.y() + self.__vSpacing,
                          self.__textRect.width(),
                          self.__textRect.height(),
                          Qt.AlignLeft, self.__text )
        return

    def getSelectTooltip( self ):
        return "Badge item '" + self.__text + "'"

    def isProxyItem( self ):
        return True

    def getProxiedItem( self ):
        return self.ref

    def isComment( self ):
        return False


class Connector( QGraphicsPathItem ):

    def __init__( self, settings, x1, y1, x2, y2 ):
        QGraphicsPathItem.__init__( self )
        self.__settings = settings

        path = QPainterPath()
        path.moveTo( x1, y1 )
        path.lineTo( x2, y2 )
        self.setPath( path )

        self.penStyle = None
        self.penColor = None
        self.penWidth = None
        return

    def paint( self, painter, option, widget ):
        color = self.__settings.lineColor
        if self.penColor:
            color = self.penColor
        width = self.__settings.lineWidth
        if self.penWidth:
            width = self.penWidth

        pen = QPen( color )
        pen.setWidth( width )
        pen.setCapStyle( Qt.FlatCap )
        pen.setJoinStyle( Qt.RoundJoin )
        if self.penStyle:
            pen.setStyle( self.penStyle )
        self.setPen( pen )
        QGraphicsPathItem.paint( self, painter, option, widget )
        return

    def getSelectTooltip( self ):
        return "Connector item"

    def isProxyItem( self ):
        return True

    def getProxiedItem( self ):
        return None

    def isComment( self ):
        return False


class Text( QGraphicsSimpleTextItem ):

    def __init__( self, settings, text ):
        QGraphicsSimpleTextItem.__init__( self )
        self.__settings = settings

        self.setFont( settings.badgeFont )
        self.setText( text )

        self.color = None
        return

    def paint( self, painter, option, widget ):
        color = self.__settings.lineColor
        if self.color:
            color = self.color

        self.setBrush( QBrush( color ) )
        QGraphicsSimpleTextItem.paint( self, painter, option, widget )
        return

    def getSelectTooltip( self ):
        return "Text item"

    def isProxyItem( self ):
        return True

    def getProxiedItem( self ):
        return None

    def isComment( self ):
        return False


