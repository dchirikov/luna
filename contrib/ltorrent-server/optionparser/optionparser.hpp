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

#include "../config.hpp"
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <string>
#include <iostream>
#include <stdexcept>
#include <log4cplus/loglevel.h>
#include "log4cplus/clogger.h"
#include <pwd.h>
#include <wordexp.h>
#include <libgen.h>
#include <inttypes.h>

class OptionParser {
public:
  OptionParser(int argc, char* argv[]);
  std::string user = DEFAULT_LTORRENT_USER;
  std::string homeDir = DEFAULT_LTORRENT_HOMEDIR;
  std::string logFile = DEFAULT_LTORRENT_LOGFILE;
  std::string logDir;
  std::string pidFile = DEFAULT_LTORRENT_PIDFILE;
  std::string pidDir;
  int logLevel = log4cplus::INFO_LOG_LEVEL;
  int logSize = 1024 * 1024;
  int logNum = 7;
  bool logToSTDERR = true;
  bool logFlush = true;
  bool daemonize = true;
  bool kill = false;
  int killtimeout = DEFAULT_LTORRENT_KILLTIMEOUT;
  std::string logPatternInfo = "[%D{%m/%d/%y %H:%M:%S:%q}][%p] %m%n";
  std::string logPatternDebug = "[%D{%m/%d/%y %H:%M:%S:%q}][%p] %m [%b:%L]%n";
  uid_t pw_uid;
  gid_t pw_gid;
  std::vector<std::string> getImagesCmd{DEFAULT_LTORRENT_GET_OSIMAGES_CMD};
private:
  void getEnvironment_();
  void PrintHelp_();
  void expandPath_(std::string* path);
  std::string getDirname_(const std::string path);
  std::string exec_name_;
};
