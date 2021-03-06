# Codimension [![Build Status](https://travis-ci.org/SergeySatskiy/codimension.svg?branch=master)](https://travis-ci.org/SergeySatskiy/codimension)

Essential links:
* [Presentation of the technology and the tool] (http://codimension.org/documentation/technologypresentation/)
* [Project home page] (http://codimension.org/)
* [Packages and installation] (http://codimension.org/download/linuxdownload.html)
* [Running Codimension from a git clone] (http://codimension.org/download/runfromgit.html)
* [Hot keys cheat sheet] (http://codimension.org/documentation/cheatsheet.html)

---

**Codimension** is yet another free experimental Python IDE licensed under GPL v3.

Codimension aims to provide an integrated system for:
 * traditional text-based code editing, and
 * diagram-based code analysis.

At the moment a few graphics oriented features are implemented. One of the major (and the most visible) is a generation of a control flow diagram while the code is typed. The screenshot below shows the main area divided into two parts. The left one is a traditional text editor while the right one is a generated diagram. The diagram is updated when the IDE detects a pause in typing the code.

![Screenshot](http://satsky.spb.ru/codimension/screenshots/00-upcomingCommonView.png "Screenshot")


## Features

### Implemented features (major only, no certain order):

  * Ability to work with standalone files and with projects
  * Remembering the list of opened files (and the cursor position in each file) separately for each project
  * Editing history support within / between files
  * Ability to hide / show tab bars
  * Recently edited files list support for each project separately
  * Recent projects list support
  * Automatic watching of the project dirs for deleted / created files
  * Template supports for new python files for each project separately
  * Editor syntax highlight
  * Imports diagram for a file, a directory (recursively) or for a whole project with jumps to the code
  * Simple line counter
  * Hierarchical python files content browser with quick jumps to the code
  * Hierarchical classes / functions / globals browsers with filtering and quick jump to the code
  * Object browsers support showing docstrings as items tooltips
  * File outline tab
  * Running pylint with one click and quick jumps to the code from the produced output
  * Running pymetrics with one click and quick jumps to the code from the produced output where possible
  * Ability to run pylint / pymetrics for a file, a directory (recursively) or for a whole project
  * Table sortable representation of the McCabe cyclomatic complexity for a file or many files
  * Ability to have pylint settings file for each project separately
  * Opening file imports using a hot key; jumping to a definition of a certain imported item
  * Incremental search in a file
  * Incremental replace in a file
  * Search in files
  * Search for a name (class, function, global variable) in the project
  * Search for a file in the project
  * Jumping to a line in a file
  * Pixmaps viewer
  * Editor skins support
  * Detecting files changed outside of codimension
  * Code completers (TAB or Ctrl+Space)
  * Context help for a python file (Ctrl+F1)
  * Jump to the current tag definition (Ctrl+backslash)
  * Find occurrences (Ctrl+])
  * Main menu, editor and tab context menus
  * PythonTidy (python code beautifier) script integration and diff viewer
  * Search for unused global variables, functions, classes
  * Disassembler for classes and functions via object browsers context menu
  * Table representation of profiling results (individual scripts/project)
  * Graphics representation of profiling results (individual scripts/project)
  * Extending running/profiling parameters to close terminal upon successful completion
  * Pyflakes integration
  * Debugger
  * Calltips
  * Plugin infrastructure including Version Control System plugin support
  * SVN plugin
  * Ran and debugged script may have IO redirected to IDE
  * Main editor navigation bar
  * On-the-fly generation of the program control flow diagram
