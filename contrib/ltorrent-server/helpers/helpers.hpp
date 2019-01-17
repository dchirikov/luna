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
#include <fstream>
#include <string>
#include <cstdlib>
#include "../config.hpp"
#include "../optionparser/optionparser.hpp"
#include <csignal>
#include <signal.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <vector>
#include <dirent.h>

namespace helpers {
  int create_dir(std::string path);
  int chowner(std::string path, uid_t pw_uid, gid_t pw_gid);
  int create_dir_and_chown(std::string path, uid_t pw_uid, gid_t pw_gid);
  int createDirs(const OptionParser &opts);
  int changeUser(const OptionParser &opts);
  bool pidFileExists(const OptionParser &opts);
  int killProcess(const OptionParser &opts);
  std::vector<std::string> readDirectory(const std::string& dirname);
}

std::ostream& operator <<(std::ostream& os, const std::vector<std::string>& v);
