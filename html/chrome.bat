@echo off
FOR /F "tokens=2* skip=2" %%a in ('reg query HKCR\ChromeHTML\shell\open\command /ve') do set chrome_cmd=%%b

set "args=%chrome_cmd:*.exe"=%"

call set "chrome=%%chrome_cmd:%args%=%%"
echo using chrome at [%chrome%]
echo calling chrome %*

start "chrome" %chrome% %*