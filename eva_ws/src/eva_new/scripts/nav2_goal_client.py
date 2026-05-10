#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped

class Nav2GoalClient(Node):
    def __init__(self):
        super().__init__('nav2_goal_client')
        self.client = ActionClient(self, NavigateToPose, '/navigate_to_pose')

    def send_goal(self):
        if not self.client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('Action server not available')
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = 3.66  # Adjust these values
        goal_msg.pose.pose.position.y = 0.88
        # goal_msg.pose.pose.position.x = 1.35  # Adjust these values
        # goal_msg.pose.pose.position.y = -0.88
        goal_msg.pose.pose.orientation.w = 0.0

        self.get_logger().info('Sending goal...')

        send_goal_future = self.client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected')
            return

        self.get_logger().info('Goal accepted, waiting for result...')

        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(f'Distance remaining: {feedback.distance_remaining:.2f}m')

    def result_callback(self, future):
        result = future.result().result
        self.get_logger().info('Goal succeeded!')
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    client = Nav2GoalClient()
    client.send_goal()
    rclpy.spin(client)

if __name__ == '__main__':
    main()
