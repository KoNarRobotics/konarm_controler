from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_demo_launch
from launch_ros.actions import Node

def generate_launch_description():

   
    moveit_config = (
        MoveItConfigsBuilder(
            robot_name="sdrac",
            package_name="sdrac_moveit_config"
        )
        .trajectory_execution(
            file_path="config/moveit_controllers.yaml"
        )
        .to_moveit_configs()
    )

  
    demo_launch = generate_demo_launch(moveit_config)

    
    konarm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["konarm_controller", "-c", "/controller_manager", "--inactive"],
    )
    #main controller
    velocity_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["konarm_velocity_controller", "-c", "/controller_manager"],
    )
    
    demo_launch.add_action(konarm_controller_spawner)
    demo_launch.add_action(velocity_controller_spawner)

    return demo_launch
