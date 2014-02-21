#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy sergey.satskiy@gmail.com
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

" Redirected IO console messages mplementation "

from datetime import datetime
from utils.settings import Settings



def getNowTimestamp():
    " Provides the now() timestamp as a string "
    timestamp = datetime.now()
    millisecond = str( int( round( timestamp.microsecond / 1000.0 ) ) )
    while len( millisecond ) != 3:
        millisecond = "0" + millisecond
    return timestamp.strftime( "%H:%M:%S." ) + millisecond



class IOConsoleMsg( object ):
    " Holds a single message "

    __slots__ = [ "msgType", "msgText", "timestamp" ]

    IDE_MESSAGE = 0
    STDOUT_MESSAGE = 1
    STDERR_MESSAGE = 2
    STDIN_MESSAGE = 3

    def __init__( self, msgType, msgText ):
        self.msgType = msgType
        self.msgText = msgText
        self.timestamp = datetime.now()
        return

    def getTimestamp( self ):
        " Provides the timestamp as a string "
        millisecond = str( int( round( self.timestamp.microsecond / 1000.0 ) ) )
        while len( millisecond ) != 3:
            millisecond = "0" + millisecond
        return self.timestamp.strftime( "%H:%M:%S." ) + millisecond


class IOConsoleMessages:
    " Holds a list of messages "

    def __init__( self ):
        self.msgs = []
        self.size = 0
        return

    def append( self, msg ):
        """ Appends the given message to the list.
            Returns True if there was trimming """
        self.msgs.append( msg )
        self.size += 1

        if self.size <= Settings().ioconsolemaxmsgs:
            return False

        removeCount = Settings().ioconsoledelchunk
        self.msgs = self.msgs[ removeCount : ]
        self.size -= removeCount
        return True

    def clear( self ):
        " Clears all the messages "
        self.msgs = []
        self.size = 0
        return
