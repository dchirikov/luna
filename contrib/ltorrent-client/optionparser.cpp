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

#include "optionparser.h"

void OptionParser::_PrintHelp() {
  std::cout
  << "Usage: " << _exec_name << " [-h] -t FILE [-p PID] [-f PIDFILE]\n"
  << "                [-b XXX.XXX.XXX.XXX] [-d NUM]\n"
  << "        -h                  Print help.\n"
  << "        -t FILE             Torrent file.\n"
  << "        -p PID              SIGUSR1 will be sent to this process\n"
  << "                            on complete.\n"
  << "        -f PIDFILE          File to write own pid to.\n"
  << "                            (" << _exec_name << ".pid by default)\n"
  << "        -b XXX.XXX.XXX.XXX  IP to bind. (0.0.0.0 by default)\n"
  << "        -d NUM              Sent announce to tracker every NUM sec.\n"
  << "                            (10 sec by default)\n";
}

OptionParser::OptionParser(int argc, char* argv[])
  : _exec_name(argv[0]), pidfile(std::string(argv[0]) + ".pid")  {
  char key;
  while ((key = getopt(argc,argv,"ht:p:f:b:d:")) != -1) {
    switch(key) {
      case 'h':
        _PrintHelp();
        exit(EXIT_SUCCESS);
        break;
      case 't':
        torrentfile = std::string(optarg);
        break;
      case 'p':
        userpid = atoi(optarg);
        break;
      case 'f':
        pidfile = std::string(optarg);
        break;
      case 'b':
        bindip = std::string(optarg);
        break;
      case 'd':
        delay = atoi(optarg);
        break;
      default:
        _PrintHelp();
        exit(EXIT_FAILURE);
        break;
    }
  }
  if (torrentfile.empty()) {
    std::cerr << _exec_name << ": torrent file should be specified\n";
    _PrintHelp();
    exit(EXIT_FAILURE);
  }
}

