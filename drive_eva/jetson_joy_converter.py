#!/usr/bin/env python3
"""
Joy to Twist Converter for Swedish Drive
Converts PS4 controller input to velocity commands for Teensy
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist


class JoyToTwist(Node):
    def __init__(self):
        super().__init__('joy_to_twist_converter')
        
        # ================== PARAMETERS ==================
        self.declare_parameter('deadzone', 0.05)
        self.declare_parameter('max_linear_vel', 1.0)
        self.declare_parameter('max_angular_vel', 1.0)
        self.declare_parameter('publish_rate', 50.0)  # Hz
        
        self.deadzone = self.get_parameter('deadzone').value
        self.max_linear_vel = self.get_parameter('max_linear_vel').value
        self.max_angular_vel = self.get_parameter('max_angular_vel').value
        
        # ================== PS4 CONTROLLER MAPPING ==================
        # Axes indices for PS4 controller
        self.AXIS_LEFT_X = 0      # Strafe (left/right)
        self.AXIS_LEFT_Y = 1      # Forward/backward
        self.AXIS_RIGHT_X = 2     # Rotation
        
        # ================== ROS2 SETUP ==================
        # Subscriber to joy topic
        self.joy_sub = self.create_subscription(
            Joy,
            'joy',
            self.joy_callback,
            10
        )
        
        # Publisher to cmd_vel topic
        self.twist_pub = self.create_publisher(
            Twist,
            'teensy_drive',
            10
        )
        
        # Timer for consistent publishing
        publish_period = 1.0 / self.get_parameter('publish_rate').value
        self.timer = self.create_timer(publish_period, self.timer_callback)
        
        # Store latest joystick values
        self.current_twist = Twist()
        self.joy_received = False
        
        self.get_logger().info('=================================')
        self.get_logger().info('Joy to Twist Converter Started')
        self.get_logger().info('=================================')
        self.get_logger().info(f'Deadzone: {self.deadzone}')
        self.get_logger().info(f'Max Linear Vel: {self.max_linear_vel}')
        self.get_logger().info(f'Max Angular Vel: {self.max_angular_vel}')
        self.get_logger().info(f'Publishing at {self.get_parameter("publish_rate").value} Hz')
        self.get_logger().info('=================================')
        self.get_logger().info('Waiting for controller input...')
        self.get_logger().info('=================================\n')
    
    def apply_deadzone(self, value):
        """Apply deadzone to joystick value"""
        if abs(value) < self.deadzone:
            return 0.0
        # Scale the remaining range to 0-1
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)
    
    def joy_callback(self, msg):
        """Process incoming joystick messages"""
        if not self.joy_received:
            self.get_logger().info('✓ Controller connected!')
            self.joy_received = True
        
        # Safety check - make sure we have enough axes
        if len(msg.axes) < 3:
            self.get_logger().warn('Insufficient axes on joystick')
            return
        
        # Read joystick axes (inverted for correct movement)
        #X,Y ARE NOT INVERTED
        left_x = msg.axes[self.AXIS_LEFT_X]   # Strafe (left stick X)
        left_y = msg.axes[self.AXIS_LEFT_Y]   # Forward (left stick Y)
        right_x = msg.axes[self.AXIS_RIGHT_X] # Rotation (right stick X)
        
        # Apply deadzone
        left_x = self.apply_deadzone(left_x)
        left_y = self.apply_deadzone(left_y)
        right_x = self.apply_deadzone(right_x)
        
        # Create Twist message
        twist = Twist()
        
        # Map joystick to velocity commands
        # PS4 axes are typically -1 to 1, but Y is inverted
        twist.linear.x = left_y * self.max_linear_vel      # Forward/backward
        twist.linear.y = left_x * self.max_linear_vel      # Strafe left/right
        twist.angular.z = -right_x * self.max_angular_vel  # Rotation (inverted)
        
        # Store for publishing
        self.current_twist = twist
    
    def timer_callback(self):
        """Publish twist messages at constant rate"""
        # Publish the current twist command
        self.twist_pub.publish(self.current_twist)
        
        # Optional: Log values periodically (every 2 seconds)
        if hasattr(self, '_log_counter'):
            self._log_counter += 1
        else:
            self._log_counter = 0
        
        if self._log_counter % 100 == 0 and self.joy_received:  # Every 2 sec at 50Hz
            if abs(self.current_twist.linear.x) > 0.01 or \
               abs(self.current_twist.linear.y) > 0.01 or \
               abs(self.current_twist.angular.z) > 0.01:
                self.get_logger().info(
                    f'CMD: vx={self.current_twist.linear.x:+.2f} '
                    f'vy={self.current_twist.linear.y:+.2f} '
                    f'vw={self.current_twist.angular.z:+.2f}'
                )


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = JoyToTwist()
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\n\nShutting down...')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
