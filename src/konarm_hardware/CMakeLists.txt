cmake_minimum_required(VERSION 3.8)
project(konarm_hardware)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(THIS_PACKAGE_INCLUDE_DEPENDS
  hardware_interface
  pluginlib
  rclcpp
  rclcpp_lifecycle
  konarm_driver
  can_device
  ari_shared_types
)

find_package(ament_cmake REQUIRED)
foreach(Dependency IN ITEMS ${THIS_PACKAGE_INCLUDE_DEPENDS})
  find_package(${Dependency} REQUIRED)
endforeach()

# Require ros2_control >= 4.0 (Jazzy)
find_package(controller_manager 4.0.0 REQUIRED)

# ---- Plugin shared library ------------------------------------------------
add_library(${PROJECT_NAME} SHARED
  src/konarm_hardware.cpp
)

target_compile_features(${PROJECT_NAME} PUBLIC cxx_std_20)

target_include_directories(${PROJECT_NAME} PUBLIC
  $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include/${PROJECT_NAME}>
)

ament_target_dependencies(${PROJECT_NAME} PUBLIC
  ${THIS_PACKAGE_INCLUDE_DEPENDS}
)

# Link against the joint-driver library extracted from konarm_driver.
# This brings in KonArmJointDriver, KonArmJointDriverBase, and sdrac_shared_types.
target_link_libraries(${PROJECT_NAME} PUBLIC
  konarm_driver::konarm_joint_driver_lib
)

# Register plugin description file with pluginlib
pluginlib_export_plugin_description_file(hardware_interface konarm_hardware.xml)

# ---- Install --------------------------------------------------------------
install(
  DIRECTORY include/
  DESTINATION include/${PROJECT_NAME}
)

install(TARGETS ${PROJECT_NAME}
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

# ---- Export ---------------------------------------------------------------
ament_export_targets(export_${PROJECT_NAME} HAS_LIBRARY_TARGET)
ament_export_dependencies(${THIS_PACKAGE_INCLUDE_DEPENDS})

ament_package()
