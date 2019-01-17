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

#include "helpers.hpp"


int helpers::create_dir(std::string path) {
  struct stat info;
  if (stat(path.c_str(), &info) == 0 ) {
    if ((info.st_mode & S_IFMT) == S_IFDIR) {
      return(EXIT_SUCCESS);
    } else {
      // logger is unavailable here yet, so use stderr
      std::cerr << "'" << path << "' exists and not directory\n";
      return(EXIT_FAILURE);
    }
  }
  if (mkdir(path.c_str(), 0750)) {
    std::perror(path.c_str());
    std::cerr << "Unable to create dir '" << path << "'\n";
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

int helpers::chowner(std::string path, uid_t pw_uid, gid_t pw_gid) {
  if (chown(path.c_str(), pw_uid, pw_gid)) {
    std::perror(path.c_str());
    std::cerr << "Unable to chown "
      << pw_uid << ":" << pw_gid << " " << path << "\n";
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

int helpers::create_dir_and_chown(std::string path, uid_t pw_uid, gid_t pw_gid) {
  if (create_dir(path)) {
    return(EXIT_FAILURE);
  }
  if (chowner(path, pw_uid, pw_gid)) {
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

int helpers::createDirs(const OptionParser &opts) {
  if (create_dir_and_chown(opts.logDir, opts.pw_uid, opts.pw_gid)) {
    return(EXIT_FAILURE);
  }
  if (create_dir_and_chown(opts.pidDir, opts.pw_uid, opts.pw_gid)) {
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

bool helpers::pidFileExists(const OptionParser &opts) {
  // check if pid file exists
  struct stat info;
  if (stat(opts.pidFile.c_str(), &info) != 0 ) {
    return(false);
  }
  // check if piddile is a file, actually
  if (!((info.st_mode & S_IFMT) == S_IFREG)) {
    std::cerr << "'" << opts.pidFile << "' is not a regular file\n";
    return(false);
  }
  return(true);
}

int helpers::killProcess(const OptionParser &opts) {
  if (!pidFileExists(opts)) {
    std::perror("Error accessing PID file");
    std::cerr << "Unable to find '" << opts.pidFile << "'. "
      << "Is daemon running?\n";
    return(EXIT_FAILURE);
  }
  // read pid from pidfile
  std::ifstream pidfile(opts.pidFile);
  pid_t pid;
  pidfile >> pid;
  // check if process exists
  if (kill(pid, 0)) {
    std::cerr << "Process with PID '" << pid << "' is not running\n";
    return(EXIT_FAILURE);
  }
  // get process group for PID
  pid_t pgid;
  pgid = getpgid(pid);

  int seconds = 0;
  while (seconds < opts.killtimeout) {
    sleep(1);
    if (killpg(pgid, SIGTERM)) {
      return(EXIT_SUCCESS);
    }
    seconds++;
  }
  std::cerr << "Timeout killing process. Sending SIGKILL.\n";
  killpg(pgid, SIGKILL);
  // do cleanup for killed process
  if (std::remove(opts.pidFile.c_str()) != 0 ) {
    std::cerr << "Unable to delete '" << opts.pidFile << "'\n";
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

int helpers::changeUser(const OptionParser &opts) {
  if (setuid(opts.pw_uid)) {
    std::perror("Unable to change user");
    std::cerr << "Unable to change EUID to " << opts.pw_uid
      << " to run as " << opts.user <<  "\n";
    return(EXIT_FAILURE);
  }
  return(EXIT_SUCCESS);
}

std::vector<std::string> helpers::readDirectory(const std::string& name) {
  std::vector<std::string> res;
  DIR* dirp = opendir(name.c_str());
  struct dirent * dp;
  while ((dp = readdir(dirp)) != NULL) {
    res.push_back(dp->d_name);
  }
  closedir(dirp);
  return res;
}

std::ostream& operator <<(
    std::ostream& os, const std::vector<std::string>& v) {
  for (auto it = v.begin(); it != v.end(); it++) {
    os << *it << "; ";
  }
  return os;
}
