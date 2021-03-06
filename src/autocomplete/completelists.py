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
# $Id$
#

" Utilities to build completeion lists to suggest to the user "


from cdmbriefparser import ( getBriefModuleInfoFromMemory,
                             getBriefModuleInfoFromFile )
from bufferutils import ( getEditorTags, isRemarkLine, isStringLiteral,
                          isOnSomeImport )
from utils.globals import GlobalData
from utils.settings import Settings
from listmodules import getSysModules, getModules
import os, imp
from rope.base.libutils import path_to_resource
from rope.contrib.codeassist import code_assist, get_calltip, get_doc
from rope.contrib.findit import find_definition, find_occurrences
from rope.base import worder

__systemwideModules = {}
__systemwideInitialized = False


def buildSystemWideModulesList():
    " Builds a map for the system wide modules "
    global __systemwideModules
    global __systemwideInitialized

    if not __systemwideInitialized:
        __systemwideModules = getSysModules()
        __systemwideInitialized = True
    return


def __getModuleNames( fileName ):
    " Provides a list of modules available for completion "
    buildSystemWideModulesList()

    # Additional paths:
    # if project is loaded: the project import dirs
    # if file is an absolute path: modules for the basedir
    specificModules = getProjectSpecificModules( fileName )
    specificModules.update( __systemwideModules )
    return set( specificModules.keys() )


def getSystemWideModules():
    " provides a list of system wide modules "
    buildSystemWideModulesList()
    return __systemwideModules


def getProjectSpecificModules( path = "", onlySpecified = False ):
    " Provides a dictionary of the project specific modules "
    specificModules = {}
    importDirs = []

    if not onlySpecified:
        importDirs = GlobalData().getProjectImportDirs()
        for importPath in importDirs:
            specificModules.update( getModules( importPath ) )

        projectFile = GlobalData().project.fileName
        if projectFile != "":
            basedir = os.path.dirname( projectFile )
            if basedir not in importDirs:
                importDirs.append( basedir )
                specificModules.update( getModules( basedir ) )

    if path and os.path.isabs( path ):
        path = os.path.normpath( path )
        basedir = ""
        if os.path.isfile( path ):
            basedir = os.path.dirname( path )
        elif os.path.isdir( path ):
            basedir = path

        if basedir and basedir not in importDirs:
            specificModules.update( getModules( basedir ) )

    return specificModules


def __isBinaryModule( moduleName ):
    " Returns True if it is a binary library "
    for suffix in imp.get_suffixes():
        if suffix[ 2 ] == imp.C_EXTENSION:
            if moduleName.endswith( suffix[ 0 ] ):
                return suffix
    return None


def __getParsedModuleNames( info ):
    " Provides the names which could be imported from a module "
    result = set()
    for item in info.globals:
        result.add( item.name )
    for item in info.functions:
        result.add( item.name )
    for item in info.classes:
        result.add( item.name )
    return result


def __getImportedObjects( moduleName, fileName ):
    " Provides a list of objects to be imported from "
    buildSystemWideModulesList()

    modulePath = None
    moduleName = str( moduleName )
    if moduleName in __systemwideModules:
        modulePath = __systemwideModules[ moduleName ]
        if modulePath is None or moduleName in Settings().dirSafeModules:
            # it could be a built-in module
            return getImportNames( moduleName )
    else:
        # Not a system wide, try search in the project
        # or current directories
        if moduleName.startswith( "." ):
            # That's a relative import
            if not fileName:
                # File name must be known for a relative import
                return set()
            dotCount = 0
            while moduleName.startswith( "." ):
                dotCount += 1
                moduleName = moduleName[ 1: ]
            # Strip as many paths as dots instruct
            baseDir = os.path.dirname( fileName )
            while dotCount > 1:
                baseDir = os.path.dirname( baseDir )
                dotCount -= 1
            specificModules = getProjectSpecificModules( baseDir, True )
        else:
            specificModules = getProjectSpecificModules( fileName )
        if moduleName in specificModules:
            modulePath = specificModules[ moduleName ]

    if modulePath is None:
        return set()

    binarySuffix = __isBinaryModule( modulePath )
    if binarySuffix is not None:
        try:
            modName = os.path.basename( modulePath )
            modObj = imp.load_module( modName, None, modulePath, binarySuffix )
            return set( dir( modObj ) )
        except:
            # Failed to load a binary module
            return set()

    # It's not a binary module, so parse it and make a list of objects.
    # Check first if the module is loaded into the editor
    mainWindow = GlobalData().mainWindow
    editorsManager = mainWindow.editorsManagerWidget.editorsManager
    widget = editorsManager.getWidgetForFileName( modulePath )
    if widget is None:
        # Not loaded, so parse it from a file
        info = getBriefModuleInfoFromFile( modulePath )
    else:
        # Parse it from memory because it could be changed
        editor = widget.getEditor()
        info = getBriefModuleInfoFromMemory( editor.text() )

    return __getParsedModuleNames( info )



