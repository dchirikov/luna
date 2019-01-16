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

#include "optionparser.hpp"

void OptionParser::PrintHelp_() {
  std::cout
  << "Usage: "
    << exec_name_ << " [-h] [-v] -b FILE -r TRACKER_URL -t TORRENT_FILE\n"
  << "        -h                  Print help.\n"
  << "        -b                  Input file.\n"
  << "        -r                  URL of the tracker.\n"
  << "        -t                  Name of the output torrent file.\n"
  ;
}

OptionParser::OptionParser(int argc, char* argv[])
  : exec_name_(argv[0]) {
  char key;
  while ((key = getopt(argc,argv,"hvb:r:t:")) != -1) {
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
      case 'b':
        tarball = std::string(optarg);
        break;
      case 't':
        torrent = std::string(optarg);
        break;
      case 'r':
        tracker = std::string(optarg);
        break;
      default:
        PrintHelp_();
        exit(EXIT_FAILURE);
        break;
    }
  }
  if ((tarball == "") | (torrent == "") | (tracker == "")) {
        PrintHelp_();
        exit(EXIT_FAILURE);
  }
  tarballDir = getDirname_(tarball);
}

std::ostream& operator <<(std::ostream& os, const OptionParser& opt) {
  os << "verbosity: " << opt.logLevel << "; "
    << "tarball: " << opt.tarball << "; "
    << "tracker: " << opt.tracker << "; "
    << "torrent: " << opt.torrent << "; "
    << "tarballDir: " << opt.tarballDir
  ;
  return(os);
}

std::string OptionParser::getDirname_(const std::string path) {
  char* tmp = strdup(path.c_str());
  auto dir = std::string(dirname(tmp));
  free(tmp);
  return dir;
}
