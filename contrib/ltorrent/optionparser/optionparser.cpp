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

#include "../config.hpp"
#include "optionparser.hpp"

void OptionParser::PrintHelp_() {
  std::cout
  << "Usage: " << exec_name_ << " [-h] [-v] [-s] [-l PATH] [-u USER]\n"
  << "                [-p PATH]\n"
  << "        -h                  Print help.\n"
  << "        -k                  Kill daemon.\n"
  << "        -u USER             Run as USER. Default is '"
                                  << DEFAULT_LTORRENT_USER << "'\n"
  << "        -p PATH             Directory with tarballs and torrents.\n"
  << "                            Default is '" << DEFAULT_LTORRENT_HOMEDIR
                                  << "'\n"
  << "        -v                  Increase verbosity.\n"
  << "        -D                  Do not daemonize\n"
  << "        -l PATH             Log file. Default is '"
                                  << DEFAULT_LTORRENT_LOGFILE << "'\n"
  ;
}

OptionParser::OptionParser(int argc, char* argv[])
  : exec_name_(argv[0]) {
  char key;
  while ((key = getopt(argc,argv,"hvslk:u:p:D")) != -1) {
    switch(key) {
      case 'h':
        PrintHelp_();
        exit(EXIT_SUCCESS);
        break;
      case 'v':
        // as per header:
        // TRACE_LOG_LEVEL = 0;
        // DEBUG_LOG_LEVEL = 10000;
        // INFO_LOG_LEVEL = 20000
        if (logLevel > log4cplus::TRACE_LOG_LEVEL) {
          logLevel -= log4cplus::DEBUG_LOG_LEVEL;
        }
        break;
      case 'D':
        daemonize = false;
        break;
      case 'k':
        kill = true;
        break;
      default:
        PrintHelp_();
        exit(EXIT_FAILURE);
        break;
    }
  }
  // get UID and GID of the user
  auto user_data = getpwnam(user.c_str());
  pw_uid = user_data->pw_uid;
  pw_gid = user_data->pw_gid;

  // expand paths
  expandPath_(&homeDir);
  expandPath_(&logFile);
  expandPath_(&pidFile);

  // get parent dirs for PID file and logs
  logDir = getDirname_(logFile);
  pidDir = getDirname_(pidFile);

}

void OptionParser::expandPath_(std::string* path) {
  wordexp_t exp_result;
  wordexp((*path).c_str(), &exp_result, 0);
  *path = std::string(exp_result.we_wordv[0]);
}

std::string OptionParser::getDirname_(const std::string path) {
  char* tmp = strdup(path.c_str());
  auto dir = std::string(dirname(tmp));
  free(tmp);
  return dir;
}
