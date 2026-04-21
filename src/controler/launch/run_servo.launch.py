import os
import yaml
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, TimerAction 
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
   
    urdf_file = os.path.join(get_package_share_directory('sdrac_description'), 'urdf', 'sdrac.urdf')
    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    srdf_file = os.path.join(get_package_share_directory('sdrac_moveit_config'), 'config', 'sdrac.srdf')
    with open(srdf_file, 'r') as f:
        robot_desc_semantic = f.read()

    kinematics_file = os.path.join(get_package_share_directory('sdrac_moveit_config'), 'config', 'kinematics.yaml')
    with open(kinematics_file, 'r') as f:
        kinematics_yaml = yaml.safe_load(f)

    servo_yaml = os.path.join(get_package_share_directory('controler'), 'config', 'servo_config.yaml')

   
    servo_node = Node(
        package='moveit_servo',
        executable='servo_node',
        # name='servo_node',
        parameters=[
            servo_yaml,
            {'robot_description': robot_desc},
            {'robot_description_semantic': robot_desc_semantic},
            {'robot_description_kinematics': kinematics_yaml}
        ],
        output='screen'
    )

    
    switch_type = TimerAction(
        period=4.0,
        actions=[
            ExecuteProcess(
                cmd=['ros2', 'service', 'call', '/servo_node/switch_command_type', 'moveit_msgs/srv/ServoCommandType', '{command_type: 1}'],
                output='screen'
            )
        ]
    )

    return LaunchDescription([servo_node, switch_type])