# See: http://stackoverflow.com/questions/211100/
#             pythons-import-doesnt-work-as-expected
def importModule( modName, parentModule = None ):
    """Attempts to import the supplied string as a module.
       Returns the module that was imported."""

    mods = modName.split( '.' )
    childModuleString = '.'.join( mods[ 1: ] )
    if parentModule is None:
        if len( mods ) > 1:
            # First time this function is called; import the module
            # __import__() will only return the top level module
            return importModule( childModuleString, __import__( modName ) )
        else:
            return __import__( modName )
    else:
        mod = getattr( parentModule, mods[ 0 ] )
        if len( mods ) > 1:
            # We're not yet at the intended module; drill down
            return importModule( childModuleString, mod )
        else:
            return mod


def getImportNames( importName ):
    """ Builds a list of names for an import """
    try:
        mod = importModule( importName )

        result = set()
        for item in dir( mod ):
            result.add( item )
        return result
    except:
        return set()


def _addClassPrivateNames( classInfo, names ):
    " Adds private names to the given list "
    for item in classInfo.classAttributes:
        if item.name.startswith( '__' ) and not item.name.endswith( '__' ):
            names.add( item.name )
    for item in classInfo.instanceAttributes:
        if item.name.startswith( '__' ) and not item.name.endswith( '__' ):
            names.add( item.name )
    for item in classInfo.functions:
        if item.name.startswith( '__' ) and not item.name.endswith( '__' ):
            names.add( item.name )
    for item in classInfo.classes:
        if item.name.startswith( '__' ) and not item.name.endswith( '__' ):
            names.add( item.name )
    return


def _getRopeCompletion( fileName, text, editor, prefix ):
    " Provides the rope library idea of how to complete "
    try:
        GlobalData().validateRopeProject()
        ropeProject = GlobalData().getRopeProject( fileName )
        position = editor.currentPosition() - len( prefix )

        if os.path.isabs( fileName ):
            resource = path_to_resource( ropeProject, fileName )
            proposals = code_assist( ropeProject, text, position,
                                     resource, None, maxfixes = 7 )
        else:
            # The file does not exist
            proposals = code_assist( ropeProject, text, position,
                                     None, None, maxfixes = 7 )
        return proposals, True
    except:
        # Rope may throw exceptions e.g. in case of syntax errors
        return [], False


def getCalltipAndDoc( fileName, editor, position = None, tryQt = False ):
    " Provides a calltip and docstring "
    try:
        GlobalData().validateRopeProject()
        ropeProject = GlobalData().getRopeProject( fileName )
        if position is None:
            position = editor.currentPosition()
        text = editor.text()

        calltip = None
        docstring = None

        resource = None
        if os.path.isabs( fileName ):
            resource = path_to_resource( ropeProject, fileName )

        calltip = get_calltip( ropeProject, text, position, resource,
                               ignore_unknown = False,
                               remove_self = True, maxfixes = 7 )
        if calltip is not None:
            calltip = calltip.strip()
            while '..' in calltip:
                calltip = calltip.replace( '..', '.' )
            if '(.)' in calltip:
                calltip = calltip.replace( '(.)', '(...)' )
            calltip = calltip.replace( '.__init__', '' )
            try:
                docstring = get_doc( ropeProject, text, position, resource,
                                     maxfixes = 7 )
            except:
                pass
            if not calltip:
                calltip = None

        if tryQt and calltip is not None and docstring is not None:
            # try to extract signatures from the QT docstring
            try:
                if calltip.startswith( 'QtCore.' ) or calltip.startswith( 'QtGui.' ):
                    parenPos = calltip.index( "(" )
                    dotPos = calltip.rindex( ".", 0, parenPos )
                    pattern = calltip[ dotPos : parenPos + 1 ]
                    signatures = []
                    for line in docstring.splitlines():
                        line = line.strip()
                        if pattern in line and not line.endswith( ':' ):
                            signatures.append( line )
                    if signatures:
                        calltip = '\n'.join( signatures )
            except:
                pass

        if calltip:
            # Sometimes rope makes a mistake and provides a calltip for the
            # wrong function. Check the name here.
            line, index = editor.lineIndexFromPosition( position )
            word = str( editor.getWord( line, index ) )
            if word and not (word.startswith( '__' ) and word.endswith( '__' )):
                fullName = calltip.split( '(', 1 )[ 0 ].strip()
                lastPart = fullName.split( '.' )[ -1 ]
                if lastPart != word:
                    # Wrong calltip
