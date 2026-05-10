from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os
import numpy as np


def generate_launch_description():
    # Robot package
    eva_new_share = get_package_share_directory('eva_new')
    urdf_file = os.path.join(eva_new_share, 'urdf', 'EVAFinal.SLDASM.urdf')

    # World package
    robocon_share = get_package_share_directory('robocon_world')
    world_file = os.path.join(robocon_share, 'worlds', 'arena.world')

    # 1) Generic install/share root (like in your working launch)
    install_prefix = os.path.dirname(os.path.dirname(eva_new_share))
    install_share = os.path.join(install_prefix, 'share')
    # 2) Explicit robocon models dir (for safety, but not strictly needed if 1) is set)
    robocon_models = os.path.join(robocon_share, 'models')

    old_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    path_parts = [p for p in [old_path, install_share, robocon_models] if p]
    new_path = ":".join(path_parts)

    set_ign_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=new_path
    )

    set_gz_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=new_path
    )

    # Gazebo bringup
    ros_gz_share = get_package_share_directory('ros_gz_sim')
    gz_launch = os.path.join(ros_gz_share, 'launch', 'gz_sim.launch.py')

    gz_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch),
        launch_arguments={
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
            '-x', '-1.0',
            '-y', '-2.0',
            '-z', '1.0',
            '-R', '1.57',
            '-P', '1.57',
            '-Y', '0.0',
        ]
    )

    # Bridge topics
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/tf_static@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
        ]
    )

    return LaunchDescription([
        set_ign_path,
        set_gz_path,
        gz_bringup,
        spawn_entity,
        bridge,
    ])
