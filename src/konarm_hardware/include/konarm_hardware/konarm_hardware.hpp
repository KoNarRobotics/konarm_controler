/*
 * Copyright (c) 2025 Patryk Dudziński
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <memory>
#include <string>
#include <vector>

#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "rclcpp/macros.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/state.hpp"

#include "konarm_driver/konarm_joint_driver.hpp"
#include "can_device/can_device.hpp"

namespace konarm_hardware {

class KonArmHardware : public hardware_interface::SystemInterface {
public:
  RCLCPP_SHARED_PTR_DEFINITIONS(KonArmHardware)

  hardware_interface::CallbackReturn on_init(
    const hardware_interface::HardwareComponentInterfaceParams & params) override;

  hardware_interface::CallbackReturn on_configure(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_activate(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::CallbackReturn on_deactivate(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::return_type read(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

  hardware_interface::return_type write(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

private:
  struct JointHandle {
    std::string name;
    std::shared_ptr<konarm_driver::KonArmJointDriverBase> driver;
  };

  std::vector<JointHandle> joints_;
  std::shared_ptr<CanDriver> can_driver_;
  std::shared_ptr<rclcpp::Clock> clock_;

  std::string can_interface_{"can0"};
  double timeout_s_{0.5};
};

}  // namespace konarm_hardware
