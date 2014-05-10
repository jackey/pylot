Compiling the C++ Extensions for Using Pylot Shell/Console on Microsoft Windows.
--------------------------------------------------------------------------------

The contents of the lib/win/ directory are necessary to run Pylot in shell/console 
mode on Microsoft Windows.

The only thing these C++ extensions do is position the cursor on the console screen.

There is a compiled version for Python 2.5 and Python 2.6.

The C++ extension defines windows native functions for positioning the cursor on the 
command prompt, since ANSI sequence support is disabled by default on Windows.  
More info: http://en.wikipedia.org/wiki/ANSI_escape_code

The .pyd file is just a renamed dll.  See the C++ source code for the library.  It is 
built with Visual Studio.  You should build it for every version of Python and include 
the .pyd file when you distribute it so users don't need to install VS or mingw and 
go through the pain of building it.

Important points about compiling C/C++ extensions on Windows:
1. The easiest way is with VS, since Python for Windows is compiled 
   with VS and the needed static libraries (lib files) are easiest to
   link against with VS. If you want to use the GNU compiler (MinGW), you
   need to convert them to *.a files.
2. The linker needs to know where the python lib files are located 
   (c:\Python2x\libs).
3. The compiler needs to know where the python header files are
   (c:\Python2x\include).
4. You need to explicitly tell the linker to link with python2x.lib.
5. You need to build as release (not debug), unless you have the
   python libraries compiled for debugging.
6. The resulting dlls need to be renamed to have a pyd extension.

There are other tools like SWIG, pyrex etc. that ease the task of
creating such extensions and can generate makefiles etc.


For more help in compiling/building the extension on windows, 
please see http://www.pylot.org/dev.html