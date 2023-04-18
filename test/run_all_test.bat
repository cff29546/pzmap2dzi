@echo off

call step1_prepare_data.bat
call step2_unpack_texture.bat
pause
echo step3_test_base
call step3_test_base.bat
pause
echo step4_test_base_top
call step4_test_base_top.bat
pause
echo step5_test_grid
call step5_test_grid.bat
pause
echo step6_test_grid_top
call step6_test_grid_top.bat
pause
echo step7_test_room
call step7_test_room.bat
pause
echo step8_test_zombie
call step8_test_zombie.bat
pause
echo step9_test_zombie_top
call step9_test_zombie_top.bat
pause
echo step10_test_foraging
call step10_test_foraging.bat
pause
echo step11_test_foraging_top
call step11_test_foraging_top.bat
pause
echo step12_test_objects
call step12_test_objects.bat
pause
