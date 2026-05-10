# eva_control.launch.py - Use this code to build the map and save it after building complete map by roaming around the room.

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os 
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration 
from launch_ros.substitutions import FindPackageShare 

def generate_launch_description():
    package_name = 'eva_new'
    eva_new_share = get_package_share_directory(package_name)

    # Paths to configuration files
    cartographer_config_dir = os.path.join(eva_new_share, 'config')
    map_file = os.path.join(eva_new_share, 'maps', 'map_eva.yaml') 

    configuration_basename = 'cartographer.lua'

    urdf_file = os.path.join(eva_new_share, 'urdf', 'EVAFinal.SLDASM.urdf')
    rviz_config_file = os.path.join(eva_new_share, 'config', 'eva_nav2_default.rviz') 
  
    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time')
    # resolution = LaunchConfiguration('resolution')
    # publish_period_sec = LaunchConfiguration('publish_period_sec')

    declare_map_cmd = DeclareLaunchArgument(
        'map', 
        default_value=map_file,  # Empty = SLAM-only mode (no localization)
        description='Full path to map yaml (e.g. ~/eva_map.yaml) for Nav2 localization'
    )
  
    # Declare launch arguments
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true')
    
    declare_resolution_cmd = DeclareLaunchArgument(
        'resolution',
        default_value='0.05',
        description='Resolution of the map')
    
    declare_publish_period_sec_cmd = DeclareLaunchArgument(
        'publish_period_sec',
        default_value='1.0',
        description='OccupancyGrid publishing period')
    
    # Cartographer node
    cartographer_node = Node(
        package='cartographer_ros',
        executable='cartographer_node',
        name='cartographer_node',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            '-configuration_directory', cartographer_config_dir,
            '-configuration_basename', configuration_basename
        ],
        remappings=[
            ('scan', 'scan'),
        ]
    )

    # # Cartographer occupancy grid node
    # cartographer_occupancy_grid_node = Node(
    #     package='cartographer_ros',
    #     executable='cartographer_occupancy_grid_node',
    #     name='cartographer_occupancy_grid_node',
    #     output='screen',
    #     parameters=[
    #         {'use_sim_time': use_sim_time},
    #         {'resolution': resolution},
    #         {'publish_period_sec': publish_period_sec}
    #     ]
    # )

    # After cartographer_occupancy_grid_node:
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time, 'yaml_filename': LaunchConfiguration('map')}]
    )

    odom_base_footprint_tf = Node(  # For Nav2
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'odom', 'base_footprint'],
        output='screen'
    ) 

    base_footprint_base_link_tf = Node(  # For Nav2
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'base_footprint', 'base_link'],
        output='screen'
    )  

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        parameters=[{'use_sim_time': use_sim_time, 'global_frame_id': 'map', 'odom_frame_id': 'odom', 'base_frame_id': 'base_footprint'}]
    )

    # Full Nav2
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([FindPackageShare('nav2_bringup').find('nav2_bringup'), '/launch/navigation_launch.py']),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'map': LaunchConfiguration('map'),  # ~/eva_map.yaml later
            'params_file': os.path.join(eva_new_share, 'config', 'nav2_params.yaml')
        }.items()
    )

    with open(urdf_file, 'r') as infp:
        robot_description = infp.read()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen'
    )

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
 
    # Spawn controllers with delays
    spawn_joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=["joint_state_broadcaster", "-c", "/controller_manager"]
    ) 

    sllidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([FindPackageShare('sllidar_ros2').find('sllidar_ros2'), '/launch/sllidar_s1_launch.py']),
        launch_arguments={'frame_id': 'lidar_link'}.items()  # Match URDF
    ) 

    lifecycle_manager_map = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': ['map_server']
        }]
    )


    return LaunchDescription([ 
        declare_use_sim_time_cmd,
        declare_resolution_cmd,
        declare_publish_period_sec_cmd, 
        declare_map_cmd,
        robot_state_publisher,
        joint_state_publisher,
        spawn_joint_state_broadcaster,
        cartographer_node,
        # cartographer_occupancy_grid_node,      
        odom_base_footprint_tf, 
        base_footprint_base_link_tf, 
        map_server, 
        lifecycle_manager_map,
        # amcl,
        nav2_bringup, 
        rviz2, 
        sllidar_launch
    ])