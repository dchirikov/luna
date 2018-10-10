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

#include "optionparser.h"
#include <stdlib.h>
#include <stdio.h>
#include <iostream>
#include <fstream>
#include <csignal>
#include "boost/asio/error.hpp"
#include "libtorrent/entry.hpp"
#include "libtorrent/bencode.hpp"
#include "libtorrent/session.hpp"
#include "libtorrent/session.hpp"
#include <libtorrent/alert_types.hpp>
#include <vector>
#include <sstream>
#include <thread>
#include <chrono>

class LtorrentClient {
public:
  static bool running;
  static void StopHandler(int signal);
  LtorrentClient(OptionParser opts);
  int RegisterHandlers();
  int CreatePidfile();
  int SetPeerID();
  int BindPorts();
  int DownloadTorrent();
  int RemovePidfile();
private:
  OptionParser _opts;
  static libtorrent::session _sess;
};

