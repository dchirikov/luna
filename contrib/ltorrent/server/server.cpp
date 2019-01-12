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

#include "server.hpp"

bool LTorrent::running_ = true;

LTorrent::LTorrent(const OptionParser &opts)
  : opts_(opts),
    logger_(log4cplus::Logger::getInstance(DEFAULT_LOGGER_NAME))
{
  log_trace(__PRETTY_FUNCTION__);
};

int LTorrent::createDirs(const OptionParser &opts) {
  return(EXIT_SUCCESS);
}

void LTorrent::stopHandler(int signal) {
  auto logger = log4cplus::Logger::getInstance(DEFAULT_LOGGER_NAME);
  LOG4CPLUS_TRACE(logger, __PRETTY_FUNCTION__);
  running_ = false;
}

int LTorrent::changeUser() {
  log_trace(__PRETTY_FUNCTION__);
  setuid(1000);
  return(EXIT_SUCCESS);
}

int LTorrent::daemonize() {
  log_trace(__PRETTY_FUNCTION__);
  if (!opts_.daemonize) {
    log_debug("Running in foreground");
    return(EXIT_SUCCESS);
  }
  log_debug("Starting to daemonize");
  return(EXIT_SUCCESS);
}

int LTorrent::registerHandlers() {
  log_trace(__PRETTY_FUNCTION__);
  std::signal(SIGINT, stopHandler);
  std::signal(SIGTERM, stopHandler);
  return(EXIT_SUCCESS);
}

int LTorrent::createPidFile() {
  log_trace(__PRETTY_FUNCTION__);
  auto pid = getpid();
  log_info("Running PID " << pid);
  std::ofstream pidfile;
  log_debug("Write PID to pidfile");
  pidfile.open(opts_.pidFile);
  pidfile << pid;
  pidfile << "\n";
  pidfile.close();
  return(EXIT_SUCCESS);
}

int LTorrent::cleanup() {
  log_trace(__PRETTY_FUNCTION__);
  if (std::remove(opts_.pidFile.c_str()) != 0 ) {
    log_error("Unable to delete " << opts_.pidFile);
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

int LTorrent::run() {
  log_trace(__PRETTY_FUNCTION__);

  log_debug("Run main loop");
  while (running_) {
    log_trace("running");
    sleep(1);
  }
  log_debug("stopping");

  return(0);
}

