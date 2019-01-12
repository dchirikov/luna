/*
* Written by Dmitry Chirikov <dmitry@chirikov.ru>
* This file is part of Luna, cluster provisioning tool
* https://github.com/dchirikov/luna
*
* This file is part of Luna.
*
* Luna is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.

* Luna is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with Luna.  If not, see <http://www.gnu.org/licenses/>.
*/

#pragma once

#include <iostream>
#include <string>
#include <cstdlib>
#include "../config.hpp"
#include "../optionparser/optionparser.hpp"
#include "../logger/logger.hpp"
#include <csignal>
#include <signal.h>
#include <sys/types.h>
#include <sys/stat.h>

#define log_error(msg) LOG4CPLUS_ERROR(logger_, msg)
#define log_info(msg) LOG4CPLUS_INFO(logger_, msg)
#define log_debug(msg) LOG4CPLUS_DEBUG(logger_, msg)
#define log_trace(msg) LOG4CPLUS_TRACE(logger_, msg)

class LTorrent {
public:
  LTorrent(const OptionParser &opts);
  static void stopHandler(int signal);
  static int createDirs(const OptionParser &opts);
  static int changeUser(const OptionParser &opts);
  static int killProcess(const OptionParser &opts);
  int createDirs();
  int registerHandlers();
  int createPidFile();
  int daemonize();
  int run();
  int cleanup();
private:
  const OptionParser opts_;
  log4cplus::Logger logger_;
  static bool running_;
};
