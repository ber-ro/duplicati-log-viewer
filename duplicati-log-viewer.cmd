::goto :eof
::set >C:\Users\bernh\Seafile\src\python\DuplicatiLogViewer.cmd.env
IF *%DUPLICATI__OPERATIONNAME% NEQ *Backup GOTO :eof
set python=c:\msys64\mingw64\bin\python.exe
%python% C:\Users\bernh\..my\Seafile\src\python\duplicati-log-viewer.py %DUPLICATI__log_file%
