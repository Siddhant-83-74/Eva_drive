cmake_minimum_required(VERSION 3.8)
project(eva_new)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)

# Install Python modules (for gait_ik_visualization)
ament_python_install_package(${PROJECT_NAME})

install(
  DIRECTORY urdf meshes launch config maps
  DESTINATION share/${PROJECT_NAME}
)

# Install Python scripts nav2_to_teensy_converter
install(PROGRAMS
  scripts/nav_data_listener.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME nav_data_listener
)

install(PROGRAMS
  scripts/nav2_to_teensy_converter.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME nav2_to_teensy_converter
)


if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