#                    print "Wrong calltip. Asked: '" + word + "' received: '" + lastPart + "'"
#                    print calltip
                    return None, None

        return calltip, docstring
    except:
        return None, None


def getDefinitionLocation( fileName, editor ):
    " Provides the definition location or None "
    try:
        GlobalData().validateRopeProject()
        ropeProject = GlobalData().getRopeProject( fileName )
        position = editor.currentPosition()
        text = editor.text()

        resource = None
        if os.path.isabs( fileName ):
            resource = path_to_resource( ropeProject, fileName )

        return find_definition( ropeProject, text, position,
                                resource, maxfixes = 7 )
    except:
        return None

def _switchFileAndBuffer( fileName, editor ):
    """ Saves the original file under a temporary name and
        writes the content into the original file if needed """
    if editor.isModified():
        content = unicode( editor.text() )
        dirName = os.path.dirname( fileName )
        fName = os.path.basename( fileName )
        temporaryName = dirName + os.path.sep + "." + fName + ".rope-temp"
        os.rename( fileName, temporaryName )

        f = open( fileName, "wb" )
        try:
            f.write( content )
        except:
            # Revert the change back
            f.close()
            os.rename( temporaryName, fileName )
            raise
        f.close()
        return temporaryName

    # The file is not modified, no need to create a temporary one
    return fileName

def _restoreOriginalFile( fileName, temporaryName, editor ):
    " removes the temporary file and validete the project if needed "
    if editor.isModified():
        if temporaryName != "":
            os.rename( temporaryName, fileName )
    return

def _buildOccurrencesImplementationsResult( locations ):
    " Cleans up the rope locations "
    result = []
    for loc in locations:
        path = os.path.realpath( loc.resource.real_path )
        result.append( [ path, loc.lineno ] )
    return result


def getOccurrences( fileName, editorOrPosition, throwException = False ):
    """ Provides occurences for the current editor position or
        for a position in a file """
    if type( editorOrPosition ) == type( 1 ):
        # This is called for a position in the existing file
        return getOccurencesForFilePosition( fileName, editorOrPosition,
                                             throwException )
    return getOccurencesForEditor( fileName, editorOrPosition,
                                   throwException )


def getOccurencesForEditor( fileName, editor, throwException ):
    " Provides a list of the current token occurences "

    temporaryName = ""
    result = []
    nameToSearch = ""
    try:
        temporaryName = _switchFileAndBuffer( fileName, editor )
        GlobalData().validateRopeProject()
        ropeProject = GlobalData().getRopeProject( fileName )
        position = editor.currentPosition()
        resource = path_to_resource( ropeProject, fileName )

        nameToSearch = worder.get_name_at( resource, position )
        result = find_occurrences( ropeProject, resource, position, True )
    except:
        if throwException:
            raise

    _restoreOriginalFile( fileName, temporaryName, editor )
    return nameToSearch, _buildOccurrencesImplementationsResult( result )


def getOccurencesForFilePosition( fileName, position, throwException ):
    " Provides a list of the token at position occurences "
    result = []
    try:
        GlobalData().validateRopeProject()
        ropeProject = GlobalData().getRopeProject( fileName )
        resource = path_to_resource( ropeProject, fileName )

        result = find_occurrences( ropeProject, resource, position, True )
    except:
        if throwException:
            raise
    return _buildOccurrencesImplementationsResult( result )


