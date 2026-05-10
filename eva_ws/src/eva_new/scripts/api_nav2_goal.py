#!/usr/bin/env python3

import math
import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped

app = FastAPI(title="Nav2 Goal API")

# ─── GLOBAL CONFIG (Defined FIRST!) ───────────────────────────────────────────
LOCATIONS = {
    "home": {"x": 0.0,  "y": 0.0,   "yaw": 0.0},
    "front_cupboard": {"x": 3.66, "y": 0.88,  "yaw": 0.0},
    "near_ac": {"x": 1.35, "y": -0.97, "yaw": math.pi / 2},
    # "loc3": {"x": 5.00, "y": 2.50,  "yaw": math.pi},
}

ros_node = None

# ─── ROS2 NAVIGATION NODE ─────────────────────────────────────────────────────
class Nav2GoalNode(Node):
    def __init__(self):
        super().__init__('nav2_goal_api')
        self.client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.status = "idle"

    def yaw_to_quaternion(self, yaw):
        return [0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)]

    async def send_goal_async(self, target):
        """Send Nav2 goal asynchronously"""
        global ros_node
        ros_node.status = "sending_goal"
        
        # Check Nav2 server availability
        if not self.client.wait_for_server(timeout_sec=5.0):
            ros_node.status = "error_nav2_unavailable"
            raise HTTPException(status_code=503, detail="Nav2 action server unavailable")

        # Validate location
        if target not in LOCATIONS:
            ros_node.status = f"error_unknown_location_{target}"
            raise HTTPException(
                status_code=404, 
                detail=f"Unknown location: '{target}'. Valid: {list(LOCATIONS.keys())}"
            )

        loc = LOCATIONS[target]
        
        # Create goal
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = loc["x"]
        goal_msg.pose.pose.position.y = loc["y"]
        orien = self.yaw_to_quaternion(loc["yaw"])
        goal_msg.pose.pose.orientation.x = orien[0]
        goal_msg.pose.pose.orientation.y = orien[1]
        goal_msg.pose.pose.orientation.z = orien[2]
        goal_msg.pose.pose.orientation.w = orien[3]


        self.get_logger().info(f'🎯 Sending to {target}: ({loc["x"]:.2f}, {loc["y"]:.2f}, Angle : {loc["yaw"]:.2f})')
        ros_node.status = f"navigating_{target}"

        # Send async goal
        future = self.client.send_goal_async(goal_msg, feedback_callback=self.feedback_cb)
        future.add_done_callback(self.goal_response_cb)
        
        return {
            "success": True, 
            "message": f"Goal sent to {target}",
            "target": target,
            "position": {"x": loc["x"], "y": loc["y"], "yaw": loc["yaw"]}
        }

    def feedback_cb(self, feedback_msg):
        dist = feedback_msg.feedback.distance_remaining
        ros_node.status = f"navigating_{dist:.1f}m_remaining"

    def goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            ros_node.status = "error_goal_rejected"
            return
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.result_cb)

    def result_cb(self, future):
        ros_node.status = "idle_goal_reached"
        self.get_logger().info('✅ Goal completed successfully!')

# ─── FASTAPI ROUTES ───────────────────────────────────────────────────────────
@app.get("/status")
async def get_status():
    return {"status": getattr(ros_node, 'status', 'initializing')}

@app.get("/locations")
async def get_locations():
    return LOCATIONS

@app.post("/nav2_send_goal")
async def nav2_send_goal(request: dict):
    """Send navigation goal to ROS2 Nav2"""
    target = request.get("target")
    if not target:
        raise HTTPException(status_code=400, detail="Missing 'target' in request")
    
    try:
        result = await ros_node.send_goal_async(target)
        return result
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        ros_node.status = f"error_internal_{str(e)[:20]}"
        print(ros_node.status)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# ─── MAIN ENTRYPOINT ──────────────────────────────────────────────────────────
async def main():
    global ros_node
    
    print("🔧 Initializing ROS2...")
    rclpy.init()
    ros_node = Nav2GoalNode()
    
    print("🚀 Nav2 Goal API: http://localhost:8000")
    print("📡 FastAPI + ROS2 Nav2 ready!")
    print("📋 Available locations:", list(LOCATIONS.keys()))
    
    # Start FastAPI server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        if rclpy.ok():
            rclpy.shutdown()
