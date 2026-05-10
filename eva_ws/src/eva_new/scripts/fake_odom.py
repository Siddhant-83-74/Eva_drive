#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import math
import time

class FakeOdomPublisher(Node):
    def __init__(self):
        super().__init__('fake_odom_publisher')
        self.publisher_ = self.create_publisher(Odometry, '/odom', 10)
        self.timer = self.create_timer(0.05, self.publish_odom)  # 20Hz
        self.start_time = time.time()
    
    def publish_odom(self):
        current_time = self.get_clock().now()
        msg = Odometry()
        msg.header.stamp = current_time.to_msg()
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_footprint'
        
        t = time.time() - self.start_time
        msg.pose.pose.position.x = 0.3 * math.sin(0.5 * t)
        msg.pose.pose.position.y = 0.3 * math.cos(0.5 * t)
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation.w = 1.0
        
        msg.twist.twist.linear.x = -0.3 * math.cos(0.5 * t) * 0.05
        msg.twist.twist.angular.z = 0.2
        
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = FakeOdomPublisher()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
