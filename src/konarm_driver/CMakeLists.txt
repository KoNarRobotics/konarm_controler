cmake_minimum_required(VERSION 3.8)
project(konarm_driver)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)

# Set required dependencies
set(THIS_PACKAGE_INCLUDE_DEPENDS
  ament_cmake
  rclcpp
  std_msgs
  generate_parameter_library
  sensor_msgs
  ari_shared_types
  can_device
  diagnostic_msgs
  konarm_driver_msg
)

set(CMAKE_CXX_STANDARD 20)
foreach(Dependency IN ITEMS ${THIS_PACKAGE_INCLUDE_DEPENDS})
  find_package(${Dependency} REQUIRED)
endforeach()


## PARAMETERS
set(PARAMETERS_LIB_NAME "${PROJECT_NAME}_parameters")
generate_parameter_library( ${PARAMETERS_LIB_NAME}
  src/${PARAMETERS_LIB_NAME}.yaml
)

set(EXPORT_COMPILE_COMMANDS ON)


add_executable(konarm_driver
  src/konarm_driver.cpp
  # konarm_joint_driver.cpp is now compiled into konarm_joint_driver_lib
)

add_executable(konarm_basic_joystick_driver
src/konarm_basic_joystick_driver.cpp
)

add_subdirectory(sdrac_shared_types)

# --------------------------------------------------------------------------
# konarm_joint_driver_lib — exported shared library consumed by konarm_hardware.
#
# sdrac_shared_types is an INTERFACE sub-directory library; its source and
# headers are compiled directly here so downstream packages get a
# self-contained target without needing the sub-directory.
# --------------------------------------------------------------------------
add_library(konarm_joint_driver_lib SHARED
  src/konarm_joint_driver.cpp
  sdrac_shared_types/src/sdrac_shared_types.cpp
)

target_compile_features(konarm_joint_driver_lib PUBLIC cxx_std_20)

target_include_directories(konarm_joint_driver_lib PUBLIC
  $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
  $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/sdrac_shared_types/src>
  $<INSTALL_INTERFACE:include/${PROJECT_NAME}>
)

ament_target_dependencies(konarm_joint_driver_lib PUBLIC
  rclcpp
  std_msgs
  ari_shared_types
  can_device
  konarm_driver_msg
)

install(TARGETS konarm_joint_driver_lib
  EXPORT export_konarm_joint_driver_lib
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

# Install sdrac_shared_types header alongside konarm_driver headers so it is
# found at include/konarm_driver/sdrac_shared_types.hpp (INSTALL_INTERFACE path).
install(
  FILES sdrac_shared_types/src/sdrac_shared_types.hpp
  DESTINATION include/${PROJECT_NAME}
)

ament_export_targets(export_konarm_joint_driver_lib HAS_LIBRARY_TARGET)
# --------------------------------------------------------------------------

target_compile_features(${PROJECT_NAME} PUBLIC cxx_std_20)

target_include_directories(${PROJECT_NAME} PUBLIC
  $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include/${PROJECT_NAME}>
)

ament_target_dependencies(
  ${PROJECT_NAME} PUBLIC
  ${THIS_PACKAGE_INCLUDE_DEPENDS}
)

target_link_libraries(
  ${PROJECT_NAME} PUBLIC
    ${PARAMETERS_LIB_NAME}
    konarm_joint_driver_lib  # provides KonArmJointDriver + sdrac_shared_types symbols
)

target_include_directories(konarm_basic_joystick_driver PUBLIC
  $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include/${PROJECT_NAME}>
)

ament_target_dependencies(
  konarm_basic_joystick_driver PUBLIC
  ${THIS_PACKAGE_INCLUDE_DEPENDS}
)

target_link_libraries(
  konarm_basic_joystick_driver PUBLIC
    ${PARAMETERS_LIB_NAME}
    sdrac_shared_types

)



if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

install(TARGETS ${PROJECT_NAME}
  DESTINATION lib/${PROJECT_NAME}
)

install(TARGETS konarm_basic_joystick_driver
  DESTINATION lib/${PROJECT_NAME}
)


install(DIRECTORY include/
  DESTINATION include/${PROJECT_NAME}
)


ament_export_dependencies(${THIS_PACKAGE_INCLUDE_DEPENDS})

ament_package()
