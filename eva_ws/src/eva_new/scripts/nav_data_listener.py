#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import PoseStamped, Twist
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from geometry_msgs.msg import TransformStamped

class NavDataListener(Node):
    def __init__(self):
        super().__init__('nav_data_listener')
        
        # TF buffer + listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Goal + vel
        self.goal_sub = self.create_subscription(
            PoseStamped, '/clicked_point', self.goal_cb, 10)
        self.vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.vel_cb, 10)
        
        self.current_pose = None
        self.goal_pose = None
        self.cmd_vel = None
        
        # Timer for TF lookup
        self.timer = self.create_timer(0.2, self.tf_cb)  # 5Hz

    def tf_cb(self):
        try:
            # FIXED: Use now() + timeout
            now = self.get_clock().now()
            t = self.tf_buffer.lookup_transform(
                'map', 'base_footprint', now,
                timeout=Duration(seconds=0.1))
            self.current_pose = t  # TransformStamped (Pose msg compatible)
            self.get_logger().info(f'Curr TF: x={t.transform.translation.x:.2f} y={t.transform.translation.y:.2f}')
            self.log_poses()
        except TransformException as ex:
            pass  # Silent - common during init

    def goal_cb(self, msg):
        self.get_logger().info(f'Goal set: x={msg.pose.position.x:.2f} y={msg.pose.position.y:.2f}')
        self.goal_pose = msg.pose
        self.log_poses()

    def vel_cb(self, msg):
        self.get_logger().info(f'Vel: lin.x={msg.linear.x:.2f} ang.z={msg.angular.z:.2f}')

    def log_poses(self):
        if self.current_pose and self.goal_pose:
            x = self.current_pose.transform.translation.x
            y = self.current_pose.transform.translation.y
            z = self.current_pose.transform.translation.z
            gx = self.goal_pose.position.x
            gy = self.goal_pose.position.y
            gz = self.goal_pose.position.z
            self.get_logger().info(f'CURR: {x:.2f},{y:.2f},{z:.2f} | GOAL: {gx:.2f},{gy:.2f},{gz:.2f}')

def main(args=None): 
    rclpy.init(args=args)
    node = NavDataListener()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
