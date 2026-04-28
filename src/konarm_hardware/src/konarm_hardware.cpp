/*
 * Copyright (c) 2025 Patryk Dudziński
 * SPDX-License-Identifier: MIT
 *
 * KonArmHardware — ros2_control SystemInterface for the SDRAC 6-DOF arm.
 *
 * Each joint runs custom KonArm firmware on an STM32 board.
 * Communication is over SocketCAN (default: can0).
 * The firmware uses a request-response CAN protocol (not unsolicited broadcast):
 *   write() sends velocity commands + requests state for next cycle.
 *   read()  copies the latest received position/velocity/effort into state interfaces.
 *
 * CAN base IDs (mask 0xfffffff0):
 *   Rev1 = 0x610,  Rev2 = 0x620,  Rev3 = 0x630
 *   Rev4 = 0x640,  Rev5 = 0x650,  Rev6 = 0x660
 */

#include "konarm_hardware/konarm_hardware.hpp"

#include <array>
#include <string>
#include <unordered_map>

#include "can_device/can_messages.h"
#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "rclcpp/rclcpp.hpp"

namespace {

constexpr const char * kName = "KonArmHardware";

// Mask applied to CAN_KONARM_N_STATUS_FRAME_ID to get the per-joint base ID.
// The lower nibble (0x1, 0x2, …) encodes the message type; the upper nibble
// encodes the joint node address.
constexpr uint32_t kJointIdMask = 0xfffffff0u;

// Map of URDF joint name → CAN base ID.
// Derived from can_messages.h constants used in konarm_driver.cpp.
const std::unordered_map<std::string, uint32_t> kJointBaseIds = {
  {"Rev1", CAN_KONARM_1_STATUS_FRAME_ID & kJointIdMask},  // 0x610
  {"Rev2", CAN_KONARM_2_STATUS_FRAME_ID & kJointIdMask},  // 0x620
  {"Rev3", CAN_KONARM_3_STATUS_FRAME_ID & kJointIdMask},  // 0x630
  {"Rev4", CAN_KONARM_4_STATUS_FRAME_ID & kJointIdMask},  // 0x640
  {"Rev5", CAN_KONARM_5_STATUS_FRAME_ID & kJointIdMask},  // 0x650
  {"Rev6", CAN_KONARM_6_STATUS_FRAME_ID & kJointIdMask},  // 0x660
};

}  // namespace

namespace konarm_hardware {

// ---------------------------------------------------------------------------
// on_init — validate URDF, read parameters
// ---------------------------------------------------------------------------
hardware_interface::CallbackReturn KonArmHardware::on_init(
  const hardware_interface::HardwareComponentInterfaceParams & params)
{
  if (hardware_interface::SystemInterface::on_init(params) !=
      hardware_interface::CallbackReturn::SUCCESS)
  {
    return hardware_interface::CallbackReturn::ERROR;
  }

  const auto & info = params.hardware_info;

  // Optional hardware parameters
  if (info.hardware_parameters.count("can_interface")) {
    can_interface_ = info.hardware_parameters.at("can_interface");
  }
  if (info.hardware_parameters.count("timeout_s")) {
    timeout_s_ = std::stod(info.hardware_parameters.at("timeout_s"));
  }

  // Validate joint count
  if (info.joints.size() != 6) {
    RCLCPP_ERROR(rclcpp::get_logger(kName),
      "Expected exactly 6 joints, got %zu. "
      "Each of Rev1–Rev6 must be declared in the <ros2_control> block.",
      info.joints.size());
    return hardware_interface::CallbackReturn::ERROR;
  }

  // Validate each joint has at least a velocity command interface
  for (const auto & joint : info.joints) {
    bool has_vel = false;
    for (const auto & ci : joint.command_interfaces) {
      if (ci.name == hardware_interface::HW_IF_VELOCITY) {
        has_vel = true;
      }
    }
    if (!has_vel) {
      RCLCPP_ERROR(rclcpp::get_logger(kName),
        "Joint '%s' must declare a velocity command interface.",
        joint.name.c_str());
      return hardware_interface::CallbackReturn::ERROR;
    }

    // Validate joint name is known
    if (kJointBaseIds.find(joint.name) == kJointBaseIds.end()) {
      RCLCPP_ERROR(rclcpp::get_logger(kName),
        "Unknown joint name '%s'. Valid names: Rev1–Rev6.", joint.name.c_str());
      return hardware_interface::CallbackReturn::ERROR;
    }
  }

  RCLCPP_INFO(rclcpp::get_logger(kName),
    "on_init OK — CAN interface: '%s', connection timeout: %.2f s",
    can_interface_.c_str(), timeout_s_);

  return hardware_interface::CallbackReturn::SUCCESS;
}

// ---------------------------------------------------------------------------
// on_configure — create CAN driver and joint driver instances.
// Callbacks are registered inside KonArmJointDriver's constructor, which
// must happen BEFORE open_can() (called in on_activate).
// ---------------------------------------------------------------------------
hardware_interface::CallbackReturn KonArmHardware::on_configure(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  clock_ = std::make_shared<rclcpp::Clock>(RCL_ROS_TIME);

  // Create CAN driver (threaded, 100 ms RX timeout, 256-frame TX queue).
  // Do NOT call open_can() here — callbacks must be registered first.
  auto maybe_driver = CanDriver::Make(can_interface_, true, 100000, 256);
  if (!maybe_driver.ok()) {
    RCLCPP_ERROR(rclcpp::get_logger(kName),
      "Failed to create CanDriver on interface '%s'. "
      "Is the interface up? (sudo ip link set %s up type can bitrate 1000000)",
      can_interface_.c_str(), can_interface_.c_str());
    return hardware_interface::CallbackReturn::ERROR;
  }
  can_driver_ = maybe_driver.valueOrDie();

  // Instantiate one KonArmJointDriver per URDF joint.
  // The constructor registers CAN callbacks for that joint's node address.
  joints_.clear();
  for (const auto & joint_info : info_.joints) {
    const uint32_t base_id = kJointBaseIds.at(joint_info.name);

    joints_.push_back({
      joint_info.name,
      std::make_shared<konarm_driver::KonArmJointDriver>(
        rclcpp::get_logger(kName).get_child(joint_info.name),
        clock_,
        can_driver_,
        base_id
      )
    });

    RCLCPP_INFO(rclcpp::get_logger(kName),
      "  Joint '%s'  CAN base id 0x%03X",
      joint_info.name.c_str(), base_id);
  }

  // Zero all state and command interfaces
  for (const auto & [name, descr] : joint_state_interfaces_) {
    set_state(name, 0.0);
  }
  for (const auto & [name, descr] : joint_command_interfaces_) {
    set_command(name, 0.0);
  }

  RCLCPP_INFO(rclcpp::get_logger(kName), "on_configure OK");
  return hardware_interface::CallbackReturn::SUCCESS;
}

// ---------------------------------------------------------------------------
// on_activate — open CAN socket and switch firmware to velocity mode
// ---------------------------------------------------------------------------
hardware_interface::CallbackReturn KonArmHardware::on_activate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  auto status = can_driver_->open_can();
  if (!status.ok()) {
    RCLCPP_ERROR(rclcpp::get_logger(kName),
      "open_can() failed on '%s'.", can_interface_.c_str());
    return hardware_interface::CallbackReturn::ERROR;
  }

