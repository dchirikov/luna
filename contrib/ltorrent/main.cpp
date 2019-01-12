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

#include "main.hpp"

int main(int argc, char* argv[]) {
  auto opts = OptionParser(argc, argv);
  if (opts.kill) {
    if (LTorrent::changeUser(opts)) {
      exit(EXIT_FAILURE);
    }
    if (LTorrent::killProcess(opts)) {
      exit(EXIT_FAILURE);
    }
    exit(EXIT_SUCCESS);
  }
  int rc = 0;
  if (LTorrent::createDirs(opts)) {
    exit(EXIT_FAILURE);
  }
  if (LTorrent::changeUser(opts)) {
    exit(EXIT_FAILURE);
  }
  init_logger(opts);
  auto lt = LTorrent(opts);
  run(lt.daemonize);
  run(lt.createPidFile);
  run(lt.registerHandlers);
  run(lt.run);
  run(lt.cleanup);
}
