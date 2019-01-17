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
#include "../config.hpp"
#include "../optionparser/optionparser.hpp"
#include "../logger/logger.hpp"
#include "../helpers/helpers.hpp"
#include "../exceptions/exceptions.hpp"
#include <map>
#include <mutex>
#include <libtorrent/torrent_info.hpp>
#include <libtorrent/error_code.hpp>
#include <chrono>

typedef std::chrono::time_point<std::chrono::system_clock> timeStamp_t;

struct localFile_t {
  std::string filename;
  libtorrent::torrent_info torrent_info;
};

struct lunaTorrent_t {
  libtorrent::torrent_info torrent_info;
  timeStamp_t timeStamp;
  bool isInLuna;
};

typedef std::map<std::string, lunaTorrent_t> torrentsList_t;

class Torrents {
public:
  Torrents(const OptionParser &opts);
  bool update();
private:
  localFile_t parseTorrentFile_(std::string);
  void updateLocalFiles_();
  void updateLunaFiles_();
  const OptionParser opts_;
  log4cplus::Logger logger_;
  torrentsList_t torrents_;
  std::mutex torrentsMutex_;
  timeStamp_t lastCheckedLuna_;
  std::unique_lock<std::mutex> torrentsLock_;
};
