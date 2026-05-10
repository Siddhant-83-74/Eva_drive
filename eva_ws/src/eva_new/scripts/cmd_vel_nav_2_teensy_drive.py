#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class Nav2ToTwist(Node):
    def __init__(self):
        super().__init__('nav2_to_teensy_converter')

        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel_nav', self.cmd_vel_callback, 10)

        self.cmd_vel_pub = self.create_publisher(Twist, '/teensy_drive', 10)

        self.get_logger().info('Relaying /cmd_vel_nav → /cmd_vel')

    def cmd_vel_callback(self, msg):
        out = Twist()
        out.linear.x  =  msg.linear.x
        out.linear.y  =  msg.linear.y   # flip if needed
        out.angular.z = -msg.angular.z  # flip if needed

        self.cmd_vel_pub.publish(out)

        self.get_logger().info(
            f'vx={out.linear.x:+.2f}  vy={out.linear.y:+.2f}  vw={out.angular.z:+.2f}'
        )

def main(args=None):
    rclpy.init(args=args)
    try:
        node = Nav2ToTwist()
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\nShutting down...')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
