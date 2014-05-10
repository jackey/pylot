/* 
#    Copyright (c) 2008-2009 Vasil Vangelovski (vvangelovski@gmail.com)
#    License: GNU GPLv3
#
#    This file is part of Pylot.
#    
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.  See the GNU General Public License 
#    for more details.
#
#
#    This program positions the cursor for Pylot's shell/console mode on Windows.
*/


#include <windows.h>
#include <iostream>
#include <python.h>

using namespace std;


// position the command prompt cursor to given coordinates
void gotoxy( short x, short y ) {
    HANDLE hStdout = GetStdHandle(STD_OUTPUT_HANDLE);
    COORD position = { x, y };
    SetConsoleCursorPosition( hStdout, position );
}

// get the current cursor coordinates
COORD getpos(void) {
    HANDLE hStdout = GetStdHandle(STD_OUTPUT_HANDLE);
    CONSOLE_SCREEN_BUFFER_INFO csbi;
    GetConsoleScreenBufferInfo(hStdout, &csbi );
    return csbi.dwCursorPosition;
}

// wrapper for gotoxy
static PyObject *wrap_gotoxy(PyObject *self, PyObject *args)
{
	short x, y;
	if (!PyArg_ParseTuple(args, "ii", &x, &y)) {
		return NULL;
	}
    gotoxy(x,y);
	    Py_INCREF(Py_None);
    return Py_None;
}

// wrapper for getpos
static PyObject *wrap_getpos(PyObject *self, PyObject *args)
{
    int ok = PyArg_ParseTuple( args, "");
        if(!ok) return 0;
    COORD c = getpos();
    // return python tuple of two ints
    return Py_BuildValue("ii", c.X, c.Y);
}



// standard code for python extensions

PyMethodDef methods[] = {
  {"gotoxy", wrap_gotoxy, METH_VARARGS, "position the console cursor"},
  {"getpos", wrap_getpos, METH_VARARGS, "get console cursor position"},
  {NULL, NULL}
};

extern "C"
__declspec(dllexport)
void init_consolepos26(void)
{
    PyObject *m =
        Py_InitModule4(
            "_consolepos26",   // name of the module
            methods,  // name of the method table
            "C++ Console cursor postioning module",  // doc string for module
            0,  // last two never change
            PYTHON_API_VERSION);
    return;
}