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

#include <string>
#include <iostream>
#include "../config.hpp"
#include <unistd.h>
#include <log4cplus/loglevel.h>
#include <string.h>
#include <libgen.h>

class OptionParser {
public:
  OptionParser(int argc, char* argv[]);
  int logLevel = log4cplus::INFO_LOG_LEVEL;
  std::string tarball;
  std::string tarballDir;
  std::string torrent;
  std::string tracker;
  std::string logPatternInfo = "[%D{%m/%d/%y %H:%M:%S:%q}][%p] %m%n";
  std::string logPatternDebug = "[%D{%m/%d/%y %H:%M:%S:%q}][%p] %m [%b:%L]%n";
  bool logToSTDERR = true;
  bool logFlush = true;
  std::string creator = DEFAULT_CREATOR;
private:
  void PrintHelp_();
  std::string exec_name_;
  std::string getDirname_(const std::string path);
};

std::ostream& operator <<(std::ostream& os, const OptionParser& opt);
