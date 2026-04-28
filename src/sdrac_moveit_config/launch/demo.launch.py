from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_demo_launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    use_real_hardware = LaunchConfiguration("use_real_hardware").perform(context)

    moveit_config = (
        MoveItConfigsBuilder(
            robot_name="sdrac",
            package_name="sdrac_moveit_config"
        )
        .robot_description(
            mappings={"use_real_hardware": use_real_hardware}
        )
        .trajectory_execution(
            file_path="config/moveit_controllers.yaml"
        )
        .to_moveit_configs()
    )

    demo_launch = generate_demo_launch(moveit_config)

    velocity_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["konarm_velocity_controller", "-c", "/controller_manager"],
    )
    demo_launch.add_action(velocity_controller_spawner)

    return demo_launch.entities


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "use_real_hardware",
            default_value="false",
            description="Use real KonArm hardware instead of mock"
        ),
        OpaqueFunction(function=launch_setup),
    ])
