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

std::sig_atomic_t LTorrent::running_ = true;
std::sig_atomic_t LTorrent::needUpdate_ = true;

LTorrent::LTorrent(const OptionParser &opts)
  : opts_(opts),
    logger_(log4cplus::Logger::getInstance(DEFAULT_LOGGER_NAME))
{
  log_trace(__PRETTY_FUNCTION__);
};

void LTorrent::stopHandler(int signal) {
  auto logger = log4cplus::Logger::getInstance(DEFAULT_LOGGER_NAME);
  LOG4CPLUS_TRACE(logger, __PRETTY_FUNCTION__);
  running_ = false;
}

void LTorrent::updateHandler(int signal) {
  auto logger = log4cplus::Logger::getInstance(DEFAULT_LOGGER_NAME);
  LOG4CPLUS_TRACE(logger, __PRETTY_FUNCTION__);
  needUpdate_ = true;
}

int LTorrent::daemonize() {
  log_trace(__PRETTY_FUNCTION__);
  if (!opts_.daemonize) {
    log_debug("Running in foreground");
    return(EXIT_SUCCESS);
  }
  log_debug("Starting to daemonize");
  pid_t pid;
  // first fork
  pid = fork();
  if (pid < 0) {
    log_error("Unable to perform first fork");
    return(EXIT_FAILURE);
  }
  // parent exit
  if (pid > 0) {
    exit(EXIT_SUCCESS);
  }
  log_debug("First fork succeded");
  // child become session leader
  if (setsid() < 0) {
    log_error("Unable to become session leader.");
    exit(EXIT_FAILURE);
  }
  // second fork
  if (pid < 0) {
    log_error("Unable to perform second fork");
    return(EXIT_FAILURE);
  }
  // parent exit (first child)
  if (pid > 0) {
    exit(EXIT_SUCCESS);
  }
  // current process is grandchild
  // set new file perms
  umask(0);
  // close STDIN, SDTOUT and STDERR
  for (int i=0; i>=2; i++)
  {
    close(i);
  }

  return(EXIT_SUCCESS);
}

int LTorrent::registerHandlers() {
  log_trace(__PRETTY_FUNCTION__);
  std::signal(SIGINT, stopHandler);
  std::signal(SIGTERM, stopHandler);
  std::signal(SIGHUP, updateHandler);
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
  // change directory
  if (chdir(opts_.homeDir.c_str())) {
    log_error("Unable to change directory to '" << opts_.homeDir << "'");
    return(EXIT_FAILURE);
  }
  log_debug("Run main loop");
  Torrents torrents(opts_);
  if (!torrents.init()) {
    log_error("Unable to initialize torrents");
    return(EXIT_FAILURE);
  }
  while (running_) {
    log_trace("running");
    if (needUpdate_) {
      needUpdate_ = false;
      torrents.update();
    }
    torrents.readAlerts();
    torrents.deleteOldTorrents();
    sleep(1);
  }
  log_debug("Stopping");

  return(0);
}
