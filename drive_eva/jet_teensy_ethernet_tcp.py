#!/usr/bin/env python3
"""
Joy to Twist Converter + TCP Server for Teensy
Sends linear.x, linear.y, angular.z over TCP on port 45000
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist
import time
import socket
import select
import struct
import threading
import os
import signal

# Pack format: 3 floats = 12 bytes exactly
# '<fff' → little-endian, matches Teensy float (IEEE 754)
PACK_FORMAT = '<fff'
TCP_PORT = 45000


class JoyToTwist(Node):
    def __init__(self):
        super().__init__('joy_to_twist_converter')

        # ================== PARAMETERS ==================
        self.declare_parameter('deadzone', 0.05)
        self.declare_parameter('max_linear_vel', 1.0)
        self.declare_parameter('max_angular_vel', 1.0)
        self.declare_parameter('publish_rate', 50.0)

        self.deadzone = self.get_parameter('deadzone').value
        self.max_linear_vel = self.get_parameter('max_linear_vel').value
        self.max_angular_vel = self.get_parameter('max_angular_vel').value

        # PS4 Axis mapping
        self.AXIS_LEFT_X = 0
        self.AXIS_LEFT_Y = 1
        self.AXIS_RIGHT_X = 2

        # ================== ROS2 SETUP ==================
        self.joy_sub = self.create_subscription(Joy, 'joy', self.joy_callback, 10)
        self.twist_pub = self.create_publisher(Twist, 'cmd_vel', 10)

        publish_period = 1.0 / self.get_parameter('publish_rate').value
        self.timer = self.create_timer(publish_period, self.timer_callback)

        self.current_twist = Twist()
        self.joy_received = False
        self._log_counter = 0

        # ================== TCP SERVER SETUP ==================
        # Lock to safely read current_twist from TCP thread
        self._twist_lock = threading.Lock()

        # Start TCP server in a daemon thread (dies when main exits)
        self._tcp_thread = threading.Thread(
            target=self._tcp_server_loop, daemon=True
        )
        self._tcp_thread.start()

        self.get_logger().info('Joy to Twist + TCP Server Started')
        self.get_logger().info(f'Listening for Teensy on port {TCP_PORT}')

    # ================== TCP SERVER ==================
    def _tcp_server_loop(self):
        """
        Non-blocking TCP server (mirrors your original send_data process).
        Responds to Teensy 0x01 with packed (linear_x, linear_y, angular_z).
        """

        # Kill any process already on this port before binding
        os.system(f'fuser -k {TCP_PORT}/tcp 2>/dev/null')
        import time; time.sleep(0.5)  # Brief wait for OS to release
        
        while True:   # ← outer retry loop
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.bind(('0.0.0.0', TCP_PORT))
                sock.listen()
                sock.setblocking(False)
                inputs = [sock]
                self.get_logger().info(f'TCP server bound to 0.0.0.0:{TCP_PORT}')
                break   # ← bind succeeded, exit retry loop
            except OSError as e:
                self.get_logger().warn(f'Bind failed ({e}) — retrying in 2s...')
                time.sleep(2)
            
        """   
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.bind(('0.0.0.0', TCP_PORT))
        sock.listen()
        sock.setblocking(False)

        inputs = [sock]

        self.get_logger().info(f'TCP server bound to 0.0.0.0:{TCP_PORT}')
        """

        while True:
            try:
                readable, _, _ = select.select(inputs, [], [], 0.001)
                for s in readable:
                    if s is sock:
                        # New Teensy connection
                        conn, addr = s.accept()
                        conn.setblocking(False)
                        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        inputs.append(conn)
                        self.get_logger().info(f'Teensy connected from {addr[0]}')
                    else:
                        try:
                            data = s.recv(1)
                            if not data:
                                raise ConnectionResetError("Client disconnected")

                            if data == b'\x01':
                                # Safely grab latest twist values
                                with self._twist_lock:
                                    vx = float(self.current_twist.linear.x)
                                    vy = float(self.current_twist.linear.y)
                                    vw = float(self.current_twist.angular.z)

                                response = struct.pack(PACK_FORMAT, vx, vy, vw)
                                s.sendall(response)

                                # Optional debug
                                # self.get_logger().info(f'Sent: vx={vx:.2f} vy={vy:.2f} vw={vw:.2f}')

                        except Exception as e:
                            self.get_logger().warn(f'Teensy disconnected: {e}')
                            inputs.remove(s)
                            s.close()

            except Exception as e:
                self.get_logger().error(f'TCP server error: {e}')

    # ================== JOY CALLBACK ==================
    def apply_deadzone(self, value):
        if abs(value) < self.deadzone:
            return 0.0
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)

    def joy_callback(self, msg):
        if not self.joy_received:
            self.get_logger().info('Controller connected!')
            self.joy_received = True

        if len(msg.axes) < 3:
            self.get_logger().warn('Insufficient axes on joystick')
            return

        left_x  = self.apply_deadzone(msg.axes[self.AXIS_LEFT_X])
        left_y  = self.apply_deadzone(msg.axes[self.AXIS_LEFT_Y])
        right_x = self.apply_deadzone(msg.axes[self.AXIS_RIGHT_X])

        twist = Twist()
        twist.linear.x  =  left_y  * self.max_linear_vel
        twist.linear.y  =  left_x  * self.max_linear_vel
        twist.angular.z = -right_x * self.max_angular_vel

        # Lock because TCP thread reads this concurrently
        with self._twist_lock:
            self.current_twist = twist

    # ================== TIMER CALLBACK ==================
    def timer_callback(self):
        with self._twist_lock:
            twist = self.current_twist
        self.twist_pub.publish(twist)

        self._log_counter += 1
        if self._log_counter % 100 == 0 and self.joy_received:
            if abs(twist.linear.x) > 0.01 or \
               abs(twist.linear.y) > 0.01 or \
               abs(twist.angular.z) > 0.01:
                self.get_logger().info(
                    f'CMD: vx={twist.linear.x:+.2f} '
                    f'vy={twist.linear.y:+.2f} '
                    f'vw={twist.angular.z:+.2f}'
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

