@echo off
echo Unpacking textures ...
call "%~dp0scripts\unpack_texture.bat"
echo Unpacking textures done

echo Copy html files ...
call "%~dp0scripts\copy_html.bat"
echo Copy html files done

echo Render pz map ...
call "%~dp0scripts\render_base.bat"
echo Render pz map done

echo Render grid ...
call "%~dp0scripts\render_grid.bat"
echo Render grid done

echo Render room ...
call "%~dp0scripts\render_room.bat"
echo Render room done
echo All done
pause
