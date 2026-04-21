#!/usr/bin/env python3
"""
MoveIt Servo Joystick Bridge with Frame Switching
==================================================
Converts Joy messages from remote_6d driver to TwistStamped commands for MoveIt Servo.

Key Feature: Dynamic reference frame switching between base_link and tool frame.

"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import TwistStamped


class JoyToServoNode(Node):
    """
    Subscribes to /joy and publishes TwistStamped commands to MoveIt Servo.

    Features:
    - Maps 6-axis joystick to 6-DOF Cartesian velocities
    - Toggles reference frame (base vs tool) via button press
    - Software deadzone to prevent drift
    - Configurable velocity scaling
    """

    def __init__(self):
        super().__init__('joy_to_servo_node')

        

        
        # Based on keyboard_rc.py:
        # - joystick_1: X/Y/Z axes (WASDQE keys) → Linear motion
        # - joystick_2: X/Y/Z axes (OKLI;P keys) → Rotational motion
        self.declare_parameter('axis_linear_x', 0)   # Joystick 1 X-axis
        self.declare_parameter('axis_linear_y', 1)   # Joystick 1 Y-axis
        self.declare_parameter('axis_linear_z', 2)   # Joystick 1 Z-axis
        self.declare_parameter('axis_angular_x', 3)  # Joystick 2 X-axis (roll)
        self.declare_parameter('axis_angular_y', 4)  # Joystick 2 Y-axis (pitch)
        self.declare_parameter('axis_angular_z', 5)  # Joystick 2 Z-axis (yaw)

        # Button index for frame toggle (button_1 = index 0 in keyboard_rc.py)
        self.declare_parameter('button_frame_toggle', 0)

        
        self.declare_parameter('scale_linear', 0.4)   # m/s
        self.declare_parameter('scale_angular', 0.8)  # rad/s

        
        self.declare_parameter('deadzone', 0.05)

        # Frame names (MUST match URDF!)
        self.declare_parameter('base_frame', 'sdrac_base_link')
        self.declare_parameter('tool_frame', 'axis6_1')

        
        self.axis_linear_x = self.get_parameter('axis_linear_x').value
        self.axis_linear_y = self.get_parameter('axis_linear_y').value
        self.axis_linear_z = self.get_parameter('axis_linear_z').value
        self.axis_angular_x = self.get_parameter('axis_angular_x').value
        self.axis_angular_y = self.get_parameter('axis_angular_y').value
        self.axis_angular_z = self.get_parameter('axis_angular_z').value

        self.button_frame_toggle = self.get_parameter('button_frame_toggle').value

        self.scale_linear = self.get_parameter('scale_linear').value
        self.scale_angular = self.get_parameter('scale_angular').value
        self.deadzone = self.get_parameter('deadzone').value

        self.base_frame = self.get_parameter('base_frame').value
        self.tool_frame = self.get_parameter('tool_frame').value

        
        self.current_frame = self.base_frame  
        self.last_button_state = 0           
        self.command_count = 0                

        

        
        self.joy_sub = self.create_subscription(
            Joy,
            '/joy',
            self.joy_callback,
            10  # QoS depth
        )

        
        # Topic name MUST match 'cartesian_command_in_topic' in servo_config.yaml
        self.twist_pub = self.create_publisher(
            TwistStamped,
            '/servo_node/delta_twist_cmds',
            10
        )

       
        self.create_timer(5.0, self.log_statistics)

        self.get_logger().info('=' * 60)
        self.get_logger().info('Joy to Servo Node STARTED')
        self.get_logger().info(f'  Base Frame: {self.base_frame}')
        self.get_logger().info(f'  Tool Frame: {self.tool_frame}')
        self.get_logger().info(f'  Current Mode: BASE (World Coordinates)')
        self.get_logger().info(f'  Frame Toggle Button: {self.button_frame_toggle}')
        self.get_logger().info('=' * 60)

    def joy_callback(self, joy_msg: Joy):
        """
        Processes incoming Joy messages and publishes TwistStamped commands.

        Args:
            joy_msg: sensor_msgs/msg/Joy from remote_6d driver
        """

        
        try:
            current_button = joy_msg.buttons[self.button_frame_toggle]

           
            if current_button == 1 and self.last_button_state == 0:
                # Toggle frame
                if self.current_frame == self.base_frame:
                    self.current_frame = self.tool_frame
                    self.get_logger().info('╔═════════════════════════════════════════╗')
                    self.get_logger().info('║  MODE: TOOL FRAME (End-Effector Coord) ║')
                    self.get_logger().info('╚═════════════════════════════════════════╝')
                else:
                    self.current_frame = self.base_frame
                    self.get_logger().info('╔═════════════════════════════════════════╗')
                    self.get_logger().info('║  MODE: BASE FRAME (World Coordinates)  ║')
                    self.get_logger().info('╚═════════════════════════════════════════╝')

            self.last_button_state = current_button

        except IndexError:
            
            self.get_logger().warn(
                f'Button {self.button_frame_toggle} not found in Joy message',
                throttle_duration_sec=5.0
            )

        
        twist_msg = TwistStamped()
        twist_msg.header.stamp = self.get_clock().now().to_msg()
        twist_msg.header.frame_id = self.current_frame  

       
        try:
            
            twist_msg.twist.linear.x = self._apply_scaling(
                joy_msg.axes[self.axis_linear_x], self.scale_linear
            )
            twist_msg.twist.linear.y = self._apply_scaling(
                joy_msg.axes[self.axis_linear_y], self.scale_linear
            )
            twist_msg.twist.linear.z = self._apply_scaling(
                joy_msg.axes[self.axis_linear_z], self.scale_linear
            )

            twist_msg.twist.angular.x = self._apply_scaling(
                joy_msg.axes[self.axis_angular_x], self.scale_angular
            )
            twist_msg.twist.angular.y = self._apply_scaling(
                joy_msg.axes[self.axis_angular_y], self.scale_angular
            )
            twist_msg.twist.angular.z = self._apply_scaling(
                joy_msg.axes[self.axis_angular_z], self.scale_angular
            )

        except IndexError:
            
            self.get_logger().error(
                f'Expected at least 6 axes, got {len(joy_msg.axes)}',
                throttle_duration_sec=5.0
            )
            return

        
        self.twist_pub.publish(twist_msg)
        self.command_count += 1

    def _apply_scaling(self, axis_value: float, scale: float) -> float:
        """
        Applies deadzone and scaling to joystick axis.

        Args:
            axis_value: Raw axis value from Joy message (typically -1.0 to 1.0)
            scale: Velocity scale factor

        Returns:
            Scaled velocity with deadzone applied
        """
        
        if abs(axis_value) < self.deadzone:
            return 0.0

        
        return axis_value * scale

    def log_statistics(self):
        """Periodic logging of node statistics."""
        self.get_logger().info(
            f'Commands sent: {self.command_count} | '
            f'Frame: {self.current_frame.split("_")[-1].upper()}',
            throttle_duration_sec=5.0
        )


def main(args=None):
    """Main entry point."""
    rclpy.init(args=args)
    node = JoyToServoNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down by user request')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
