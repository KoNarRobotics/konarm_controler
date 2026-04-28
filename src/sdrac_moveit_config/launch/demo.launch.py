import os
import yaml
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_demo_launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def launch_setup(context, *args, **kwargs):
    use_real_hardware = LaunchConfiguration("use_real_hardware").perform(context)

    # Wczytaj parametry CAN z yaml — analogicznie do starego konarm_driver_parameters.yaml
    config_path = os.path.join(
        get_package_share_directory("konarm_hardware"),
        "config", "hardware_parameters.yaml"
    )
    with open(config_path, "r") as f:
        hw_config = yaml.safe_load(f)

    can_interface = str(hw_config.get("can_interface", "can0"))
    can_timeout_s = str(hw_config.get("can_timeout_s", 2.0))

    moveit_config = (
        MoveItConfigsBuilder(
            robot_name="sdrac",
            package_name="sdrac_moveit_config",
        )
        .robot_description(
            mappings={
                "use_real_hardware": use_real_hardware,
                "can_interface":     can_interface,
                "can_timeout_s":     can_timeout_s,
            }
        )
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .to_moveit_configs()
    )

    demo_launch = generate_demo_launch(moveit_config)

    demo_launch.add_action(Node(
        package="controller_manager",
        executable="spawner",
        arguments=["konarm_velocity_controller", "-c", "/controller_manager"],
    ))

    return demo_launch.entities


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "use_real_hardware",
            default_value="false",
            description="Use real KonArm hardware (true) or mock simulation (false)",
        ),
        OpaqueFunction(function=launch_setup),
    ])