def _excludePrivateAndBuiltins( proposals ):
    " Returns a list of names excluding private members and __xxx__() methods "

    # Different versions of rope have a different name of an attribute:
    # 'kind' or 'scope'. 'scope' is newer.
    initialized = False
    hasScope = False

    result = set()
    for item in proposals:
        name = item.name
        if not name.startswith( '__' ):
            result.add( name )
            continue
        # Here: name starts with '__'
        if not initialized:
            initialized = True
            hasScope = hasattr( item, 'scope' )

        if hasScope:
            if item.scope == 'attribute' and name.endswith( '__' ):
                result.add( name )
                continue
        else:
            if item.kind == 'attribute' and name.endswith( '__' ):
                result.add( name )
                continue
    return result


def _isSystemImportOrAlias( obj, text, info ):
    " Checks if the obj is a system wide import name (possibly alias) "
    buildSystemWideModulesList()

    if obj in __systemwideModules:
        return True, obj

    # Check aliases
    if info is None:
        info = getBriefModuleInfoFromMemory( text )
    for item in info.imports:
        if item.alias == obj:
            if item.name in __systemwideModules:
                # That's an alias for a system module
                return True, item.name
            # That's an alias for something else, so stop search for a system
            # module alias
            return False, obj
    return False, obj


def getCompletionList( fileName, scope, obj, prefix,
                       editor, text, info = None ):
    """ High level function. It provides a list of suggestions for
        autocompletion depending on the text cursor scope and the
        object the user wants completion for """

    onImportModule, needToComplete, moduleName = isOnSomeImport( editor )
    if onImportModule:
        if not needToComplete:
            # No need to complete
            return [], False
        if moduleName != "":
            return list( __getImportedObjects( moduleName, fileName  ) ), False
        # Need to complete a module name
        return list( __getModuleNames( fileName ) ), True

    if isRemarkLine( editor ):
        return list( getEditorTags( editor, prefix, True ) ), False
    if isStringLiteral( editor ):
        return list( getEditorTags( editor, prefix, True ) ), False
    if obj == "" and prefix == "":
        return list( getEditorTags( editor, prefix, True ) ), False

    # Check a popular case self. and then something
    if scope.getScope() == scope.ClassMethodScope:
        infoObj = scope.getInfoObj()
        if not infoObj.isStaticMethod() and infoObj.arguments:
            firstArgName = infoObj.arguments[ 0 ]
            if firstArgName == obj:
                # The user completes the class member
                proposals, isOK = _getRopeCompletion( fileName, text,
                                                      editor, prefix )
                if isOK == False:
                    return list( getEditorTags( editor, prefix, True ) ), False

                # The rope proposals include private members and built-ins
                # which are inaccessible/not needed in most case.

                # Exclude everything private and built-in
                result = _excludePrivateAndBuiltins( proposals )

                # By some reasons rope sometimes inserts the current
                # word with '=' at the end. Let's just discard it.
                currentWord = str( editor.getCurrentWord() ).strip()
                result.discard( currentWord + "=" )

                # Add private members of the class itself
                if info is None:
                    info = getBriefModuleInfoFromMemory( text )
                _addClassPrivateNames( scope.levels[ scope.length - 2 ][ 0 ],
                                       result )
                return list( result ), False

    # Rope does not offer anything for system modules, let's handle it here
    # if so
    if obj != "":
        isSystemImport, realImportName = _isSystemImportOrAlias( obj,
                                                                 text, info )
        if isSystemImport:
            # Yes, that is a reference to something from a system module
            return list( __getImportedObjects( realImportName, "" ) ), False

    # Try rope completion
    proposals, isOK = _getRopeCompletion( fileName, text, editor, prefix )

    if isOK == False:
        return list( getEditorTags( editor, prefix, True ) ), False

    result = _excludePrivateAndBuiltins( proposals )

    # By some reasons rope sometimes inserts the current word with '=' at the
    # end. Let's just discard it.
    currentWord = str( editor.getCurrentWord() ).strip()
    result.discard( currentWord + "=" )

    if not result:
        return list( getEditorTags( editor, prefix, True ) ), False

    if obj == "":
        # Inject the editor tags as it might be good to have
        # words from another scope
        result.update( getEditorTags( editor, prefix, True ) )

    return list( result ), False
