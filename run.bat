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

echo Render room ...
call "%~dp0scripts\render_room.bat"
echo Render room done

echo Render object ...
call "%~dp0scripts\render_objects.bat"
echo Render object done

echo Render zombie ...
call "%~dp0scripts\render_zombie.bat"
echo Render zombie done

echo Render top view pz map ...
call "%~dp0scripts\render_base_top.bat"
echo Render top view pz map done

echo Render top view zombie ...
call "%~dp0scripts\render_zombie_top.bat"
echo Render top view zombie done

echo Render foraging ...
call "%~dp0scripts\render_foraging.bat"
echo Render foraging done

echo Render top view foraging ...
call "%~dp0scripts\render_foraging_top.bat"
echo Render top view foraging done

echo All done
pause
