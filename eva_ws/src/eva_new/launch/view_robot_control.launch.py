from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Package with your URDF and RViz config
    eva_new_share = get_package_share_directory('eva_new')
    urdf_file = os.path.join(eva_new_share, 'urdf', 'EVAFinal.SLDASM.urdf')
    rviz_config_file = os.path.join(eva_new_share, 'config', 'eva_new_config.rviz')
    gazebo_config_file = os.path.join(eva_new_share, 'config', 'gazebo_bridge.yaml') 
    
    # World package
    robocon_share = get_package_share_directory('robocon_world')
    world_file = os.path.join(robocon_share, 'worlds', 'arena.world')

    # === Gazebo resource path (same idea as working view_robot_gz.launch.py) ===
    # eva_new_share = .../install/eva_new/share/eva_new
    install_prefix = os.path.dirname(os.path.dirname(eva_new_share))
    install_share = os.path.join(install_prefix, 'share')          # contains eva_new, robocon_world, etc.
    robocon_models = os.path.join(robocon_share, 'models')         # explicit arena models

    ign_path_old = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    path_parts = [p for p in [ign_path_old, install_share, robocon_models] if p]
    ign_path_new = ":".join(path_parts)

    set_ign_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=ign_path_new
    )

    set_gz_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=ign_path_new
    )

    # Read URDF for robot_state_publisher
    with open(urdf_file, 'r') as infp:
        robot_description = infp.read()

    # RViz + state publishers
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen'
    )

    # REMOVED joint_state_publisher_gui - ros2_control will publish joint states
    joint_state_publisher = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
       output='screen'
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config_file],
        output='screen'
    )

    # Gazebo (ros_gz_sim) bringup
    ros_gz_share = get_package_share_directory('ros_gz_sim')
    gz_launch = os.path.join(ros_gz_share, 'launch', 'gz_sim.launch.py')

    gz_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch),
        launch_arguments={
            # Same pattern that worked in your other launch:
            'gz_args': f'-r {world_file}',
        }.items()
    )

    # Spawn entity node
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_eva_new',
        output='screen',
        arguments=[
            '-file', urdf_file,
            '-name', 'eva_new',
            '-allow_remap', 'true',
            # Pose: x y z roll pitch yaw (in radians)
            '-x', '-1.0',
            '-y', '-2.0',
            '-z', '1.0',
            '-R', '1.57',
            '-P', '1.57',
            '-Y', '0.0',
        ]
    )

    # Bridge basic topics
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        parameters=[{'config_file': gazebo_config_file}]
    )

    

    return LaunchDescription([
        set_ign_path,
        set_gz_path,
        # joint_state_publisher,  # REMOVED - ros2_control handles this now
        robot_state_publisher,
        rviz2,
        gz_bringup,
        spawn_entity,
        bridge
    ])