#!/usr/bin/env python3
"""
Nav2 Velocity to Teensy TCP Server
Receives Twist from nav2 (/cmd_vel) and sends linear.x, linear.y, angular.z over TCP on port 45000
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import time
import socket
import select
import struct
import threading
import os
import signal

# Pack format: 3 floats = 12 bytes exactly
PACK_FORMAT = '<fff'
TCP_PORT = 45000

class Nav2ToTwist(Node):
    def __init__(self):
        super().__init__('nav2_to_teensy_converter')

        # ================== PARAMETERS ==================
        self.declare_parameter('publish_rate', 50.0)
        self.publish_rate = self.get_parameter('publish_rate').value

        # ================== ROS2 SETUP ==================
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel_nav', self.cmd_vel_callback, 10)

        # publish_period = 1.0 / self.publish_rate
        # self.timer = self.create_timer(publish_period, self.timer_callback)

        self.current_twist = Twist()
        self.nav_received = False
        self._log_counter = 0

        # ================== TCP SERVER SETUP ==================
        self._twist_lock = threading.Lock()
        self._tcp_thread = threading.Thread(target=self._tcp_server_loop, daemon=True)
        self._tcp_thread.start()

        self.get_logger().info('Nav2 to Teensy TCP Server Started')
        self.get_logger().info(f'Listening for Teensy on port {TCP_PORT}')

    # ================== TCP SERVER ==================
    def _tcp_server_loop(self):
        os.system(f'fuser -k {TCP_PORT}/tcp 2>/dev/null')
        time.sleep(0.5)
        
        while True:
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
                break
            except OSError as e:
                self.get_logger().warn(f'Bind failed ({e}) — retrying in 2s...')
                time.sleep(2)

        while True:
            try:
                readable, _, _ = select.select(inputs, [], [], 0.001)
                for s in readable:
                    if s is sock:
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
                                with self._twist_lock:
                                    vx = float(self.current_twist.linear.y)
                                    vy = float(self.current_twist.linear.x)
                                    vw = float(self.current_twist.angular.z)
                                    
                                    # vy = -vy
                                    vw = -vw

                                response = struct.pack(PACK_FORMAT, vx, vy, vw)
                                s.sendall(response)

                                self._log_counter += 1
                                if self._log_counter % 10 == 0 and self.nav_received:
                                    self._log_counter = 0
                                    stat = "curr" if self.nav_received else "last"
                                    if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(vw) > 0.01:
                                        self.get_logger().info(
                                            f'NAV2->TEENSY ({stat}): vx={vx:+.2f} '
                                            f'vy={vy:+.2f} '
                                            f'vw={vw:+.2f}'
                                        )

                        except Exception as e:
                            self.get_logger().warn(f'Teensy disconnected: {e}')
                            inputs.remove(s)
                            s.close()
            except Exception as e:
                self.get_logger().error(f'TCP server error: {e}')

    # ================== NAV2 CMD_VEL CALLBACK ==================
    def cmd_vel_callback(self, msg):
        if not self.nav_received:
            self.get_logger().info('Nav2 cmd_vel received!')
            self.nav_received = True

        with self._twist_lock:
            self.current_twist = msg  # Direct assignment is safe
        
        vx = float(self.current_twist.linear.x)
        vy = float(self.current_twist.linear.y)
        vw = float(self.current_twist.angular.z)
        vw = -vw
        vy = -vy


        self.get_logger().info(
            f'NAV2->LOGING : vx={vx:+.2f} '
            f'vy={vy:+.2f} '
            f'vw={vw:+.2f}'
        )


def main(args=None):
    rclpy.init(args=args)
    try:
        node = Nav2ToTwist()
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\n\nShutting down...') 
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