  // Release emergency stop, set VELOCITY control mode, request initial state.
  // Joints have timeout_s_ to respond before write() starts skipping them.
  for (auto & joint : joints_) {
    joint.driver->set_emergency_stop(false);
    joint.driver->set_control_mode(konarm_driver::MovementControlMode::VELOCITY);
    joint.driver->request_status();
    joint.driver->request_position();
  }

  RCLCPP_INFO(rclcpp::get_logger(kName),
    "System activated — all joints in VELOCITY mode");
  return hardware_interface::CallbackReturn::SUCCESS;
}

// ---------------------------------------------------------------------------
// on_deactivate — zero all joints, assert e-stop, close CAN
// ---------------------------------------------------------------------------
hardware_interface::CallbackReturn KonArmHardware::on_deactivate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  // 1. Safety: zero velocity and assert emergency stop on every joint
  for (auto & joint : joints_) {
    joint.driver->set_velocity(0.0f);
    joint.driver->set_emergency_stop(true);
  }

  // 2. Destroy joint drivers (they hold shared_ptr refs to can_driver_).
  //    CAN is only closed once all refs are dropped.
  joints_.clear();

  // 3. Release the plugin's own reference — CAN closes if no other holders.
  CanDriver::close_can(can_driver_);

  RCLCPP_INFO(rclcpp::get_logger(kName), "System deactivated");
  return hardware_interface::CallbackReturn::SUCCESS;
}

// ---------------------------------------------------------------------------
// read — copy latest received state into ros2_control state interfaces,
//         then issue fresh state requests for the next cycle.
// ---------------------------------------------------------------------------
hardware_interface::return_type KonArmHardware::read(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
  for (auto & joint : joints_) {
    set_state(joint.name + "/position",
              static_cast<double>(joint.driver->get_position()));
    set_state(joint.name + "/velocity",
              static_cast<double>(joint.driver->get_velocity()));
    set_state(joint.name + "/effort",
              static_cast<double>(joint.driver->get_torque()));

    // Request fresh data; responses arrive asynchronously via CAN RX thread
    // and are available the next time read() is called.
    joint.driver->request_position();
    joint.driver->request_torque();
  }

  return hardware_interface::return_type::OK;
}

// ---------------------------------------------------------------------------
// write — send velocity commands; skip joints that have timed out.
// ---------------------------------------------------------------------------
hardware_interface::return_type KonArmHardware::write(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
  const rclcpp::Time now = clock_->now();

  for (auto & joint : joints_) {
    // Connection timeout guard: if the joint hasn't responded in timeout_s_,
    // stop sending commands and request status until it comes back.
    const double age =
      (now - joint.driver->get_module_connection_time()).seconds();

    if (age > timeout_s_) {
      RCLCPP_WARN_THROTTLE(rclcpp::get_logger(kName), *clock_, 3000,
        "Joint '%s' has not responded for %.2f s (timeout %.2f s) — "
        "commands suppressed until reconnection.",
        joint.name.c_str(), age, timeout_s_);
      joint.driver->request_status();
      joint.driver->reset_state();
      continue;
    }

    const double vel_cmd =
      get_command<double>(joint.name + "/" + hardware_interface::HW_IF_VELOCITY);
    joint.driver->set_velocity(static_cast<float>(vel_cmd));
  }

  return hardware_interface::return_type::OK;
}

}  // namespace konarm_hardware

PLUGINLIB_EXPORT_CLASS(konarm_hardware::KonArmHardware, hardware_interface::SystemInterface)
